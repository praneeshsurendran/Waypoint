"""Serialize one operating day's mutations without locking unrelated runs."""

from datetime import date
from sqlalchemy.orm import Session

from sqlalchemy import text


def lock_run(db: Session, day: date) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "waypoint-run:" + str(day)},
        )
