"""Operations-owned reliability records; persisted alongside each business transaction."""

from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.base import Base


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    envelope: Mapped[dict] = mapped_column(JSON)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Inbox(Base):
    __tablename__ = "inbox"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64))


class IntakeClosure(Base):
    __tablename__ = "intake_closures"
    delivery_date: Mapped[date] = mapped_column(Date, primary_key=True)
    order_snapshot: Mapped[list] = mapped_column(JSON)
    closed_by: Mapped[int | None] = mapped_column(Integer)
    closed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class PlanningJob(Base):
    __tablename__ = "planning_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_key: Mapped[str] = mapped_column(String(100), unique=True)
    delivery_date: Mapped[date] = mapped_column(Date)
    requested_by: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    plan_id: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class DeviceOperation(Base):
    __tablename__ = "device_operations"
    client_op_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    actor_id: Mapped[int] = mapped_column(Integer)
    stop_id: Mapped[int] = mapped_column(Integer)
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


Index(
    "ix_device_operations_device_sequence",
    DeviceOperation.actor_id,
    DeviceOperation.payload["device_id"].as_string(),
    DeviceOperation.payload["device_sequence"].as_integer(),
)


class DeviceCursor(Base):
    __tablename__ = "device_cursors"
    actor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer)


class ProofObject(Base):
    __tablename__ = "proof_objects"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer)
    stop_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stops.id"))
    content_type: Mapped[str] = mapped_column(String(50))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ProjectionVersion(Base):
    __tablename__ = "projection_versions"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
