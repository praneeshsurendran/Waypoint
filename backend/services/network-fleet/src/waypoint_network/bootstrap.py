from collections.abc import Iterator
from sqlalchemy.orm import Session
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from waypoint_network.infrastructure.db.models import Base as Base
from waypoint_network.infrastructure.db import reference as reference, audit as audit
from waypoint_network.infrastructure.messaging.outbox import install

from waypoint_security import validate_runtime

validate_runtime()

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True,
    hide_parameters=True,
    pool_size=5,
    max_overflow=5,
    pool_timeout=5,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


install(SessionLocal)
