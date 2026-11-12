from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, field_validator, model_validator
from waypoint_contracts.common import ContractModel as BaseModel

EVENT_TYPES = frozenset(
    {
        "order.confirmed",
        "orders.closed",
        "plan.published",
        "order.deferred",
        "load.shortfall_reported",
        "load.completed",
        "delivery.started",
        "stop.completed",
        "delivery.failed",
        "proof_of_delivery.recorded",
        "receipt.confirmed",
        "receipt.issue_reported",
        "identity.user_changed",
        "network.reference_changed",
        "planning.job_requested",
        "intake.close_requested",
        "audit.recorded",
        "delivery.delayed",
    }
)


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    version: Literal[1] = 1
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=100)
    correlation_id: str = Field(default_factory=lambda: str(uuid4()), max_length=100)
    causation_id: str | None = None
    traceparent: str | None = Field(
        default=None, pattern=r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"
    )
    data: dict[str, Any]

    @field_validator("event_type")
    @classmethod
    def supported(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError("unsupported event type")
        return value

    @field_validator("occurred_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event time must have a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def typed_payload(self) -> "EventEnvelope":
        from .event_data import PAYLOADS

        payload = PAYLOADS[self.event_type].model_validate(self.data)
        if self.event_type in ("identity.user_changed", "network.reference_changed"):
            from .event_data import ReferenceChange

            if isinstance(payload, ReferenceChange):
                if (payload.entity == "users") != (
                    self.event_type == "identity.user_changed"
                ):
                    raise ValueError("event type does not own the reference entity")
        return self

    def fingerprint(self) -> str:
        import hashlib
        import json

        canonical = json.dumps(
            self.model_dump(mode="json", exclude_none=True),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()
