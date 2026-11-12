from __future__ import annotations
from fastapi import APIRouter, status
from waypoint_identity.api.dependencies import DbDep, require_role
from waypoint_identity.infrastructure.db.accounts import User
from waypoint_contracts.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    PasswordReset,
    TripReassign,
)
from waypoint_identity.application.use_cases import admin as use_cases

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
