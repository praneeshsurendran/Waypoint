from __future__ import annotations
from fastapi import APIRouter, Query, status
from app.api.deps import DbDep, require_role
from app.infrastructure.db.models.user import User
from waypoint_contracts.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    AuditOut,
    OutletCreate,
    PasswordReset,
    TripReassign,
    VehicleCreate,
)
from waypoint_contracts.reference import OutletOut, VehicleOut
from app.application.use_cases import people as use_cases

router = APIRouter(prefix="/admin", tags=["admin"])
_ADMIN = require_role("ADMIN")


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: DbDep, _: object = _ADMIN):
    return use_cases.list_users(db=db, _=_)


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: AdminUserCreate, db: DbDep, admin: User = _ADMIN):
    return use_cases.create_user(body=body, db=db, admin=admin)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, body: AdminUserUpdate, db: DbDep, admin: User = _ADMIN):
    return use_cases.update_user(user_id=user_id, body=body, db=db, admin=admin)


@router.post("/users/{user_id}/reassign-trip", status_code=status.HTTP_204_NO_CONTENT)
def reassign_trip(user_id: int, body: TripReassign, db: DbDep, admin: User = _ADMIN):
    """Hands a driver's vehicle, and so the trip on it, to another driver at the same depot."""
    return use_cases.reassign_trip(user_id=user_id, body=body, db=db, admin=admin)


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(user_id: int, body: PasswordReset, db: DbDep, admin: User = _ADMIN):
    return use_cases.reset_password(user_id=user_id, body=body, db=db, admin=admin)


@router.post("/outlets", response_model=OutletOut, status_code=status.HTTP_201_CREATED)
def create_outlet(body: OutletCreate, db: DbDep, admin: User = _ADMIN):
    return use_cases.create_outlet(body=body, db=db, admin=admin)


@router.post("/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(body: VehicleCreate, db: DbDep, admin: User = _ADMIN):
    return use_cases.create_vehicle(body=body, db=db, admin=admin)


@router.get("/audit", response_model=list[AuditOut])
def list_audit(db: DbDep, limit: int = Query(200, ge=1, le=1000), _: object = _ADMIN):
    return use_cases.list_audit(db=db, limit=limit, _=_)
