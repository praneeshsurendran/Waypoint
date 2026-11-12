"""Map domain conflicts to the established frontend error contract."""

from fastapi import HTTPException
from app.domain.workflow import StatusEntity
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.plan import Trip, Stop
from app.domain.workflow import (
    InvalidTransition,
    transition,
    ORDER_TRANSITIONS,
    TRIP_TRANSITIONS,
    STOP_TRANSITIONS,
)


def _transition(entity: StatusEntity, new_status: str, table: dict[str, set[str]]) -> None:
    try:
        transition(entity, new_status, table)
    except InvalidTransition as exc:
        raise HTTPException(
            409,
            detail={
                "code": "INVALID_TRANSITION",
                "message": str(exc),
                "details": {
                    "current": exc.current,
                    "attempted": exc.attempted,
                    "allowed": exc.allowed,
                },
            },
        ) from exc


def transition_order(order: Order, new_status: str) -> None:
    _transition(order, new_status, ORDER_TRANSITIONS)


def transition_trip(trip: Trip, new_status: str) -> None:
    _transition(trip, new_status, TRIP_TRANSITIONS)


def transition_stop(stop: Stop, new_status: str) -> None:
    _transition(stop, new_status, STOP_TRANSITIONS)
