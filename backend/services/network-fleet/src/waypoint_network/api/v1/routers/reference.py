from __future__ import annotations
from waypoint_contracts.reference import VehicleAvailability
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_network.api.dependencies import require_role
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Query
from waypoint_network.api.dependencies import CurrentUser, DbDep
from waypoint_contracts.reference import CalendarDayOut, DepotOut, OutletOut, VehicleOut
from waypoint_network.application.use_cases import reference as use_cases

from waypoint_network.infrastructure.cache import cached_reference

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/depots", response_model=list[DepotOut])
def list_depots(db: DbDep, _: CurrentUser) -> list[DepotOut]:
    return TypeAdapter(list[DepotOut]).validate_python(
        cached_reference(
            _,
            "list_depots",
            {},
            TypeAdapter(list[DepotOut]),
            lambda: use_cases.list_depots(db=db, _=_),
        )
    )


@router.get("/outlets", response_model=list[OutletOut])
def list_outlets(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
) -> list[OutletOut]:
    return TypeAdapter(list[OutletOut]).validate_python(
        cached_reference(
            _,
            "list_outlets",
            {"depot": depot, "brand": brand, "district": district},
            TypeAdapter(list[OutletOut]),
            lambda: use_cases.list_outlets(
                db=db, _=_, depot=depot, brand=brand, district=district
            ),
        )
    )


@router.get("/outlets/{outlet_id}", response_model=OutletOut)
def get_outlet(outlet_id: str, db: DbDep, _: CurrentUser) -> OutletOut:
    return TypeAdapter(OutletOut).validate_python(
        cached_reference(
            _,
            "get_outlet",
            {"outlet_id": outlet_id},
            TypeAdapter(OutletOut),
            lambda: use_cases.get_outlet(outlet_id=outlet_id, db=db, _=_),
        )
    )


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(
    db: DbDep,
    _: CurrentUser,
    depot: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    refrigerated: Optional[bool] = Query(None),
) -> list[VehicleOut]:
    return TypeAdapter(list[VehicleOut]).validate_python(
        cached_reference(
            _,
            "list_vehicles",
            {"depot": depot, "type": type, "refrigerated": refrigerated},
            TypeAdapter(list[VehicleOut]),
            lambda: use_cases.list_vehicles(
                db=db, _=_, depot=depot, type=type, refrigerated=refrigerated
            ),
        )
    )


@router.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: str, db: DbDep, _: CurrentUser) -> VehicleOut:
    return TypeAdapter(VehicleOut).validate_python(
        cached_reference(
            _,
            "get_vehicle",
            {"vehicle_id": vehicle_id},
            TypeAdapter(VehicleOut),
            lambda: use_cases.get_vehicle(vehicle_id=vehicle_id, db=db, _=_),
        )
    )


@router.get("/calendar", response_model=list[CalendarDayOut])
def list_calendar(
    db: DbDep,
    _: CurrentUser,
    from_: Optional[dt.date] = Query(None, alias="from"),
    to: Optional[dt.date] = Query(None),
    operating_only: bool = Query(False),
) -> list[CalendarDayOut]:
    return TypeAdapter(list[CalendarDayOut]).validate_python(
        cached_reference(
            _,
            "list_calendar",
            {
                "from_": from_.isoformat() if from_ else None,
                "to": to.isoformat() if to else None,
                "operating_only": operating_only,
            },
            TypeAdapter(list[CalendarDayOut]),
            lambda: use_cases.list_calendar(
                db=db, _=_, from_=from_, to=to, operating_only=operating_only
            ),
        )
    )


@router.patch("/vehicles/{vehicle_id}/availability", response_model=VehicleOut)
def set_availability(
    vehicle_id: str,
    body: VehicleAvailability,
    db: DbDep,
    user: CurrentUser,
    _: Annotated[Actor, require_role("ADMIN", "DISPATCHER")],
) -> VehicleOut:
    return TypeAdapter(VehicleOut).validate_python(
        use_cases.set_availability(vehicle_id, body, db, user)
    )
