"""Map domain conflicts to the established frontend error contract."""

from fastapi import HTTPException
from app.domain.workflow import (
    InvalidTransition,
    transition,
    ORDER_TRANSITIONS,
    TRIP_TRANSITIONS,
    STOP_TRANSITIONS,
)


def _transition(entity, new_status, table):
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


def transition_order(order, new_status):
    _transition(order, new_status, ORDER_TRANSITIONS)


def transition_trip(trip, new_status):
    _transition(trip, new_status, TRIP_TRANSITIONS)


def transition_stop(stop, new_status):
    _transition(stop, new_status, STOP_TRANSITIONS)
