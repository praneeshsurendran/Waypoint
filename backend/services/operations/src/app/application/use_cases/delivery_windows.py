from sqlalchemy.orm import Session
from waypoint_security import Actor
from waypoint_contracts.runtime import CreatedResult
from datetime import datetime, time
from uuid import uuid5, NAMESPACE_URL
from zoneinfo import ZoneInfo
from app.core import clock
from app.infrastructure.db.models.plan import Stop, Trip, Plan
from app.infrastructure.db.models.reference import Outlet
from app.infrastructure.messaging.models import Outbox
from app.infrastructure.messaging.outbox import enqueue
from .delivery import authorize_trip, trip_payload


def check(db: Session, user: Actor) -> CreatedResult:
    query = (
        db.query(Stop)
        .join(Trip, Trip.id == Stop.trip_id)
        .join(Plan, Plan.id == Trip.plan_id)
        .filter(
            Trip.status == "IN_TRANSIT",
            Plan.status == "PUBLISHED",
            Stop.status.in_(["PENDING", "ARRIVED"]),
        )
    )
    if user.role == "DRIVER":
        if not user.vehicle_id:
            return CreatedResult(created=0)
        query = query.filter(Trip.vehicle_id == user.vehicle_id)
    count = 0
    for stop in query.order_by(Stop.id).with_for_update(of=Stop).all():
        trip = db.get(Trip, stop.trip_id)
        authorize_trip(db, trip, user)
        if trip is None:
            raise ValueError("delivery stop references a missing trip")
        outlet = db.get(Outlet, stop.outlet_id)
        plan = db.get(Plan, trip.plan_id)
        if outlet is None or plan is None:
            raise ValueError("delivery references missing planning data")
        closes = outlet.mall_window_close if outlet.is_mall else outlet.window_close_time
        if outlet.brand == "Fresh":
            closes = min(closes or time(8), time(8))
        if closes is None:
            continue
        deadline = datetime.combine(plan.delivery_date, closes, tzinfo=ZoneInfo("Asia/Colombo"))
        if clock.now() <= deadline:
            continue
        event_id = uuid5(NAMESPACE_URL, f"waypoint:deadline:{stop.id}")
        if db.get(Outbox, str(event_id)):
            continue
        enqueue(
            db,
            "delivery.delayed",
            stop.id,
            {
                **trip_payload(db, trip),
                "stop_id": stop.id,
                "outlet_id": stop.outlet_id,
                "note": "Delivery is past the receiving window.",
                "kind": "deadline",
            },
            event_id=event_id,
        )
        count += 1
    db.commit()
    return CreatedResult(created=count)
