from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from .paths import DATA_ROOT


def read(group: Any, name: Any) -> Any:
    return pd.read_csv(DATA_ROOT / group / name)


def minutes(s: Any) -> Any:
    return pd.to_timedelta(s + ":00").dt.total_seconds() / 60


def prepare_task1(test: Any = False) -> Any:
    orders = read(
        "Test Data" if test else "Training Data",
        "task1_test_inputs.csv" if test else "deliveries_train.csv",
    )
    legs = read(
        "Test Data" if test else "Training Data",
        "route_legs_test.csv" if test else "route_legs_train.csv",
    )
    orders = orders[orders.route_id.notna()].copy()
    d = orders.merge(
        legs,
        left_on=["route_id", "seq_in_route"],
        right_on=["route_id", "seq"],
        validate="one_to_one",
        suffixes=("", "_leg"),
    )
    assert (
        len(d) == len(orders)
        and (d.outlet_id == d.to_outlet).all()
        and (d.dispatch_date == d.date).all()
    )
    assert (d.planned_arrival_time == d.planned_arrival_time_leg).all()
    if not test:
        d["service"] = minutes(d.leave_outlet_time) - np.maximum(
            minutes(d.arrival_time), minutes(d.window_open_time)
        )
        d["late"] = (minutes(d.arrival_time) > minutes(d.window_close_time)).astype(int)
        assert d.service.ge(0).all()
    return enrich(d)


def enrich(d: Any) -> Any:
    initial_count = len(d)
    d = d.merge(
        read("General Data", "outlets.csv")[
            ["outlet_id", "dock_type", "parking_constraint", "mall_window"]
        ],
        on="outlet_id",
        validate="many_to_one",
    )
    d = d.merge(
        read("General Data", "vehicles.csv")[
            ["vehicle_id", "weight_cap_kg", "volume_cap_m3", "km_per_l"]
        ],
        on="vehicle_id",
        validate="many_to_one",
    )
    cal = read("General Data", "calendar.csv").drop(
        columns=["dow", "dow_name", "monsoon"]
    )
    d = d.merge(
        cal,
        left_on="dispatch_date",
        right_on="date",
        suffixes=("", "_calendar"),
        validate="many_to_one",
    )
    d = d.merge(
        read("General Data", "district_travel.csv").drop(columns="depot"),
        on="district",
        validate="many_to_one",
    )
    d = d.merge(
        read("General Data", "service_allowance.csv"),
        on=["brand", "dock_type"],
        validate="many_to_one",
    )
    for c in [
        "planned_depart_time",
        "planned_arrival_time",
        "window_open_time",
        "window_close_time",
    ]:
        d[c + "_min"] = minutes(d[c])
    d["hour"] = (d.planned_depart_time_min // 60).astype(int)
    d = d.merge(
        read("General Data", "traffic_speed.csv"),
        on=["district", "hour", "monsoon"],
        validate="many_to_one",
    )
    d = d.merge(
        read("General Data", "road_conditions.csv"),
        on=["district", "date"],
        validate="many_to_one",
    )
    d["slack"] = d.window_close_time_min - d.planned_arrival_time_min
    d["window_width"] = d.window_close_time_min - d.window_open_time_min
    d["earliness"] = (d.window_open_time_min - d.planned_arrival_time_min).clip(lower=0)
    d["density"] = d.order_weight_kg / d.order_volume_m3.clip(lower=0.001)
    d["weight_per_unit"] = d.order_weight_kg / d.order_units.clip(lower=1)
    d["volume_per_unit"] = d.order_volume_m3 / d.order_units.clip(lower=1)
    d["weight_ratio"] = d.order_weight_kg / d.weight_cap_kg
    d["volume_ratio"] = d.order_volume_m3 / d.volume_cap_m3
    d["traffic_travel"] = d.planned_travel_duration_min * 100 / d.speed_index
    d["road_adjusted_travel"] = d.traffic_travel * 100 / d.disruption_index
    d["traffic_excess"] = d.road_adjusted_travel - d.planned_travel_duration_min
    d = d.sort_values(["dispatch_date", "route_id", "seq"]).reset_index(drop=True)
    for c in [
        "order_weight_kg",
        "order_volume_m3",
        "planned_travel_duration_min",
        "service_allowance_min",
        "traffic_excess",
    ]:
        d["prefix_" + c] = d.groupby("route_id")[c].cumsum() - d[c]
    d["route_stops"] = d.groupby("route_id").seq.transform("size")
    d["size_band"] = pd.cut(
        d.order_volume_m3,
        [-np.inf, 1, 3, 10, np.inf],
        labels=["small", "medium", "large", "very_large"],
    ).astype(str)
    d["order_size_band"] = d.size_band
    d["service_group"] = d.brand + "_" + d.dock_type
    for group in sorted(d.service_group.unique()):
        for c in ["order_units", "order_weight_kg", "order_volume_m3"]:
            d[group + "__" + c] = d[c] * d.service_group.eq(group)
    for c in ["slack", "seq", "traffic_excess"]:
        d[c + "_square"] = d[c] ** 2
    assert len(d) == initial_count
    return d


BASIC = [
    "brand",
    "dock_type",
    "temp_requirement",
    "order_units",
    "order_weight_kg",
    "order_volume_m3",
    "outlet_id",
    "parking_constraint",
]
FULL = BASIC + [
    "district",
    "depot",
    "vehicle_type",
    "vehicle_temp",
    "weight_cap_kg",
    "volume_cap_m3",
    "weight_ratio",
    "volume_ratio",
    "density",
    "weight_per_unit",
    "volume_per_unit",
    "seq",
    "route_stops",
    "planned_depart_time_min",
    "planned_arrival_time_min",
    "planned_travel_duration_min",
    "distance_km",
    "window_open_time_min",
    "window_close_time_min",
    "slack",
    "window_width",
    "earliness",
    "dow",
    "monsoon",
    "is_payday",
    "festival",
    "festival_ramp",
    "is_holiday",
    "road_class",
    "speed_index",
    "disruption_index",
    "road_adjusted_travel",
    "traffic_excess",
    "prefix_order_weight_kg",
    "prefix_order_volume_m3",
    "prefix_planned_travel_duration_min",
    "prefix_service_allowance_min",
    "prefix_traffic_excess",
    "service_allowance_min",
]


def features(d: Any, variant: Any = "full") -> Any:
    cols = BASIC if variant == "basic" else FULL
    if variant == "linear":
        cols = (
            FULL
            + [c for c in d if "__order_" in c]
            + ["slack_square", "seq_square", "traffic_excess_square"]
        )
    if variant == "upstream":
        cols = FULL + ["prefix_pred_service", "prefix_service_excess"]
    x = d[cols].copy()
    cats = list(x.select_dtypes(include=["object", "string", "category"]).columns)
    for c in cats:
        x[c] = x[c].fillna("_missing_").astype(str)
    assert not any(
        c in x
        for c in [
            "service",
            "late",
            "arrival_time",
            "actual_depart_time",
            "actual_travel_duration_min",
            "leave_outlet_time",
        ]
    )
    return x, cats
