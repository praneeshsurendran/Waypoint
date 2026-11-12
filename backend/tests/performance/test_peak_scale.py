import datetime as dt
import json
import math
import os
import time
from pathlib import Path
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.planning import build_context
from app.domain.planning.allocate import allocate
from app.domain.planning.validate import validate_plan


def test_120_outlet_60_vehicle_plan_and_api_latency(service_clients, contexts):
    with contexts["operations"].begin() as db:
        for index in range(120):
            db.add(
                Order(
                    reference=f"PEAK-{index}",
                    outlet_id=f"SYN{index+1:03}",
                    brand="Fresh" if index < 80 else "Style" if index < 105 else "Tech",
                    temperature_class="CHILLED" if index < 40 else "AMBIENT",
                    delivery_date=dt.date(2024, 4, 10),
                    status="QUEUED",
                    total_cases=20,
                    total_weight=200,
                    total_volume=1,
                    priority=False,
                    cutoff_missed=False,
                )
            )
    started = time.perf_counter()
    with contexts["operations"]() as db:
        ctx = build_context(db, dt.date(2024, 4, 10))
        plan = allocate(ctx)
    duration = time.perf_counter() - started
    assert (
        len(ctx.outlets) == 120 and len(ctx.vehicles) == 60 and len(ctx.orders) == 120
    )
    assert validate_plan(plan, ctx) == []
    served = sum(len(stop.order_ids) for trip in plan.trips for stop in trip.stops)
    assert served + len(plan.deferrals) == 120
    auth = service_clients["identity"].post(
        "/api/v1/auth/login",
        json={"username": "dispatcher", "password": "test-role-password"},
    )
    assert auth.status_code == 200
    headers = {"Authorization": "Bearer " + auth.json()["access_token"]}
    timings = []
    for _ in range(20):
        start = time.perf_counter()
        response = service_clients["operations"].get(
            "/api/v1/orders?limit=200", headers=headers
        )
        assert response.status_code == 200, response.text
        assert len(response.json()) == 120
        timings.append((time.perf_counter() - start) * 1000)
    p95 = sorted(timings)[math.ceil(0.95 * len(timings)) - 1]
    result = {
        "outlets": 120,
        "vehicles": 60,
        "orders": 120,
        "served": served,
        "deferred": len(plan.deferrals),
        "plan_seconds": round(duration, 4),
        "list_orders_p95_ms": round(p95, 2),
        "samples": len(timings),
        "identity_transport": "in-process HTTP transport",
        "database": "real PostgreSQL",
    }
    print("\nWAYPOINT_PERFORMANCE=" + json.dumps(result))
    if os.getenv("BENCHMARK_REPORT"):
        Path(os.environ["BENCHMARK_REPORT"]).write_text(
            json.dumps(result, indent=2) + "\n"
        )
    assert duration < 30 and p95 < 10000
