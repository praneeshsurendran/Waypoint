"""Reference data router: outlets, vehicles, depots, calendar."""

from __future__ import annotations
import datetime as dt
from typing import Optional

from sqlalchemy.orm import Session as DbDep
from waypoint_security import Principal as CurrentUser
from waypoint_network.infrastructure.db.reference import (
    CalendarDay,
    Depot,
    Outlet,
    Vehicle,
)


def list_depots(db: DbDep, _: CurrentUser):
    return db.query(Depot).all()


def list_outlets(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = None,
    brand: Optional[str] = None,
    district: Optional[str] = None,
):
    q = db.query(Outlet)
    if depot:
        q = q.filter(Outlet.depot_code == depot)
    if brand:
        q = q.filter(Outlet.brand == brand)
    if district:
        q = q.filter(Outlet.district == district)
    return q.all()


def get_outlet(outlet_id: str, db: DbDep, _: CurrentUser):
    outlet = db.get(Outlet, outlet_id)
    if not outlet:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Outlet not found."},
        )
    return outlet


def list_vehicles(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = None,
    type: Optional[str] = None,
    refrigerated: Optional[bool] = None,
):
    q = db.query(Vehicle)
    if depot:
        q = q.filter(Vehicle.depot_code == depot)
    if type:
        q = q.filter(Vehicle.type == type)
    if refrigerated is not None:
        q = q.filter(Vehicle.is_refrigerated == refrigerated)
    return q.all()


def get_vehicle(vehicle_id: str, db: DbDep, _: CurrentUser):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vehicle not found."},
        )
    return vehicle


def list_calendar(
    db: DbDep,
    _: CurrentUser,
    from_: Optional[dt.date] = None,
    to: Optional[dt.date] = None,
    operating_only: bool = False,
):
    q = db.query(CalendarDay)
    if from_:
        q = q.filter(CalendarDay.date >= from_)
    if to:
        q = q.filter(CalendarDay.date <= to)
    if operating_only:
        q = q.filter(CalendarDay.is_operating.is_(True))
    return q.order_by(CalendarDay.date).all()


def set_availability(vehicle_id, body, db, user):
    from fastapi import HTTPException
    from waypoint_network.infrastructure.db.audit import log_action

    vehicle = db.get(Vehicle, vehicle_id, with_for_update=True)
    if not vehicle:
        raise HTTPException(
            404, detail={"code": "NOT_FOUND", "message": "Vehicle not found."}
        )
    if (
        user.role == "DISPATCHER"
        and user.depot_id
        and user.depot_id != vehicle.depot_code
    ):
        raise HTTPException(
            403,
            detail={
                "code": "FORBIDDEN",
                "message": "Vehicle belongs to another depot.",
            },
        )
    before = vehicle.status
    vehicle.status = body.status
    log_action(
        db,
        "VEHICLE_AVAILABILITY_CHANGED",
        "vehicle",
        vehicle_id,
        user.id,
        before={"status": before},
        after={"status": vehicle.status},
    )
    db.commit()
    db.refresh(vehicle)
    return vehicle
