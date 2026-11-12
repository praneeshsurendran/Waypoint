from collections.abc import Mapping
from uuid import UUID
from pydantic import JsonValue, TypeAdapter
from sqlalchemy.orm import Session, sessionmaker
from waypoint_messaging import EventPublisher, SQSQueue
from sqlalchemy import select
from app.infrastructure.messaging.models import Outbox
from waypoint_contracts.events import EventEnvelope
from waypoint_observability import correlation_id, traceparent


def enqueue(
    db: Session,
    event_type: str,
    aggregate_id: str | int,
    data: Mapping[str, object],
    event_id: UUID | None = None,
) -> EventEnvelope:
    envelope = EventEnvelope(
        event_type=event_type,
        aggregate_id=str(aggregate_id),
        source="operations",
        correlation_id=correlation_id.get(),
        traceparent=traceparent.get(),
        data=TypeAdapter(dict[str, JsonValue]).validate_python(dict(data)),
    )
    if event_id is not None:
        envelope.event_id = event_id
    db.add(Outbox(id=str(envelope.event_id), envelope=envelope.model_dump(mode="json")))
    return envelope


def publish_pending(
    factory: sessionmaker[Session],
    publisher: EventPublisher,
    jobs: SQSQueue | None = None,
    limit: int = 50,
) -> int:
    sent = 0
    for _ in range(limit):
        with factory.begin() as db:
            row = db.scalar(
                select(Outbox)
                .where(Outbox.published.is_(False))
                .order_by(Outbox.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if row is None:
                break
            row.attempts += 1
            try:
                envelope = EventEnvelope.model_validate(row.envelope)
                if envelope.event_type == "planning.job_requested":
                    if jobs is None:
                        raise RuntimeError("planning queue required")
                    jobs.send(envelope)
                else:
                    publisher.publish(envelope)
            except Exception:
                import logging

                logging.getLogger("waypoint.outbox").warning(
                    "Outbox publication failed; retry pending", extra={"event_id": row.id}
                )
                return -1
            row.published = True
            sent += 1
    return sent
