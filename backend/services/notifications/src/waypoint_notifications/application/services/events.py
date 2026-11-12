from waypoint_contracts.events import EventEnvelope
from sqlalchemy.dialects.postgresql import insert
from waypoint_notifications.bootstrap import SessionLocal
from waypoint_notifications.infrastructure.db.models import Inbox
from waypoint_notifications.infrastructure.db.notifications import (
    Notification,
    DeliveryLog,
)

NOTIFIABLE = {
    "order.deferred",
    "plan.published",
    "load.shortfall_reported",
    "load.completed",
    "delivery.started",
    "stop.completed",
    "delivery.failed",
    "delivery.delayed",
    "proof_of_delivery.recorded",
    "receipt.confirmed",
    "receipt.issue_reported",
}


def handle(event: EventEnvelope) -> None:
    digest = event.fingerprint()
    with SessionLocal.begin() as db:
        accepted = db.execute(
            insert(Inbox)
            .values(event_id=str(event.event_id), payload_hash=digest)
            .on_conflict_do_nothing()
            .returning(Inbox.event_id)
        ).scalar_one_or_none()
        if not accepted:
            previous = db.get(Inbox, str(event.event_id))
            if previous is None or previous.payload_hash != digest:
                raise ValueError("event identity conflict")
            return
        if event.event_type not in NOTIFIABLE:
            return
        if event.source != "operations":
            raise ValueError("untrusted notification producer")
        db.add(
            Notification(
                event_id=str(event.event_id),
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                outlet_id=event.data.get("outlet_id"),
                depot_id=event.data.get("depot_id"),
                vehicle_id=event.data.get("vehicle_id"),
                payload=event.data,
                created_at=event.occurred_at,
            )
        )
        db.add(DeliveryLog(event_id=str(event.event_id)))
