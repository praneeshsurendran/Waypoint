from app.infrastructure.db.models.reference import (
    Depot,
    Outlet,
    Vehicle,
    CalendarDay,
    VehicleWeeklyFuel,
)
from app.infrastructure.db.models.user import User
from app.infrastructure.db.models.order import Order, OrderLine
from app.infrastructure.db.models.plan import Plan, Trip, Stop, StopOrder
from app.infrastructure.db.models.deferral import Deferral
from app.infrastructure.db.models.loading import LoadCheck
from app.infrastructure.db.models.delivery import DeliveryEvent
from app.infrastructure.db.models.receipt import Receipt
from app.infrastructure.db.models.issue import Issue
from app.infrastructure.db.models.notification import Notification
from app.infrastructure.db.models.audit import AuditLog
from app.infrastructure.db.models.position import VehiclePosition

__all__ = [
    "Depot",
    "Outlet",
    "Vehicle",
    "CalendarDay",
    "VehicleWeeklyFuel",
    "User",
    "Order",
    "OrderLine",
    "Plan",
    "Trip",
    "Stop",
    "StopOrder",
    "Deferral",
    "LoadCheck",
    "DeliveryEvent",
    "Receipt",
    "Issue",
    "Notification",
    "AuditLog",
    "VehiclePosition",
]
