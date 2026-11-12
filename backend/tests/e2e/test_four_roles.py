"""Real SQL and business handlers; only HTTP transport to identity is in-process."""

from sqlalchemy import select


def login(clients, name):
    response = clients["identity"].post(
        "/api/v1/auth/login", json={"username": name, "password": "test-role-password"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_four_role_order_loading_offline_receipt_and_notifications(
    service_clients, contexts, monkeypatch
):
    from app.core import clock

    monkeypatch.setattr(clock, "is_past_cutoff", lambda: False)
    clients = service_clients
    headers = {
        role: login(clients, role)
        for role in ("manager", "dispatcher", "loader", "driver", "admin")
    }
    ops = clients["operations"]
    created = ops.post(
        "/api/v1/orders",
        headers=headers["manager"],
        json={"outlet_id": "SYN001", "temperature_class": "CHILLED", "cases": 20},
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]
    oversized = ops.post(
        "/api/v1/orders",
        headers=headers["dispatcher"],
        json={
            "outlet_id": "SYN003",
            "temperature_class": "AMBIENT",
            "cases": 10,
            "total_weight": 999999,
        },
    )
    assert oversized.status_code == 201, oversized.text
    assert (
        ops.post("/api/v1/orders/close", headers=headers["dispatcher"]).status_code
        == 200
    )
    result = ops.post("/api/v1/plans/auto-plan", headers=headers["dispatcher"])
    assert result.status_code == 201, result.text
    plan = result.json()
    trip = plan["trips"][0]
    stop = trip["stops"][0]
    assert (
        ops.post(
            f'/api/v1/plans/{plan["id"]}/publish', headers=headers["dispatcher"]
        ).status_code
        == 200
    )
    users = (
        clients["identity"].get("/api/v1/admin/users", headers=headers["admin"]).json()
    )
    driver = next(u for u in users if u["username"] == "driver")
    updated = clients["identity"].patch(
        f'/api/v1/admin/users/{driver["id"]}',
        headers=headers["admin"],
        json={"vehicle_id": trip["vehicle_id"]},
    )
    assert updated.status_code == 200, updated.text
    path = f'/api/v1/loading/trips/{trip["id"]}'
    assert (
        ops.post(
            path + "/flags",
            headers=headers["loader"],
            json={
                "status": "MISSING",
                "order_id": order_id,
                "note": "One case needs replacing",
            },
        ).status_code
        == 201
    )
    assert (
        ops.post(path + "/release", headers=headers["loader"]).json()["detail"]["code"]
        == "UNRESOLVED_SHORTFALL"
    )
    assert (
        ops.post(
            path + "/flags",
            headers=headers["loader"],
            json={"status": "OK", "order_id": order_id, "note": "Replacement loaded"},
        ).status_code
        == 201
    )
    assert ops.post(path + "/release", headers=headers["loader"]).status_code == 200
    assert (
        ops.post("/api/v1/driver/trips/start", headers=headers["driver"]).status_code
        == 200
    )
    arrive = {
        "client_op_id": "e2e-arrive",
        "stop_id": stop["id"],
        "outcome": "ARRIVED",
        "device_id": "e2e-device",
        "device_sequence": 1,
    }
    assert (
        ops.post(
            f'/api/v1/driver/stops/{stop["id"]}/events',
            headers=headers["driver"],
            json=arrive,
        ).status_code
        == 201
    )
    proof = ops.post(
        "/api/v1/driver/uploads",
        headers=headers["driver"],
        data={"stop_id": str(stop["id"])},
        files={"file": ("proof.png", b"\x89PNG\r\n\x1a\nsynthetic-test", "image/png")},
    )
    assert proof.status_code == 200, proof.text
    evidence = proof.json()["path"]
    assert ops.get(evidence).status_code == 401
    assert ops.get(evidence, headers=headers["manager"]).status_code == 200
    event = {
        "client_op_id": "e2e-deliver",
        "stop_id": stop["id"],
        "outcome": "DELIVERED",
        "device_id": "e2e-device",
        "device_sequence": 2,
        "pod_photo_path": "http://api.example" + evidence,
        "receiver_name": "Synthetic receiver",
    }
    first = ops.post(
        "/api/v1/driver/sync",
        headers=headers["driver"],
        json={"events": [event, event]},
    )
    assert first.status_code == 200, first.text
    assert all(row["accepted"] for row in first.json())
    assert first.json()[1]["message"] == "duplicate"
    history = ops.get(
        "/api/v1/driver/sync",
        headers=headers["driver"],
        params={"device_id": "e2e-device", "limit": 1},
    ).json()
    assert history["server_cursor"] == 2
    assert history["next_cursor"] == 1
    assert history["has_more"] is True
    assert history["events"][0]["event"]["outcome"] == "ARRIVED"
    next_page = ops.get(
        "/api/v1/driver/sync",
        headers=headers["driver"],
        params={"device_id": "e2e-device", "after": 1},
    ).json()
    assert next_page["next_cursor"] == 2 and next_page["has_more"] is False
    assert all(
        next_page["events"][0]["event"][key] == value for key, value in event.items()
    )
    assert next_page["events"][0]["event"]["pod_photo_path"] == event["pod_photo_path"]
    assert (
        ops.get(
            "/api/v1/driver/sync",
            headers=headers["manager"],
            params={"device_id": "e2e-device"},
        ).status_code
        == 403
    )
    assert (
        ops.get(
            "/api/v1/driver/sync",
            headers=headers["dispatcher"],
            params={"device_id": "e2e-device"},
        ).json()["events"]
        == []
    )
    conflict = ops.post(
        "/api/v1/driver/sync",
        headers=headers["driver"],
        json={"events": [{**event, "note": "changed payload"}]},
    )
    assert conflict.json()[0]["message"] == "idempotency_conflict"
    timeline = ops.get("/api/v1/driver/history", headers=headers["driver"])
    assert timeline.status_code == 200
    assert {"arrived", "accepted", "released", "started"} <= {
        row["kind"] for row in timeline.json()
    }
    assert all(row["vehicleId"] == trip["vehicle_id"] for row in timeline.json())
    assert (
        ops.get("/api/v1/driver/history", headers=headers["manager"]).status_code == 403
    )
    receipt = ops.post(
        f"/api/v1/orders/{order_id}/receipt",
        headers=headers["manager"],
        json={"outcome": "FULL"},
    )
    assert receipt.status_code == 201, receipt.text
    from app.infrastructure.messaging.models import Outbox, DeviceOperation
    from app.infrastructure.db.models.delivery import DeliveryEvent
    from waypoint_contracts.events import EventEnvelope
    from waypoint_notifications.application.services.events import handle

    with contexts["operations"]() as db:
        assert len(db.scalars(select(DeliveryEvent)).all()) == 1
        assert len(db.scalars(select(DeviceOperation)).all()) == 2
        events = [
            EventEnvelope.model_validate(row.envelope)
            for row in db.scalars(select(Outbox)).all()
        ]
    for event in events:
        handle(event)
        handle(event)
    inbox = clients["notifications"].get(
        "/api/v1/notifications", headers=headers["manager"]
    )
    assert inbox.status_code == 200, inbox.text
    assert any(row["type"] == "proof_of_delivery.recorded" for row in inbox.json())
    assert len({row["id"] for row in inbox.json()}) == len(inbox.json())
