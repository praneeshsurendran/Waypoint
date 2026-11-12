from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class Notification(Base):
    __tablename__ = "notifications"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    aggregate_id: Mapped[str] = mapped_column(String(200))
    outlet_id: Mapped[str | None] = mapped_column(String(20), index=True)
    depot_id: Mapped[str | None] = mapped_column(String(50), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(20), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReadReceipt(Base):
    __tablename__ = "notification_reads"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class DeliveryLog(Base):
    __tablename__ = "notification_delivery_log"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    channel: Mapped[str] = mapped_column(String(30), default="in_app")
    status: Mapped[str] = mapped_column(String(30), default="delivered")
    attempts: Mapped[int] = mapped_column(Integer, default=1)
