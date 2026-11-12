"""Loading router — loader views trips and flags/releases them."""

from __future__ import annotations
import datetime as dt
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session as DbDep
from waypoint_security import Principal as CurrentUser
from app.infrastructure.db.models.loading import LoadCheck
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.plan import Plan, Stop, StopOrder, Trip
from app.infrastructure.db.models.reference import Vehicle
from waypoint_contracts.plan import LoadFlagIn
from app.services.audit import log_action
from app.services.state_machine import transition_trip


_LOADER = None
_READ_ROLES = None


def list_loading_trips(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _READ_ROLES,
    date: Optional[dt.date] = None,
    depot: Optional[str] = None,
):
    q = (
        db.query(Trip)
        .join(Plan, Trip.plan_id == Plan.id)
        .options(selectinload(Trip.stops), selectinload(Trip.load_checks))
    )
    if date:
        q = q.filter(Plan.delivery_date == date)
    if current_user.role == "DRIVER":
        if current_user.vehicle_id:
            q = q.filter(Trip.vehicle_id == current_user.vehicle_id)
        else:
            return []
    elif current_user.role == "LOADER" and (not current_user.depot_id):
        return []
    elif current_user.role == "LOADER" and current_user.depot_id:
        q = q.join(Vehicle, Trip.vehicle_id == Vehicle.vehicle_id).filter(
            Vehicle.depot_code == current_user.depot_id
        )
    elif depot:
        q = q.join(Vehicle, Trip.vehicle_id == Vehicle.vehicle_id).filter(
            Vehicle.depot_code == depot
        )
    return q.order_by(Trip.planned_depart).all()


def get_loading_trip(trip_id: int, db: DbDep, current_user: CurrentUser, _: None = _READ_ROLES):
    trip = db.get(Trip, trip_id, options=[selectinload(Trip.stops), selectinload(Trip.load_checks)])
    if not trip:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Trip not found."}
        )
    from app.application.use_cases.delivery import authorize_trip

    authorize_trip(db, trip, current_user)
    trip.stops.sort(key=lambda s: s.sequence, reverse=True)
    return trip


def flag_load(
    trip_id: int, body: LoadFlagIn, db: DbDep, current_user: CurrentUser, _: None = _LOADER
):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Trip not found."}
        )
    from app.application.use_cases.delivery import authorize_trip

    authorize_trip(db, trip, current_user)
    if trip.status not in ("PLANNED", "LOADING"):
        raise HTTPException(
            409, detail={"code": "LOAD_FINALIZED", "message": "This load has already left loading."}
        )
    if body.order_id is not None:
        belongs = (
            db.query(StopOrder)
            .join(Stop, StopOrder.stop_id == Stop.id)
            .filter(Stop.trip_id == trip.id, StopOrder.order_id == body.order_id)
            .first()
        )
        if not belongs:
            raise HTTPException(
                422,
                detail={
                    "code": "ORDER_TRIP_MISMATCH",
                    "message": "Order does not belong to this trip.",
                },
            )
    check = LoadCheck(
        trip_id=trip_id,
        order_id=body.order_id,
        status=body.status,
        note=body.note,
        photo_path=body.photo_path,
        flagged_by=current_user.id,
    )
    db.add(check)
    log_action(
        db,
        "LOAD_FLAG",
        "Trip",
        trip_id,
        actor_user_id=current_user.id,
        after={"status": body.status, "order_id": body.order_id, "photo_path": body.photo_path},
    )
    db.commit()
    return {"ok": True}


def start_loading_trip(trip_id: int, db: DbDep, current_user: CurrentUser, _: None = _LOADER):
    """Mark that vehicle loading has physically started at the bay (PLANNED -> LOADING)."""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Trip not found."}
        )
    from app.application.use_cases.delivery import authorize_trip

    authorize_trip(db, trip, current_user)
    before = {"status": trip.status}
    transition_trip(trip, "LOADING")
    log_action(
        db,
        "START_LOADING_TRIP",
        "Trip",
        trip_id,
        actor_user_id=current_user.id,
        before=before,
        after={"status": trip.status},
    )
    db.commit()
    return {"ok": True, "status": trip.status}


def release_trip(trip_id: int, db: DbDep, current_user: CurrentUser, _: None = _LOADER):
    """Release vehicle after loading is complete (PLANNED/LOADING -> LOADED)."""
    trip = db.get(Trip, trip_id, options=[selectinload(Trip.stops)])
    if not trip:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Trip not found."}
        )
    from app.application.use_cases.delivery import authorize_trip

    authorize_trip(db, trip, current_user)
    before = {"status": trip.status}
    checks = db.query(LoadCheck).filter(LoadCheck.trip_id == trip.id).order_by(LoadCheck.id).all()
    latest = {check.order_id: check.status for check in checks}
    if any((status in ("MISSING", "DAMAGED") for status in latest.values())):
        raise HTTPException(
            409,
            detail={
                "code": "UNRESOLVED_SHORTFALL",
                "message": "Resolve shortages or damage and record an OK check before departure.",
            },
        )
    transition_trip(trip, "LOADED")
    for stop in trip.stops:
        for so in db.query(StopOrder).filter(StopOrder.stop_id == stop.id).all():
            order = db.get(Order, so.order_id)
            if order and order.status == "PLANNED":
                order.status = "LOADED"
    log_action(
        db,
        "RELEASE_TRIP",
        "Trip",
        trip_id,
        actor_user_id=current_user.id,
        before=before,
        after={"status": trip.status},
    )
    db.commit()
    return {"ok": True, "status": trip.status}
