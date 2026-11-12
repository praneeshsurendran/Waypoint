"""Audit log service — writes every transition and plan decision."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.infrastructure.db.models.audit import AuditLog


def log_action(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str | int,
    actor_user_id: Optional[int] = None,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
) -> None:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_json=before,
        after_json=after,
    )
    db.add(entry)
    # Flush so the entry is persisted within the same transaction
    db.flush()
    # Integration events are part of this same transaction, never emitted before commit.
    from app.infrastructure.messaging.outbox import enqueue
    from app.infrastructure.db.models.order import Order
    from app.infrastructure.db.models.plan import Plan, Trip
    from app.infrastructure.db.models.reference import Outlet

    mapping = {
        "CONFIRM_ORDER": "order.confirmed",
        "PUBLISH_PLAN": "plan.published",
        "DEFER_ORDER": "order.deferred",
        "RELEASE_TRIP": "load.completed",
        "START_TRIP": "delivery.started",
        "CONFIRM_RECEIPT": "receipt.confirmed",
        "REPORT_ISSUE": "receipt.issue_reported",
    }
    event_type = mapping.get(action)
    if action == "CLOSE_INTAKE" and entity_type == "Order":
        event_type = "order.confirmed"
    if action == "LOAD_FLAG" and (after or {}).get("status") in ("MISSING", "DAMAGED"):
        event_type = "load.shortfall_reported"
    if event_type:
        data = {"actor_user_id": actor_user_id, "decision": after or {}, "revision": entry.id}
        if entity_type == "Order":
            order = db.get(Order, int(entity_id))
            if order:
                outlet = db.get(Outlet, order.outlet_id)
                data.update(
                    order_id=order.id,
                    reference=order.reference,
                    outlet_id=order.outlet_id,
                    depot_id=outlet.depot_code if outlet else None,
                    status=order.status,
                )
        if entity_type == "Trip":
            trip = db.get(Trip, int(entity_id))
            if trip:
                from app.application.use_cases.delivery import trip_payload

                data.update(trip_payload(db, trip))
        if entity_type == "Plan":
            plan = db.get(Plan, int(entity_id))
            data.update(
                delivery_date=str(plan.delivery_date),
                version=plan.version,
                trips=[
                    {
                        "id": t.id,
                        "vehicle_id": t.vehicle_id,
                        "trip_number": t.trip_number,
                        "status": t.status,
                        "revision": t.revision,
                        "stops": [
                            {
                                "id": s.id,
                                "outlet_id": s.outlet_id,
                                "sequence": s.sequence,
                                "order_ids": s.order_ids,
                            }
                            for s in t.stops
                        ],
                    }
                    for t in plan.trips
                ],
            )
        enqueue(db, event_type, entity_id, data)
