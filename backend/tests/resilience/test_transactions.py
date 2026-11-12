from sqlalchemy import select
import pytest
from waypoint_contracts.events import EventEnvelope


def test_outbox_is_atomic_and_failed_publish_is_retryable(contexts):
    from app.infrastructure.messaging.models import Outbox
    from app.infrastructure.messaging.outbox import enqueue, publish_pending

    factory = contexts["operations"]
    with pytest.raises(RuntimeError):
        with factory.begin() as db:
            enqueue(db, "order.confirmed", "1", {"order_id": 1})
            raise RuntimeError("business rollback")
    with factory() as db:
        assert db.scalars(select(Outbox)).all() == []
    with factory.begin() as db:
        enqueue(db, "order.confirmed", "2", {"order_id": 2})

    class Publisher:
        failed = True
        events = []

        def publish(self, event):
            if self.failed:
                raise OSError("transient")
            self.events.append(event)

    publisher = Publisher()
    publish_pending(factory, publisher)
    with factory() as db:
        assert not db.scalars(select(Outbox)).one().published
    publisher.failed = False
    assert publish_pending(factory, publisher) == 1
    assert len(publisher.events) == 1


def test_notification_crash_after_commit_before_ack_deduplicates(contexts):
    from waypoint_notifications.application.services.events import handle
    from waypoint_notifications.infrastructure.db.notifications import (
        Notification,
        DeliveryLog,
    )
    from waypoint_notifications.infrastructure.db.models import Inbox

    event = EventEnvelope(
        event_type="order.deferred",
        source="operations",
        aggregate_id="7",
        data={"outlet_id": "SYN001", "order_id": 7, "reason_code": "CAPACITY"},
    )
    handle(
        event
    )  # Simulate successful DB commit followed by worker death before SQS delete.
    handle(event)
    with contexts["notifications"]() as db:
        assert len(db.scalars(select(Notification)).all()) == 1
        assert len(db.scalars(select(DeliveryLog)).all()) == 1
        assert len(db.scalars(select(Inbox)).all()) == 1
    with pytest.raises(ValueError):
        handle(event.model_copy(update={"data": {"outlet_id": "different"}}))


def test_projection_out_of_order_and_duplicate_delivery(contexts):
    from app.infrastructure.messaging.consumer import handle
    from app.infrastructure.db.models.reference import Depot, Vehicle
    from waypoint_contracts.events import EventEnvelope

    with contexts["operations"].begin() as db:
        db.add(Depot(code="Synthetic", name="Synthetic"))
    record = {
        "vehicle_id": "SYNV9",
        "type": "van",
        "temp": "ambient",
        "is_refrigerated": False,
        "weight_cap_kg": 1000,
        "volume_cap_m3": 8,
        "fuel_type": "diesel",
        "km_per_l": 8,
        "weekly_fuel_quota_l": 100,
        "depot_code": "Synthetic",
        "status": "in_workshop",
    }
    newer = EventEnvelope(
        event_type="network.reference_changed",
        source="network-fleet",
        aggregate_id="vehicles:SYNV9",
        data={"entity": "vehicles", "revision": 3, "record": record},
    )
    older = EventEnvelope(
        event_type="network.reference_changed",
        source="network-fleet",
        aggregate_id="vehicles:SYNV9",
        data={
            "entity": "vehicles",
            "revision": 2,
            "record": {**record, "status": "available"},
        },
    )
    handle(newer)
    handle(older)
    handle(newer)
    with contexts["operations"]() as db:
        assert db.get(Vehicle, "SYNV9").status == "in_workshop"
