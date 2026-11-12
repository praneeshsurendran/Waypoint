"""Compatibility and boundary regressions introduced by the full-stack audit."""

import datetime as dt
from sqlalchemy import event
from app.infrastructure.db.models.audit import AuditLog


def test_cursor_drains_equal_timestamp_events_without_loss(client, db_session, dispatcher_token):
    dispatcher_headers = {"Authorization": "Bearer " + dispatcher_token}
    same_time = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    db_session.add_all(
        [
            AuditLog(
                action=f"CURSOR_{i}", entity_type="test", entity_id=str(i), created_at=same_time
            )
            for i in range(7)
        ]
    )
    db_session.flush()
    cursor = 0
    seen = []
    while True:
        response = client.get(
            f"/api/v1/admin/events/poll?cursor={cursor}&limit=2", headers=dispatcher_headers
        )
        assert response.status_code == 200, response.text
        page = response.json()
        if not page["events"]:
            break
        seen.extend(row["id"] for row in page["events"])
        cursor = page["next_cursor"]
    assert len(seen) == len(set(seen))
    assert (
        len(
            [
                row
                for row in db_session.query(AuditLog).filter(AuditLog.id.in_(seen)).all()
                if row.action.startswith("CURSOR_")
            ]
        )
        == 7
    )
    assert (
        client.get("/api/v1/admin/events/poll?limit=0", headers=dispatcher_headers).status_code
        == 422
    )


def test_daily_summary_uses_three_grouped_queries_and_keeps_wire_fields(
    client, db_session, dispatcher_token
):
    dispatcher_headers = {"Authorization": "Bearer " + dispatcher_token}
    statements = []
    connection = db_session.connection()

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", capture)
    try:
        response = client.get(
            "/api/v1/admin/analytics/daily?date=2026-01-01", headers=dispatcher_headers
        )
    finally:
        event.remove(connection, "before_cursor_execute", capture)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["orders"] == {
        "total": 0,
        "by_status": {},
        "delivered": 0,
        "failed": 0,
        "deferred": 0,
    }
    assert result["trips"] == {"total": 0, "by_status": {}, "completed": 0}
    assert len([statement for statement in statements if "GROUP BY" in statement]) == 3


def test_manual_edit_rejects_an_order_from_another_delivery_day(
    client, db_session, dispatcher_token, dispatcher_user, store_manager_user
):
    from app.infrastructure.db.models.order import Order
    from app.infrastructure.db.models.plan import Plan

    plan = Plan(
        delivery_date=dt.date(2035, 1, 2), version=1, status="DRAFT", created_by=dispatcher_user.id
    )
    order = Order(
        reference="AUDIT-CROSS-DAY",
        outlet_id=store_manager_user.outlet_id,
        brand="Fresh",
        temperature_class="CHILLED",
        delivery_date=dt.date(2035, 1, 3),
        status="QUEUED",
        total_cases=5,
        total_weight=50,
        total_volume=1,
    )
    db_session.add_all([plan, order])
    db_session.flush()
    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers={"Authorization": "Bearer " + dispatcher_token},
        json={"moves": [{"order_id": order.id, "to_trip_id": None}]},
    )
    assert response.status_code == 409, response.text
    db_session.refresh(order)
    assert order.delivery_date == dt.date(2035, 1, 3)
    assert order.status == "QUEUED"
