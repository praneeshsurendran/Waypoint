"""User model."""

from __future__ import annotations


import datetime as dt
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from waypoint_identity.infrastructure.db.models import Base

ROLES = ("DISPATCHER", "LOADER", "DRIVER", "STORE_MANAGER", "ADMIN")


class User(Base):
    auth_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('DISPATCHER','LOADER','DRIVER','STORE_MANAGER','ADMIN')",
            name="role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(
        String(200), unique=True, nullable=True
    )
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    phone: Mapped[Optional[str]] = mapped_column(String(30), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Role-specific links (nullable)
    outlet_id: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )
    vehicle_id: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )
    depot_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
