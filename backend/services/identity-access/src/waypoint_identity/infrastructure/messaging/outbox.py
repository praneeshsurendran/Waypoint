from sqlalchemy.orm import Session, sessionmaker
from waypoint_messaging import EventPublisher
import json
from sqlalchemy import event, select
from waypoint_contracts.events import EventEnvelope
from waypoint_observability import correlation_id, traceparent
from waypoint_identity.infrastructure.db.models import Outbox
from waypoint_identity.infrastructure.db.accounts import User

OWNERS = (User,)


def install(factory: sessionmaker[Session]) -> None:
    @event.listens_for(factory, "before_flush")
    def collect(session: Session, *_: object) -> None:
        changed = [
            obj
            for obj in set(session.new) | set(session.dirty)
            if isinstance(obj, OWNERS)
            and (
                obj in session.new
                or session.is_modified(obj, include_collections=False)
            )
        ]
        for obj in changed:
            obj.revision = (obj.revision or 0) + 1
        session.info.setdefault("owner_changes", []).extend(changed)

    @event.listens_for(factory, "after_flush_postexec")
    def enqueue(session: Session, *_: object) -> None:
        for obj in session.info.pop("owner_changes", []):
            data = {
                column.key: getattr(obj, column.key)
                for column in obj.__table__.columns
                if column.key != "password_hash"
            }
            data = json.loads(json.dumps(data, default=lambda v: v.isoformat()))
            key = str(
                next(getattr(obj, column.key) for column in obj.__table__.primary_key)
            )
            envelope = EventEnvelope(
                event_type="identity.user_changed",
                source="identity-access",
                aggregate_id=f"{obj.__tablename__}:{key}",
                correlation_id=correlation_id.get(),
                traceparent=traceparent.get(),
                data={
                    "entity": obj.__tablename__,
                    "record": data,
                    "revision": obj.revision,
                },
            )
            session.add(
                Outbox(
                    id=str(envelope.event_id), envelope=envelope.model_dump(mode="json")
                )
            )


def publish_pending(
    factory: sessionmaker[Session], publisher: EventPublisher, limit: int = 50
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
                publisher.publish(EventEnvelope.model_validate(row.envelope))
            except Exception:
                # Keep the row pending. A crash after publish/before commit can duplicate it.
                return -1
            row.published = True
            sent += 1
    return sent
