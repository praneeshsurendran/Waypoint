"""Serialize one operating day's mutations without locking unrelated runs."""

from sqlalchemy import text


def lock_run(db, day):
    if db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "waypoint-run:" + str(day)},
        )
