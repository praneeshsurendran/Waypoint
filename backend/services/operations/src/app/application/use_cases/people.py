"""Administration router: people, outlets, vehicles and the audit trail."""

from __future__ import annotations

from sqlalchemy.orm import InstrumentedAttribute
from pydantic import TypeAdapter
from typing import Optional
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

import re
from typing import NoReturn
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbDep
from app.core.security import hash_password
from app.infrastructure.db.models.audit import AuditLog
from app.infrastructure.db.models.plan import Trip
from app.infrastructure.db.models.reference import Depot, Outlet, Vehicle
from app.infrastructure.db.models.user import ROLES, User
from app.services.audit import log_action


_ADMIN = None


def _fail(code: str, message: str, http: int = status.HTTP_422_UNPROCESSABLE_CONTENT) -> NoReturn:
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
    db: DbDep, role: str, outlet_id: str | None, vehicle_id: str | None, depot_id: str | None
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
            _fail("DUPLICATE", f"That {label} is already in use.", status.HTTP_409_CONFLICT)


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
    rows = db.query(Trip.vehicle_id, Trip.trip_number).filter(Trip.status == "IN_TRANSIT").all()
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


def update_user(user_id: int, body: AdminUserUpdate, db: DbDep, admin: User) -> AdminUserOut:
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
        _fail("NOT_A_DRIVER", "Both people must be drivers, and the first needs a vehicle.")
    if not target.is_active:
        _fail("INACTIVE_USER", "That driver is suspended.")
    trips = _trips_in_transit(db)
    if target.vehicle_id and target.vehicle_id in trips:
        _fail("ON_ROUTE", "That driver is already on a trip.")
    before = {"from": source.username, "to": target.username, "vehicle_id": source.vehicle_id}
    target.vehicle_id, source.vehicle_id = (source.vehicle_id, target.vehicle_id)
    log_action(
        db,
        "TRIP_REASSIGNED",
        "user",
        source.id,
        admin.id,
        before=before,
        after={"username": source.username, "to": target.username, "vehicle_id": target.vehicle_id},
    )
    db.commit()


def reset_password(user_id: int, body: PasswordReset, db: DbDep, admin: User) -> None:
    user = db.get(User, user_id)
    if not user:
        _fail("NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
    if not 8 <= len(body.password.encode()) <= 72:
        _fail("WEAK_PASSWORD", "The temporary password must be between 8 and 72 bytes.")
    user.password_hash = hash_password(body.password)
    log_action(db, "PASSWORD_RESET", "user", user.id, admin.id, after=_snapshot(user))
    db.commit()


def _next_id(db: DbDep, column: InstrumentedAttribute[str], prefix: str, width: int = 3) -> str:
    highest = 0
    for (value,) in db.query(column).all():
        match = re.fullmatch(f"{prefix}(\\d+)", value or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}{highest + 1:0{width}d}"


def create_outlet(body: OutletCreate, db: DbDep, admin: User) -> OutletOut:
    if not body.name.strip():
        _fail("INVALID_INPUT", "The outlet needs a name.")
    if body.brand not in ("Fresh", "Style", "Tech"):
        _fail("INVALID_BRAND", "Brand must be Fresh, Style or Tech.")
    if not db.get(Depot, body.depot_code):
        _fail("UNKNOWN_DEPOT", f"Depot {body.depot_code} does not exist.")
    open_minutes = body.window_open_time.hour * 60 + body.window_open_time.minute
    close_minutes = body.window_close_time.hour * 60 + body.window_close_time.minute
    if close_minutes - open_minutes < 60:
        _fail("INVALID_WINDOW", "The receiving window must be at least an hour long.")
    parking = (
        body.parking_constraint if body.parking_constraint in ("van_only", "narrow_lane") else None
    )
    outlet = Outlet(
        outlet_id=_next_id(db, Outlet.outlet_id, "OUT"),
        name=body.name.strip(),
        brand=body.brand,
        district=body.district.strip(),
        depot_code=body.depot_code,
        dock_type="street",
        parking_constraint=parking,
        van_only=parking == "van_only",
        is_mall=False,
        window_open_time=body.window_open_time,
        window_close_time=body.window_close_time,
    )
    db.add(outlet)
    db.flush()
    log_action(
        db,
        "OUTLET_CREATED",
        "outlet",
        outlet.outlet_id,
        admin.id,
        after={"name": outlet.name, "brand": outlet.brand, "depot": outlet.depot_code},
    )
    db.commit()
    db.refresh(outlet)
    return TypeAdapter(OutletOut).validate_python(outlet)


def create_vehicle(body: VehicleCreate, db: DbDep, admin: User) -> VehicleOut:
    if body.type not in ("truck", "van"):
        _fail("INVALID_TYPE", "Type must be truck or van.")
    if body.is_refrigerated and body.brand != "Fresh":
        _fail("REEFER_FRESH_ONLY", "Only Fresh vehicles can be refrigerated.")
    if not db.get(Depot, body.depot_code):
        _fail("UNKNOWN_DEPOT", f"Depot {body.depot_code} does not exist.")
    if not 100 <= body.weight_cap_kg <= 20000 or not 0.5 <= body.volume_cap_m3 <= 60:
        _fail("INVALID_CAPACITY", "Capacity is outside the usual range.")
    registration = (body.registration or "").strip().upper() or None
    if registration and db.query(Vehicle).filter(Vehicle.registration == registration).first():
        _fail("DUPLICATE", "That registration is already in use.", status.HTTP_409_CONFLICT)
    vehicle = Vehicle(
        vehicle_id=_next_id(db, Vehicle.vehicle_id, "VEH"),
        type=body.type,
        temp="reefer" if body.is_refrigerated else "ambient",
        is_refrigerated=body.is_refrigerated,
        registration=registration,
        weight_cap_kg=body.weight_cap_kg,
        volume_cap_m3=body.volume_cap_m3,
        fuel_type="diesel",
        km_per_l=6.0 if body.type == "truck" else 9.0,
        weekly_fuel_quota_l=450.0 if body.type == "truck" else 250.0,
        depot_code=body.depot_code,
    )
    db.add(vehicle)
    db.flush()
    log_action(
        db,
        "VEHICLE_CREATED",
        "vehicle",
        vehicle.vehicle_id,
        admin.id,
        after={
            "type": vehicle.type,
            "depot": vehicle.depot_code,
            "refrigerated": vehicle.is_refrigerated,
        },
    )
    db.commit()
    db.refresh(vehicle)
    return TypeAdapter(VehicleOut).validate_python(vehicle)


def list_audit(db: DbDep, limit: int = 200, _: object = _ADMIN) -> list[AuditOut]:
    rows = (
        db.query(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return TypeAdapter(list[AuditOut]).validate_python(
        [
            AuditOut(
                id=entry.id,
                at=entry.created_at,
                action=entry.action,
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                actor=username,
                before=entry.before_json,
                after=entry.after_json,
            )
            for entry, username in rows
        ]
    )
