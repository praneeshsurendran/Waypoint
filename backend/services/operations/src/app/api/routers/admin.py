from __future__ import annotations
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Query, status
from pydantic import BaseModel
from app.api.deps import CurrentUser, DbDep, require_role
from app.application.use_cases import admin as use_cases

router = APIRouter(prefix="/admin", tags=["admin"])
_DISPATCHER = require_role("DISPATCHER")


class ClockAdvanceRequest(BaseModel):
    business_date: str


@router.post("/clock", status_code=status.HTTP_200_OK)
def advance_clock(body: ClockAdvanceRequest, current_user: CurrentUser, _: None = _DISPATCHER):
    """Advance the business date for demo purposes."""
    return use_cases.advance_clock(body=body, current_user=current_user, _=_)


@router.get("/clock")
def get_clock(current_user: CurrentUser, _: None = _DISPATCHER):
    return use_cases.get_clock(current_user=current_user, _=_)


@router.get("/events/poll")
def poll_events(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    since: Optional[dt.datetime] = Query(None),
    limit: int = Query(50, le=200),
):
    """Returns recent audit events. Used by the dispatcher monitor for live updates."""
    return use_cases.poll_events(db=db, current_user=current_user, _=_, since=since, limit=limit)


@router.get("/capacity/forecast")
def capacity_forecast(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    date: Optional[dt.date] = Query(None),
):
    """Demand vs fleet capacity summary for the given date.
    Breakdown by depot, temperature class, and vehicle type."""
    return use_cases.capacity_forecast(db=db, current_user=current_user, _=_, date=date)


@router.get("/analytics/daily")
def daily_summary(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    date: Optional[dt.date] = Query(None),
):
    """Summary of delivery performance for a completed day."""
    return use_cases.daily_summary(db=db, current_user=current_user, _=_, date=date)


@router.get("/analytics/fuel")
def fuel_summary(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    iso_year: Optional[int] = Query(None),
    iso_week: Optional[int] = Query(None),
):
    """Per-vehicle fuel usage vs quota for the specified ISO week."""
    return use_cases.fuel_summary(
        db=db, current_user=current_user, _=_, iso_year=iso_year, iso_week=iso_week
    )
