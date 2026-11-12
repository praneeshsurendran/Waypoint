"""Version-1 integration payloads. Additive fields are accepted; required identity is checked."""

from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, Field


class ReferenceChange(BaseModel):
    entity: Literal["depots", "outlets", "vehicles", "calendar_days", "users"]
    record: dict[str, Any]
    revision: int = Field(ge=1)


class OrderChange(BaseModel):
    order_id: int
    outlet_id: str | None = None


class ClosureOrder(BaseModel):
    id: int
    reference: str
    outlet_id: str
    weight: float
    volume: float
    cases: int


class OrdersClosed(BaseModel):
    delivery_date: date
    actor_user_id: int
    orders: list[ClosureOrder]


class TripSnapshot(BaseModel):
    id: int
    vehicle_id: str
    trip_number: int = Field(ge=1, le=2)
    status: str
    revision: int = Field(default=1, ge=1)


class TripChange(BaseModel):
    trips: list[TripSnapshot]


class StopChange(TripChange):
    stop_id: int
    outlet_id: str
    order_ids: list[int] = []


class PlanningCommand(BaseModel):
    job_id: str = Field(min_length=1, max_length=36)


class IntakeCommand(BaseModel):
    actor_user_id: int


class AuditRecord(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    actor_user_id: int | None = None


PAYLOADS: dict[str, type[BaseModel]] = {
    "identity.user_changed": ReferenceChange,
    "network.reference_changed": ReferenceChange,
    "orders.closed": OrdersClosed,
    "planning.job_requested": PlanningCommand,
    "intake.close_requested": IntakeCommand,
    "audit.recorded": AuditRecord,
    **{
        name: OrderChange
        for name in (
            "order.confirmed",
            "order.deferred",
            "receipt.confirmed",
            "receipt.issue_reported",
        )
    },
    **{
        name: TripChange
        for name in (
            "plan.published",
            "load.shortfall_reported",
            "load.completed",
            "delivery.started",
        )
    },
    **{
        name: StopChange
        for name in ("stop.completed", "delivery.failed", "proof_of_delivery.recorded")
    },
    "delivery.delayed": TripChange,
}
