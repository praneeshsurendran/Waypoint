from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(200))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def log_action(
    db, action, entity_type, entity_id, actor_user_id=None, before=None, after=None
):
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before_json=before,
            after_json=after,
        )
    )
    db.flush()

    from waypoint_contracts.events import EventEnvelope
    from waypoint_observability import correlation_id
    from waypoint_network.infrastructure.db.models import Outbox

    event = EventEnvelope(
        event_type="audit.recorded",
        source="network-fleet",
        aggregate_id=f"{entity_type}:{entity_id}",
        correlation_id=correlation_id.get(),
        data={
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "actor_user_id": actor_user_id,
            "before": before,
            "after": after,
        },
    )
    db.add(Outbox(id=str(event.event_id), envelope=event.model_dump(mode="json")))
