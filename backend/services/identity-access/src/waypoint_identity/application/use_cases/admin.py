from __future__ import annotations
from pydantic import TypeAdapter
from typing import Optional
from waypoint_contracts.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    PasswordReset,
    TripReassign,
)

from typing import NoReturn
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbDep
from waypoint_identity.core.security import hash_password
from waypoint_identity.infrastructure.db.projections import Trip
from waypoint_identity.infrastructure.db.projections import Depot, Outlet, Vehicle
from waypoint_identity.infrastructure.db.accounts import ROLES, User
from waypoint_identity.infrastructure.db.audit import log_action


_ADMIN = None


def _fail(
    code: str, message: str, http: int = status.HTTP_422_UNPROCESSABLE_CONTENT
) -> NoReturn:
    raise HTTPException(status_code=http, detail={"code": code, "message": message})


def _snapshot(user: User) -> dict:
    return {
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "outlet_id": user.outlet_id,
        "vehicle_id": user.vehicle_id,
        "depot_id": user.depot_id,
    }


def _check_links(
    db: DbDep,
    role: str,
    outlet_id: str | None,
    vehicle_id: str | None,
    depot_id: str | None,
) -> None:
    if role not in ROLES:
        _fail("INVALID_ROLE", f"Role must be one of {', '.join(ROLES)}.")
    if outlet_id and (not db.get(Outlet, outlet_id)):
        _fail("UNKNOWN_OUTLET", f"Outlet {outlet_id} does not exist.")
    if vehicle_id and (not db.get(Vehicle, vehicle_id)):
        _fail("UNKNOWN_VEHICLE", f"Vehicle {vehicle_id} does not exist.")
    if depot_id and (not db.get(Depot, depot_id)):
        _fail("UNKNOWN_DEPOT", f"Depot {depot_id} does not exist.")
    if role == "STORE_MANAGER" and (not outlet_id):
        _fail("OUTLET_REQUIRED", "A store manager needs an outlet.")
    if role == "DRIVER" and (not vehicle_id):
        _fail("VEHICLE_REQUIRED", "A driver needs a vehicle.")


def _check_unique(
    db: DbDep,
    user_id: Optional[int],
    username: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> None:
    for column, value, label in (
        (User.username, username, "username"),
        (User.email, email, "email address"),
        (User.phone, phone, "mobile number"),
    ):
        if not value:
            continue
        query = db.query(User).filter(column == value)
        if user_id is not None:
            query = query.filter(User.id != user_id)
        if query.first():
            _fail(
                "DUPLICATE",
                f"That {label} is already in use.",
                status.HTTP_409_CONFLICT,
            )


def _out(db: DbDep, user: User, trips: dict[str, int] | None = None) -> AdminUserOut:
    """The account, with whether its vehicle is on a trip that has left the depot."""
    out = AdminUserOut.model_validate(user)
    if user.role == "DRIVER" and user.vehicle_id:
        if trips is None:
            trips = _trips_in_transit(db)
        if user.vehicle_id in trips:
            out.on_route = True
            out.trip_number = trips[user.vehicle_id]
    return out


def _trips_in_transit(db: DbDep) -> dict[str, int]:
    rows = (
        db.query(Trip.vehicle_id, Trip.trip_number)
        .filter(Trip.status == "IN_TRANSIT")
        .all()
    )
    return {vehicle_id: number for vehicle_id, number in rows}


def list_users(db: DbDep, _: object = _ADMIN) -> list[AdminUserOut]:
    trips = _trips_in_transit(db)
    return TypeAdapter(list[AdminUserOut]).validate_python(
        [_out(db, user, trips) for user in db.query(User).order_by(User.id).all()]
    )


def create_user(body: AdminUserCreate, db: DbDep, admin: User) -> AdminUserOut:
    username = body.username.strip()
    if not username or not body.full_name.strip():
        _fail("INVALID_INPUT", "A name and a username are required.")
    if not 8 <= len(body.password.encode()) <= 72:
        _fail("WEAK_PASSWORD", "The temporary password must be between 8 and 72 bytes.")
    email = body.email.strip().lower()
    phone = (body.phone or "").strip() or None
    _check_unique(db, None, username, email, phone)
    _check_links(db, body.role, body.outlet_id, body.vehicle_id, body.depot_id)
    user = User(
        username=username,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        email=email,
        phone=phone,
        role=body.role,
        outlet_id=body.outlet_id,
        vehicle_id=body.vehicle_id,
        depot_id=body.depot_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_action(db, "USER_CREATED", "user", user.id, admin.id, after=_snapshot(user))
    db.commit()
    db.refresh(user)
    return TypeAdapter(AdminUserOut).validate_python(_out(db, user))


def update_user(
    user_id: int, body: AdminUserUpdate, db: DbDep, admin: User
) -> AdminUserOut:
    user = db.get(User, user_id)
    if not user:
        _fail("NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
    changes = body.model_dump(exclude_unset=True)
    reason = (changes.pop("reason", None) or "").strip()
    if changes.get("is_active") is False and user.id == admin.id:
        _fail("SELF_SUSPEND", "You cannot suspend your own account.")
    if changes.get("email"):
        changes["email"] = changes["email"].strip().lower()
    if "phone" in changes:
        changes["phone"] = (changes["phone"] or "").strip() or None
    _check_unique(db, user.id, email=changes.get("email"), phone=changes.get("phone"))
    before = _snapshot(user)
    for field, value in changes.items():
        if field in ("full_name", "role", "is_active") and value is None:
            continue
        setattr(user, field, value)
    _check_links(db, user.role, user.outlet_id, user.vehicle_id, user.depot_id)
    action = "USER_UPDATED"
    after = _snapshot(user)
    if changes.get("is_active") is False:
        user.auth_version += 1
        action = "USER_SUSPENDED"
        if reason:
            after["reason"] = reason
    elif changes.get("is_active") is True and (not before["is_active"]):
        action = "USER_REACTIVATED"
    log_action(db, action, "user", user.id, admin.id, before=before, after=after)
    db.commit()
    db.refresh(user)
    return TypeAdapter(AdminUserOut).validate_python(_out(db, user))


def reassign_trip(user_id: int, body: TripReassign, db: DbDep, admin: User) -> None:
    """Hands a driver's vehicle, and so the trip on it, to another driver at the same depot."""
    source = db.get(User, user_id)
    target = db.get(User, body.to_user_id)
    if not source or not target or source.id == target.id:
        _fail("NOT_FOUND", "Choose two different drivers.", status.HTTP_404_NOT_FOUND)
    if source.role != "DRIVER" or target.role != "DRIVER" or (not source.vehicle_id):
        _fail(
            "NOT_A_DRIVER",
            "Both people must be drivers, and the first needs a vehicle.",
        )
    if not target.is_active:
        _fail("INACTIVE_USER", "That driver is suspended.")
    trips = _trips_in_transit(db)
    if target.vehicle_id and target.vehicle_id in trips:
        _fail("ON_ROUTE", "That driver is already on a trip.")
    before = {
        "from": source.username,
        "to": target.username,
        "vehicle_id": source.vehicle_id,
    }
    target.vehicle_id, source.vehicle_id = (source.vehicle_id, target.vehicle_id)
    log_action(
        db,
        "TRIP_REASSIGNED",
        "user",
        source.id,
        admin.id,
        before=before,
        after={
            "username": source.username,
            "to": target.username,
            "vehicle_id": target.vehicle_id,
        },
    )
    db.commit()


def reset_password(user_id: int, body: PasswordReset, db: DbDep, admin: User) -> None:
    user = db.get(User, user_id)
    if not user:
        _fail("NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
    if not 8 <= len(body.password.encode()) <= 72:
        _fail("WEAK_PASSWORD", "The temporary password must be between 8 and 72 bytes.")
    user.password_hash = hash_password(body.password)
    user.auth_version += 1
    log_action(db, "PASSWORD_RESET", "user", user.id, admin.id, after=_snapshot(user))
    db.commit()
