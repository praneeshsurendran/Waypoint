from __future__ import annotations
from typing import Annotated
from pydantic import TypeAdapter

from fastapi import APIRouter, status
from waypoint_network.api.dependencies import DbDep, require_role
from waypoint_security import Principal as User
from waypoint_contracts.admin import OutletCreate, VehicleCreate
from waypoint_contracts.reference import OutletOut, VehicleOut
from waypoint_network.application.use_cases import admin as use_cases

router = APIRouter(prefix="/admin", tags=["admin"])
_ADMIN = require_role("ADMIN")


@router.post("/outlets", response_model=OutletOut, status_code=status.HTTP_201_CREATED)
def create_outlet(
    body: OutletCreate, db: DbDep, admin: Annotated[User, _ADMIN]
) -> OutletOut:
    return TypeAdapter(OutletOut).validate_python(
        use_cases.create_outlet(body=body, db=db, admin=admin)
    )


@router.post(
    "/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED
)
def create_vehicle(
    body: VehicleCreate, db: DbDep, admin: Annotated[User, _ADMIN]
) -> VehicleOut:
    return TypeAdapter(VehicleOut).validate_python(
        use_cases.create_vehicle(body=body, db=db, admin=admin)
    )
