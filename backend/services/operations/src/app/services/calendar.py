"""Operating-day lookups shared by the order and deferral routers."""

from __future__ import annotations


import datetime as dt
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.db.models.reference import CalendarDay


def previous_operating_day(db: Session, day: dt.date) -> Optional[dt.date]:
    """The latest operating calendar day before `day`, or None if the calendar has none."""
    row = (
        db.query(CalendarDay)
        .filter(CalendarDay.date < day, CalendarDay.is_operating.is_(True))
        .order_by(CalendarDay.date.desc())
        .first()
    )
    return row.date if row else None


def next_operating_day(db: Session, after: dt.date) -> dt.date:
    day = after
    for _ in range(370):
        day += dt.timedelta(days=1)
        row = db.get(CalendarDay, day)
        if (row is not None and row.is_operating) or (row is None and day.weekday() != 6):
            return day
    raise ValueError("No operating day is configured within the next year")
