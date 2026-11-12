import datetime as dt
from dataclasses import asdict
from hypothesis import given, settings, strategies as st
import pytest
from app.domain.planning.types import (
    PlannerContext,
    PlannerOutlet,
    PlannerVehicle,
    PlannerOrder,
    PlannerPlan,
    PlannerTrip,
    PlannerStop,
    PlannerDeferral,
)
from app.domain.planning.allocate import allocate
from app.domain.planning.validate import validate_plan
from app.domain.planning.triptime import trip_minutes


def context(count=1):
    outlets = {
        f"O{i}": PlannerOutlet(
            outlet_id=f"O{i}",
            brand="Fresh",
            district="Colombo",
            depot_code="Peliyagoda",
            van_only=False,
            is_mall=False,
            mall_window_open=None,
            mall_window_close=None,
            window_open_time=dt.time(5),
            window_close_time=dt.time(8),
            lat=6.96 + i * 0.001,
            lng=79.90,
            dock_type="street",
        )
        for i in range(count)
    }
    vehicle = PlannerVehicle(
        vehicle_id="V1",
        type="truck",
        is_refrigerated=True,
        weight_cap_kg=5000,
        volume_cap_m3=25,
        km_per_l=5,
        weekly_fuel_quota_l=400,
        fuel_used_this_week=0,
        depot_code="Peliyagoda",
        lat=6.96,
        lng=79.90,
    )
    orders = [
        PlannerOrder(
            order_id=i + 1,
            outlet_id=f"O{i}",
            brand="Fresh",
            temperature_class="CHILLED",
            total_weight=100,
            total_volume=1,
            priority=False,
        )
        for i in range(count)
    ]
    return PlannerContext(
        delivery_date=dt.date(2024, 4, 10), outlets=outlets, vehicles={"V1": vehicle}, orders=orders
    )


@given(
    st.lists(
        st.tuples(st.integers(1, 8000), st.integers(1, 150), st.booleans()), min_size=1, max_size=35
    )
)
@settings(max_examples=60, deadline=None)
def test_deterministic_allocation_never_loses_splits_or_serves_invalid_orders(values):
    ctx = context(len(values))
    for order, (weight, volume, van_only) in zip(ctx.orders, values):
        order.total_weight = weight
        order.total_volume = volume / 5
        ctx.outlets[order.outlet_id].van_only = van_only
    result = allocate(ctx)
    ids = [oid for trip in result.trips for stop in trip.stops for oid in stop.order_ids] + [
        d.order_id for d in result.deferrals
    ]
    assert sorted(ids) == [o.order_id for o in ctx.orders]
    assert len(ids) == len(set(ids))
    assert validate_plan(result, ctx) == []
    assert asdict(result) == asdict(allocate(ctx))


def test_s1_counts_orders_at_same_outlet_and_omits_return_travel():
    ctx = context(3)
    ctx.policy = "s1"
    ctx.outlets["O0"].dock_type = "rear_dock"
    ctx.outlets["O1"].dock_type = "rear_dock"
    ctx.district_travel = {("Colombo", "Peliyagoda"): (37, 9)}
    ctx.service_allowance = {("Fresh", "rear_dock"): 15, ("Fresh", "street"): 16}
    assert trip_minutes(ctx, "Peliyagoda", "Colombo", "Fresh", ["O0", "O1", "O2"]) == 101
    assert trip_minutes(ctx, "Peliyagoda", "Colombo", "Fresh", ["O0", "O0"]) == 37 + 9 + 30
    for i, order in enumerate(ctx.orders):
        order.order_id = f"S1-{i:03}"
    plan = allocate(ctx)
    assert set(oid for trip in plan.trips for stop in trip.stops for oid in stop.order_ids) | {
        d.order_id for d in plan.deferrals
    } == {"S1-000", "S1-001", "S1-002"}
    assert validate_plan(plan, ctx) == []


def test_unavailable_vehicle_and_nonoperating_day_only_defer():
    for flag in ("workshop", "calendar"):
        ctx = context()
        if flag == "workshop":
            ctx.vehicles["V1"].status = "in_workshop"
        else:
            ctx.is_operating = False
        plan = allocate(ctx)
        assert not plan.trips
        assert len(plan.deferrals) == 1
        assert validate_plan(plan, ctx) == []


def test_unknown_outlet_is_not_silently_dropped():
    ctx = context()
    ctx.orders[0].outlet_id = "missing"
    plan = allocate(ctx)
    assert plan.deferrals[0].reason_code == "UNKNOWN_OUTLET"
    assert validate_plan(plan, ctx) == []


def test_cumulative_fuel_and_duplicate_coverage_fail():
    ctx = context(2)
    ctx.vehicles["V1"].weekly_fuel_quota_l = 10
    trip1 = PlannerTrip(
        vehicle_id="V1",
        trip_number=1,
        stops=[PlannerStop(outlet_id="O0", order_ids=[1])],
        planned_fuel=6,
    )
    trip2 = PlannerTrip(
        vehicle_id="V1",
        trip_number=2,
        stops=[PlannerStop(outlet_id="O1", order_ids=[2])],
        planned_fuel=6,
    )
    plan = PlannerPlan(delivery_date=ctx.delivery_date, trips=[trip1, trip2])
    assert "FUEL" in {v.rule for v in validate_plan(plan, ctx)}
    trip1.stops[0].order_ids.append(1)
    assert "ORDER_COVERAGE" in {v.rule for v in validate_plan(plan, ctx)}


def test_s1_brand_district_time_and_trip_count_are_hard_constraints():
    ctx = context(2)
    ctx.policy = "s1"
    ctx.district_travel = {("Colombo", "Peliyagoda"): (260, 20)}
    ctx.service_allowance = {("Fresh", "street"): 20}
    trips = [
        PlannerTrip(
            vehicle_id="V1", trip_number=n, stops=[PlannerStop(outlet_id="O0", order_ids=[1])]
        )
        for n in (1, 2, 3)
    ]
    plan = PlannerPlan(
        delivery_date=ctx.delivery_date,
        trips=trips,
        deferrals=[
            PlannerDeferral(
                order_id=2, reason_code="CAPACITY", explanation="No capacity", consecutive_count=1
            )
        ],
    )
    rules = {v.rule for v in validate_plan(plan, ctx)}
    assert {"MAX_TRIPS", "TRIP_TIME", "ORDER_COVERAGE"} <= rules
    ctx.outlets["O1"].district = "Other"
    ctx.orders[1].brand = "Tech"
    trips[0].stops.append(PlannerStop(outlet_id="O1", order_ids=[2]))
    assert "BRAND_DISTRICT" in {v.rule for v in validate_plan(plan, ctx)}


def test_duplicate_input_keys_are_rejected():
    ctx = context(2)
    ctx.orders[1].order_id = 1
    with pytest.raises(ValueError):
        allocate(ctx)
