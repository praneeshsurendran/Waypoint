"""Reference data router: outlets, vehicles, depots, calendar."""

from __future__ import annotations

from waypoint_contracts.reference import VehicleAvailability
from pydantic import TypeAdapter
from typing import Optional
from waypoint_contracts.reference import CalendarDayOut, DepotOut, OutletOut, VehicleOut

import datetime as dt

from sqlalchemy.orm import Session as DbDep
from waypoint_security import Principal as CurrentUser
from waypoint_network.infrastructure.db.reference import (
    CalendarDay,
    Depot,
    Outlet,
    Vehicle,
)


def list_depots(db: DbDep, _: CurrentUser) -> list[DepotOut]:
    return TypeAdapter(list[DepotOut]).validate_python(db.query(Depot).all())


def list_outlets(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = None,
    brand: Optional[str] = None,
    district: Optional[str] = None,
) -> list[OutletOut]:
    q = db.query(Outlet)
    if depot:
        q = q.filter(Outlet.depot_code == depot)
    if brand:
        q = q.filter(Outlet.brand == brand)
    if district:
        q = q.filter(Outlet.district == district)
    return TypeAdapter(list[OutletOut]).validate_python(q.all())


def get_outlet(outlet_id: str, db: DbDep, _: CurrentUser) -> OutletOut:
    outlet = db.get(Outlet, outlet_id)
    if not outlet:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Outlet not found."},
        )
    return TypeAdapter(OutletOut).validate_python(outlet)


def list_vehicles(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = None,
    type: Optional[str] = None,
    refrigerated: Optional[bool] = None,
) -> list[VehicleOut]:
    q = db.query(Vehicle)
    if depot:
        q = q.filter(Vehicle.depot_code == depot)
    if type:
        q = q.filter(Vehicle.type == type)
    if refrigerated is not None:
        q = q.filter(Vehicle.is_refrigerated == refrigerated)
    return TypeAdapter(list[VehicleOut]).validate_python(q.all())


def get_vehicle(vehicle_id: str, db: DbDep, _: CurrentUser) -> VehicleOut:
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vehicle not found."},
        )
    return TypeAdapter(VehicleOut).validate_python(vehicle)


def list_calendar(
    db: DbDep,
    _: CurrentUser,
    from_: Optional[dt.date] = None,
    to: Optional[dt.date] = None,
    operating_only: bool = False,
) -> list[CalendarDayOut]:
    q = db.query(CalendarDay)
    if from_:
        q = q.filter(CalendarDay.date >= from_)
    if to:
        q = q.filter(CalendarDay.date <= to)
    if operating_only:
        q = q.filter(CalendarDay.is_operating.is_(True))
    return TypeAdapter(list[CalendarDayOut]).validate_python(
        q.order_by(CalendarDay.date).all()
    )


def set_availability(
    vehicle_id: str, body: VehicleAvailability, db: DbDep, user: CurrentUser
) -> VehicleOut:
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
    return TypeAdapter(VehicleOut).validate_python(vehicle)
