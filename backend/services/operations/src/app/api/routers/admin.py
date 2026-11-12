from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_contracts.runtime import (
    CapacityForecast,
    ClockResult,
    DailySummary,
    EventPage,
    FuelSummary,
)
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Query, status
from waypoint_contracts.runtime import ClockAdvanceRequest
from app.api.deps import CurrentUser, DbDep, require_role
from app.application.use_cases import admin as use_cases

router = APIRouter(prefix="/admin", tags=["admin"])
_DISPATCHER = require_role("DISPATCHER")


@router.post(
    "/clock",
    status_code=status.HTTP_200_OK,
    response_model=ClockResult,
    response_model_exclude_unset=True,
)
def advance_clock(
    body: ClockAdvanceRequest, current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> ClockResult:
    """Advance the business date for demo purposes."""
    return TypeAdapter(ClockResult).validate_python(
        use_cases.advance_clock(body=body, current_user=current_user, _=None)
    )


@router.get("/clock", response_model=ClockResult, response_model_exclude_unset=True)
def get_clock(current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]) -> ClockResult:
    return TypeAdapter(ClockResult).validate_python(
        use_cases.get_clock(current_user=current_user, _=None)
    )


@router.get("/events/poll", response_model=EventPage, response_model_exclude_unset=True)
def poll_events(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    since: Optional[dt.datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    cursor: int | None = Query(None, ge=0),
) -> EventPage:
    """Returns recent audit events. Used by the dispatcher monitor for live updates."""
    return TypeAdapter(EventPage).validate_python(
        use_cases.poll_events(
            db=db, current_user=current_user, _=None, since=since, limit=limit, cursor=cursor
        )
    )


@router.get(
    "/capacity/forecast", response_model=CapacityForecast, response_model_exclude_unset=True
)
def capacity_forecast(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    date: Optional[dt.date] = Query(None),
) -> CapacityForecast:
    """Demand vs fleet capacity summary for the given date.
    Breakdown by depot, temperature class, and vehicle type."""
    return TypeAdapter(CapacityForecast).validate_python(
        use_cases.capacity_forecast(db=db, current_user=current_user, _=None, date=date)
    )


@router.get("/analytics/daily", response_model=DailySummary, response_model_exclude_unset=True)
def daily_summary(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    date: Optional[dt.date] = Query(None),
) -> DailySummary:
    """Summary of delivery performance for a completed day."""
    return TypeAdapter(DailySummary).validate_python(
        use_cases.daily_summary(db=db, current_user=current_user, _=None, date=date)
    )


@router.get("/analytics/fuel", response_model=FuelSummary, response_model_exclude_unset=True)
def fuel_summary(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    iso_year: Optional[int] = Query(None),
    iso_week: Optional[int] = Query(None),
) -> FuelSummary:
    """Per-vehicle fuel usage vs quota for the specified ISO week."""
    return TypeAdapter(FuelSummary).validate_python(
        use_cases.fuel_summary(
            db=db, current_user=current_user, _=None, iso_year=iso_year, iso_week=iso_week
        )
    )
