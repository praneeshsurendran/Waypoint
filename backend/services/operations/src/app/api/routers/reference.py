from __future__ import annotations
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Query
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.reference import CalendarDayOut, DepotOut, OutletOut, VehicleOut
from app.application.use_cases import reference as use_cases

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/depots", response_model=list[DepotOut])
def list_depots(db: DbDep, _: CurrentUser):
    return use_cases.list_depots(db=db, _=_)


@router.get("/outlets", response_model=list[OutletOut])
def list_outlets(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
):
    return use_cases.list_outlets(db=db, _=_, depot=depot, brand=brand, district=district)


@router.get("/outlets/{outlet_id}", response_model=OutletOut)
def get_outlet(outlet_id: str, db: DbDep, _: CurrentUser):
    return use_cases.get_outlet(outlet_id=outlet_id, db=db, _=_)


@router.get("/store-managers")
def list_store_managers(db: DbDep, _: object = require_role("DISPATCHER", "DRIVER", "LOADER")):
    """Who receives at each outlet, so a driver or dispatcher can call ahead. Names and phones only."""
    return use_cases.list_store_managers(db=db, _=_)


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    refrigerated: Optional[bool] = Query(None),
):
    return use_cases.list_vehicles(db=db, _=_, depot=depot, type=type, refrigerated=refrigerated)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: str, db: DbDep, _: CurrentUser):
    return use_cases.get_vehicle(vehicle_id=vehicle_id, db=db, _=_)


@router.get("/calendar", response_model=list[CalendarDayOut])
def list_calendar(
    db: DbDep,
    _: CurrentUser,
    from_: Optional[dt.date] = Query(None, alias="from"),
    to: Optional[dt.date] = Query(None),
    operating_only: bool = Query(False),
):
    return use_cases.list_calendar(db=db, _=_, from_=from_, to=to, operating_only=operating_only)
