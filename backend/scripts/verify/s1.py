"""Validate/allocate authorized local S1 CSV inputs without uploading or packaging datasets."""

import argparse
import csv
import datetime as dt
from pathlib import Path
from app.domain.planning.types import (
    PlannerContext,
    PlannerOutlet,
    PlannerOrder,
    PlannerVehicle,
)
from app.domain.planning.allocate import allocate
from app.domain.planning.validate import validate_plan


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def minute(value):
    return dt.time.fromisoformat(value) if value else None


def run(orders, availability, outlets, vehicles, travel, allowances, day):
    network = {}
    for row in outlets:
        mall = row.get("mall_window", "").replace("–", "-").split("-")
        network[row["outlet_id"]] = PlannerOutlet(
            outlet_id=row["outlet_id"],
            brand=row["brand"],
            district=row["district"],
            depot_code=row["depot"],
            van_only=row["parking_constraint"] == "van_only",
            is_mall=row["parking_constraint"] == "mall_dock",
            mall_window_open=minute(mall[0]) if len(mall) == 2 else None,
            mall_window_close=minute(mall[1]) if len(mall) == 2 else None,
            window_open_time=minute(row.get("window_open_time")),
            window_close_time=minute(row.get("window_close_time")),
            lat=0,
            lng=0,
            dock_type=row["dock_type"],
        )
    status = {
        r["vehicle_id"]: r["status"]
        for r in availability
        if r.get("scenario", "S1") == "S1"
    }
    fleet = {
        r["vehicle_id"]: PlannerVehicle(
            vehicle_id=r["vehicle_id"],
            type=r["type"],
            is_refrigerated=r["temp"] == "reefer",
            weight_cap_kg=float(r["weight_cap_kg"]),
            volume_cap_m3=float(r["volume_cap_m3"]),
            km_per_l=float(r["km_per_l"]),
            weekly_fuel_quota_l=float(r["weekly_fuel_quota_l"]),
            fuel_used_this_week=0,
            depot_code=r["depot"],
            lat=0,
            lng=0,
            status=status.get(r["vehicle_id"], "unavailable"),
        )
        for r in vehicles
    }
    if any(r["scenario"] != "S1" for r in orders):
        raise ValueError("This policy accepts S1 only")
    inputs = [
        PlannerOrder(
            order_id=r["order_ref"],
            outlet_id=r["outlet_id"],
            brand=r["brand"],
            temperature_class=r["temp_requirement"].upper(),
            total_weight=float(r["order_weight_kg"]),
            total_volume=float(r["order_volume_m3"]),
            priority=r["deferred_yesterday"] == "1",
            consecutive_deferrals=int(r["deferred_yesterday"]),
            days_since_last_served=int(r["days_since_last_served"]),
        )
        for r in orders
    ]
    ctx = PlannerContext(
        delivery_date=day,
        outlets=network,
        vehicles=fleet,
        orders=inputs,
        policy="s1",
        district_travel={
            (r["district"], r["depot"]): (
                float(r["depot_to_district_freeflow_min"]),
                float(r["inter_stop_freeflow_min"]),
            )
            for r in travel
        },
        service_allowance={
            (r["brand"], r["dock_type"]): float(r["service_allowance_min"])
            for r in allowances
        },
    )
    plan = allocate(ctx)
    violations = validate_plan(plan, ctx)
    if violations:
        raise ValueError(
            "S1 feasibility validation failed: " + str([v.rule for v in violations])
        )
    assigned = {
        oid: (trip.vehicle_id, trip.trip_number)
        for trip in plan.trips
        for stop in trip.stops
        for oid in stop.order_ids
    }
    rows = [
        {
            "scenario": "S1",
            "order_ref": r["order_ref"],
            "outlet_id": r["outlet_id"],
            "status": "served" if r["order_ref"] in assigned else "deferred",
            "vehicle_id": assigned.get(r["order_ref"], ("", ""))[0],
            "trip_id": assigned.get(r["order_ref"], ("", ""))[1],
        }
        for r in orders
    ]
    return rows, plan


def main():
    parser = argparse.ArgumentParser()
    for name in [
        "orders",
        "availability",
        "outlets",
        "vehicles",
        "travel",
        "allowances",
        "output",
    ]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--date", type=dt.date.fromisoformat, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[3]
    if args.output.resolve().is_relative_to(repository):
        raise ValueError(
            "Write competition results to an authorized private location outside the repository"
        )
    rows, plan = run(
        *(
            read(getattr(args, name))
            for name in [
                "orders",
                "availability",
                "outlets",
                "vehicles",
                "travel",
                "allowances",
            ]
        ),
        args.date,
    )
    with args.output.open("x", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "scenario",
                "order_ref",
                "outlet_id",
                "status",
                "vehicle_id",
                "trip_id",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(
        {
            "orders": len(rows),
            "served": sum(r["status"] == "served" for r in rows),
            "deferred": len(plan.deferrals),
            "valid": True,
        }
    )


if __name__ == "__main__":
    main()
