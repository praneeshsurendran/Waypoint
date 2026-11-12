from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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


class ProjectionVersion(Base):
    __tablename__ = "projection_versions"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
