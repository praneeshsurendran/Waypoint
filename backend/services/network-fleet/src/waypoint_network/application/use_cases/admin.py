from __future__ import annotations
import re
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbDep
from waypoint_network.infrastructure.db.reference import Depot, Outlet, Vehicle
from waypoint_security import Principal as User
from waypoint_contracts.admin import OutletCreate, VehicleCreate
from waypoint_network.infrastructure.db.audit import log_action


_ADMIN = None


def _fail(code: str, message: str, http: int = status.HTTP_422_UNPROCESSABLE_CONTENT):
    raise HTTPException(status_code=http, detail={"code": code, "message": message})


def _next_id(db, column, prefix: str, width: int = 3) -> str:
    highest = 0
    for (value,) in db.query(column).all():
        match = re.fullmatch(f"{prefix}(\\d+)", value or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}{highest + 1:0{width}d}"


def create_outlet(body: OutletCreate, db: DbDep, admin: User = _ADMIN):
    _identifier_lock(db, "OUT")
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
        body.parking_constraint
        if body.parking_constraint in ("van_only", "narrow_lane")
        else None
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
    return outlet


def create_vehicle(body: VehicleCreate, db: DbDep, admin: User = _ADMIN):
    _identifier_lock(db, "VEH")
    if body.type not in ("truck", "van"):
        _fail("INVALID_TYPE", "Type must be truck or van.")
    if body.is_refrigerated and body.brand != "Fresh":
        _fail("REEFER_FRESH_ONLY", "Only Fresh vehicles can be refrigerated.")
    if not db.get(Depot, body.depot_code):
        _fail("UNKNOWN_DEPOT", f"Depot {body.depot_code} does not exist.")
    if not 100 <= body.weight_cap_kg <= 20000 or not 0.5 <= body.volume_cap_m3 <= 60:
        _fail("INVALID_CAPACITY", "Capacity is outside the usual range.")
    registration = (body.registration or "").strip().upper() or None
    if (
        registration
        and db.query(Vehicle).filter(Vehicle.registration == registration).first()
    ):
        _fail(
            "DUPLICATE",
            "That registration is already in use.",
            status.HTTP_409_CONFLICT,
        )
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
    return vehicle


def _identifier_lock(db, prefix):
    from sqlalchemy import text

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {"key": "network-id:" + prefix},
    )
