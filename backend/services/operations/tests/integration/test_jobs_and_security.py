import datetime as dt
from sqlalchemy import select
from waypoint_contracts.events import EventEnvelope


def auth(clients, name):
    response = clients["identity"].post(
        "/api/v1/auth/login", json={"username": name, "password": "test-role-password"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_async_job_replay_and_pending_cancellation(service_clients, contexts):
    clients = service_clients
    headers = auth(clients, "dispatcher")
    from app.infrastructure.db.models.order import Order

    with contexts["operations"].begin() as db:
        db.add(
            Order(
                reference="JOB-ORDER",
                outlet_id="SYN001",
                brand="Fresh",
                temperature_class="CHILLED",
                delivery_date=dt.date(2024, 4, 10),
                status="QUEUED",
                total_cases=10,
                total_weight=100,
                total_volume=1,
                priority=False,
                cutoff_missed=False,
            )
        )
    response = clients["operations"].post(
        "/api/v1/planning/jobs",
        headers=headers,
        json={"delivery_date": "2024-04-10", "request_key": "job-replay"},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    from app.workers.planning import handle

    event = EventEnvelope(
        event_type="planning.job_requested",
        source="operations",
        aggregate_id=job_id,
        data={"job_id": job_id},
    )
    handle(event)
    handle(event)
    status = clients["operations"].get("/api/v1/planning/jobs/" + job_id, headers=headers)
    assert status.json()["status"] == "succeeded", status.text
    from app.infrastructure.db.models.plan import Plan

    with contexts["operations"]() as db:
        assert len(db.scalars(select(Plan)).all()) == 1
    pending = (
        clients["operations"]
        .post(
            "/api/v1/planning/jobs",
            headers=headers,
            json={"delivery_date": "2024-04-10", "request_key": "cancel"},
        )
        .json()["job_id"]
    )
    assert (
        clients["operations"]
        .post(f"/api/v1/planning/jobs/{pending}/cancel", headers=headers)
        .status_code
        == 200
    )
    handle(
        EventEnvelope(
            event_type="planning.job_requested",
            source="operations",
            aggregate_id=pending,
            data={"job_id": pending},
        )
    )
    assert (
        clients["operations"]
        .get("/api/v1/planning/jobs/" + pending, headers=headers)
        .json()["status"]
        == "cancelled"
    )


def test_scheduled_closure_is_idempotent_and_creates_a_planning_command(
    service_clients, contexts, monkeypatch
):
    from app.core import clock
    from app.infrastructure.db.models.user import User
    from app.infrastructure.messaging.models import Outbox, IntakeClosure, PlanningJob
    from app.infrastructure.messaging.consumer import handle

    monkeypatch.setattr(clock, "is_past_cutoff", lambda: False)
    response = service_clients["operations"].post(
        "/api/v1/orders",
        headers=auth(service_clients, "manager"),
        json={"outlet_id": "SYN001", "temperature_class": "CHILLED", "cases": 10},
    )
    assert response.status_code == 201, response.text
    with contexts["operations"]() as db:
        actor = db.scalar(select(User).where(User.username == "dispatcher")).id
    monkeypatch.setattr(clock, "is_past_cutoff", lambda: True)
    command = EventEnvelope(
        event_type="intake.close_requested",
        source="scheduler",
        aggregate_id="2024-04-10",
        data={"actor_user_id": actor},
    )
    handle(command)
    handle(command)
    with contexts["operations"]() as db:
        assert len(db.scalars(select(IntakeClosure)).all()) == 1
        closure = next(
            row
            for row in db.scalars(select(Outbox)).all()
            if row.envelope["event_type"] == "orders.closed"
        )
        event = EventEnvelope.model_validate(closure.envelope)
    handle(event)
    handle(event)
    with contexts["operations"]() as db:
        assert len(db.scalars(select(PlanningJob)).all()) == 1


def test_driver_scope_order_membership_and_delay_are_enforced(service_clients, contexts):
    from app.infrastructure.db.models.plan import Plan, Trip, Stop, StopOrder
    from app.infrastructure.db.models.order import Order

    with contexts["operations"].begin() as db:
        plan = Plan(delivery_date=dt.date(2024, 4, 10), status="PUBLISHED")
        db.add(plan)
        db.flush()
        own = Trip(plan_id=plan.id, vehicle_id="SYNV001", trip_number=1, status="IN_TRANSIT")
        other = Trip(plan_id=plan.id, vehicle_id="SYNV002", trip_number=1, status="IN_TRANSIT")
        db.add_all([own, other])
        db.flush()
        stop = Stop(trip_id=own.id, outlet_id="SYN001", sequence=1, status="ARRIVED")
        outside = Stop(trip_id=other.id, outlet_id="SYN002", sequence=1, status="ARRIVED")
        pending = Stop(trip_id=own.id, outlet_id="SYN003", sequence=2, status="PENDING")
        db.add_all([stop, outside, pending])
        db.flush()
        orders = []
        for i in range(2):
            order = Order(
                reference=f"SCOPE-{i}",
                outlet_id="SYN001",
                brand="Fresh",
                temperature_class="AMBIENT",
                delivery_date=dt.date(2024, 4, 10),
                status="IN_TRANSIT",
                total_cases=10,
                total_weight=100,
                total_volume=1,
                priority=False,
                cutoff_missed=False,
            )
            db.add(order)
            db.flush()
            orders.append(order)
            db.add(StopOrder(stop_id=stop.id, order_id=order.id))
        stop_id = stop.id
        pending_id = pending.id
        other_id = outside.id
        ids = [o.id for o in orders]
    headers = auth(service_clients, "driver")
    client = service_clients["operations"]
    base = {"client_op_id": "scope-1", "stop_id": other_id, "outcome": "DELIVERED"}
    assert (
        client.post(
            f"/api/v1/driver/stops/{other_id}/events", headers=headers, json=base
        ).status_code
        == 403
    )
    wrong = {**base, "client_op_id": "wrong-order", "stop_id": stop_id, "order_id": 9999}
    assert (
        client.post(f"/api/v1/driver/stops/{stop_id}/events", headers=headers, json=wrong).json()[
            "detail"
        ]["code"]
        == "ORDER_STOP_MISMATCH"
    )
    delay = {
        "client_op_id": "delay",
        "stop_id": stop_id,
        "outcome": "DELAY",
        "note": "Traffic delay",
    }
    assert (
        client.post(
            f"/api/v1/driver/stops/{stop_id}/events", headers=headers, json=delay
        ).status_code
        == 201
    )
    with contexts["operations"]() as db:
        assert db.get(Order, ids[0]).status == "IN_TRANSIT"
    for outcome in ("DELAY", "STARTED"):
        response = client.post(
            f"/api/v1/driver/stops/{pending_id}/events",
            headers=headers,
            json={"client_op_id": "pending-" + outcome, "stop_id": pending_id, "outcome": outcome},
        )
        assert response.status_code == 201, response.text
        with contexts["operations"]() as db:
            assert db.get(Stop, pending_id).status == "PENDING"
            assert db.get(Stop, pending_id).actual_arrival is None
    for i, oid in enumerate(ids):
        result = client.post(
            f"/api/v1/driver/stops/{stop_id}/events",
            headers=headers,
            json={
                "client_op_id": f"order-{i}",
                "stop_id": stop_id,
                "order_id": oid,
                "outcome": "DELIVERED",
            },
        )
        assert result.status_code == 201, result.text
        with contexts["operations"]() as db:
            assert db.get(Stop, stop_id).status == ("ARRIVED" if i == 0 else "COMPLETED")


def test_receipt_repeat_and_window_deadline_do_not_duplicate_effects(
    service_clients, contexts, monkeypatch
):
    from app.infrastructure.db.models.plan import Plan, Trip, Stop, StopOrder
    from app.infrastructure.db.models.order import Order
    from app.infrastructure.db.models.receipt import Receipt
    from app.infrastructure.messaging.models import Outbox
    from app.core import clock

    with contexts["operations"].begin() as db:
        plan = Plan(delivery_date=dt.date(2024, 4, 10), status="PUBLISHED")
        db.add(plan)
        db.flush()
        trip = Trip(plan_id=plan.id, vehicle_id="SYNV001", trip_number=1, status="IN_TRANSIT")
        db.add(trip)
        db.flush()
        stop = Stop(trip_id=trip.id, outlet_id="SYN001", sequence=1, status="ARRIVED")
        db.add(stop)
        db.flush()
        order = Order(
            reference="RECEIPT-IDEMPOTENT",
            outlet_id="SYN001",
            brand="Fresh",
            temperature_class="AMBIENT",
            delivery_date=dt.date(2024, 4, 10),
            status="DELIVERED",
            total_cases=10,
            total_weight=100,
            total_volume=1,
            priority=False,
            cutoff_missed=False,
        )
        db.add(order)
        db.flush()
        db.add(StopOrder(stop_id=stop.id, order_id=order.id))
        order_id = order.id
    monkeypatch.setattr(
        clock,
        "now",
        lambda: dt.datetime(2024, 4, 10, 9, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30))),
    )
    client = service_clients["operations"]
    driver = auth(service_clients, "driver")
    first = client.post("/api/v1/driver/check-delivery-windows", headers=driver)
    second = client.post("/api/v1/driver/check-delivery-windows", headers=driver)
    assert first.json() == {"created": 1}, first.text
    assert second.json() == {"created": 0}, second.text
    manager = auth(service_clients, "manager")
    for _ in range(2):
        response = client.post(
            f"/api/v1/orders/{order_id}/receipt", headers=manager, json={"outcome": "FULL"}
        )
        assert response.status_code == 201, response.text
    with contexts["operations"]() as db:
        assert len(db.scalars(select(Receipt)).all()) == 1
        events = [row.envelope["event_type"] for row in db.scalars(select(Outbox)).all()]
        assert events.count("delivery.delayed") == 1 and events.count("receipt.confirmed") == 1
