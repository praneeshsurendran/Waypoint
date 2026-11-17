"""Import private shared references without deleting or overwriting operational history."""

from __future__ import annotations
import csv
import datetime as dt
from pathlib import Path
from sqlalchemy.orm import Session
from seed.geo import outlet_coords
from waypoint_network.infrastructure.db.reference import (
    Depot,
    Outlet,
    Vehicle,
    CalendarDay,
)


def rows(root: Path, filename: str) -> list[dict[str, str]]:
    with (root / "General Data" / filename).open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        return list(csv.DictReader(handle))


def import_reference(db: Session, root: Path) -> None:
    outlets = rows(root, "outlets.csv")
    vehicles = rows(root, "vehicles.csv")
    if (
        len(outlets) != 120
        or len(vehicles) != 60
        or len({row["outlet_id"] for row in outlets}) != 120
        or len({row["vehicle_id"] for row in vehicles}) != 60
    ):
        raise ValueError(
            "Shared reference data must contain 120 unique outlets and 60 unique vehicles"
        )
    coordinates = {"Peliyagoda": (6.96, 79.90), "Kandy": (7.29, 80.64)}
    for code, (lat, lng) in coordinates.items():
        if not db.get(Depot, code):
            db.add(Depot(code=code, name=code, lat=lat, lng=lng))
    db.flush()
    for row in outlets:
        if db.get(Outlet, row["outlet_id"]):
            continue
        opening, closing = (
            dt.time.fromisoformat(row["window_open_time"]),
            dt.time.fromisoformat(row["window_close_time"]),
        )
        mall = row["mall_window"].replace("–", "-").split("-")
        lat, lng = outlet_coords(row["outlet_id"], row["district"])
        db.add(
            Outlet(
                outlet_id=row["outlet_id"],
                name=f"{row['brand']} {row['district']}",
                brand=row["brand"],
                district=row["district"],
                depot_code=row["depot"],
                dock_type=row["dock_type"],
                parking_constraint=row["parking_constraint"] or None,
                van_only=row["parking_constraint"] == "van_only",
                is_mall=len(mall) == 2,
                mall_window_open=dt.time.fromisoformat(mall[0])
                if len(mall) == 2
                else None,
                mall_window_close=dt.time.fromisoformat(mall[1])
                if len(mall) == 2
                else None,
                window_open_time=opening,
                window_close_time=closing,
                lat=lat,
                lng=lng,
            )
        )
    for row in vehicles:
        if db.get(Vehicle, row["vehicle_id"]):
            continue
        if float(row["weight_cap_kg"]) <= 0 or float(row["volume_cap_m3"]) <= 0:
            raise ValueError("Vehicle capacity must be positive")
        db.add(
            Vehicle(
                vehicle_id=row["vehicle_id"],
                type=row["type"],
                temp=row["temp"],
                is_refrigerated=row["temp"] == "reefer",
                weight_cap_kg=float(row["weight_cap_kg"]),
                volume_cap_m3=float(row["volume_cap_m3"]),
                fuel_type=row["fuel_type"],
                km_per_l=float(row["km_per_l"]),
                weekly_fuel_quota_l=float(row["weekly_fuel_quota_l"]),
                depot_code=row["depot"],
            )
        )
    for row in rows(root, "calendar.csv"):
        day = dt.date.fromisoformat(row["date"])
        if db.get(CalendarDay, day):
            continue
        db.add(
            CalendarDay(
                date=day,
                dow=int(row["dow"]),
                dow_name=row["dow_name"],
                is_weekend=row["is_weekend"] == "1",
                iso_year=int(row["iso_year"]),
                iso_week=int(row["iso_week"]),
                is_payday=row["is_payday"] == "1",
                festival=row["festival"] or None,
                festival_ramp=float(row["festival_ramp"]),
                is_holiday=row["is_holiday"] == "1",
                monsoon=row["monsoon"] == "1",
                is_operating=row["is_operating"] == "1",
            )
        )
