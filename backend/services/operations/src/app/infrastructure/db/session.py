from __future__ import annotations
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


def _make_engine() -> Engine:
    settings = get_settings()
    from waypoint_security import validate_runtime

    validate_runtime()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        echo=False,
        pool_size=settings.pool_size,
        max_overflow=settings.pool_max_overflow,
        pool_timeout=5,
    )


# Module-level engine and session factory (created lazily on first import after config is ready)
engine = _make_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session and close it when done."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
