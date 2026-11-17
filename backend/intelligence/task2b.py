"""Whole-order peak-day allocation, independent feasibility validation, lexicographic CP-SAT."""

import json
from decimal import Decimal
import pandas as pd
from ortools.sat.python import cp_model
from runtime import (
    ROOT,
    Run,
    table,
    write_json,
    sha,
    TRAIN_THREADS,
    experiment_identity,
)
from features import read


def scaled(value, factor):
    exact = Decimal(str(value)) * factor
    assert exact == exact.to_integral_value(), (value, factor)
    return int(exact)


def inputs():
    orders = read("Test Data", "task2b_peak_day_scenarios.csv")
    fleet = read("Test Data", "task2b_peak_day_fleet.csv").merge(
        read("General Data", "vehicles.csv"), on="vehicle_id", validate="one_to_one"
    )
    travel = read("General Data", "district_travel.csv").set_index(
        ["depot", "district"]
    )
    allowance = (
        read("General Data", "service_allowance.csv")
        .set_index(["brand", "dock_type"])
        .service_allowance_min
    )
    assert len(orders) == 85 and not orders.order_ref.duplicated().any()
    return orders, fleet, travel, allowance


def trip_minutes(rows, travel, allowance):
    r = rows.iloc[0]
    t = travel.loc[(r.depot, r.district)]
    return int(
        t.depot_to_district_freeflow_min
        + (len(rows) - 1) * t.inter_stop_freeflow_min
        + sum(allowance.loc[(q.brand, q.dock_type)] for q in rows.itertuples())
    )


def compatible(order, vehicle):
    return (
        vehicle.status == "available"
        and vehicle.depot == order.depot
        and (order.temp_requirement != "chilled" or vehicle.temp == "reefer")
        and (order.parking_constraint != "van_only" or vehicle.type == "van")
        and scaled(order.order_volume_m3, 1000) <= scaled(vehicle.volume_cap_m3, 1000)
        and scaled(order.order_weight_kg, 10) <= scaled(vehicle.weight_cap_kg, 10)
    )


def allocation(orders, assignment):
    template = read("Submission Templates", "submission_task2b.csv")
    assert orders[["scenario", "order_ref", "outlet_id"]].equals(
        template[["scenario", "order_ref", "outlet_id"]]
    )
    out = template[["scenario", "order_ref", "outlet_id"]].copy()
    out["decision"] = [
        "served" if i in assignment else "deferred" for i in range(len(out))
    ]
    out["vehicle_id"] = [
        assignment[i][0] if i in assignment else "" for i in range(len(out))
    ]
    out["trip_id"] = [
        str(assignment[i][1]) if i in assignment else "" for i in range(len(out))
    ]
    return out


def validate(out, orders=None, fleet=None, travel=None, allowance=None):
    if orders is None:
        orders, fleet, travel, allowance = inputs()
    errors = []
    trips = []
    template = read("Submission Templates", "submission_task2b.csv")
    if list(out.columns) != list(template.columns):
        errors.append("template columns differ")
    if len(out) != 85 or not out[["scenario", "order_ref", "outlet_id"]].reset_index(
        drop=True
    ).equals(template[["scenario", "order_ref", "outlet_id"]]):
        errors.append("identifiers/order differ")
    if not out.decision.isin(["served", "deferred"]).all():
        errors.append("invalid decision")
    deferred = out[out.decision == "deferred"]
    if deferred[["vehicle_id", "trip_id"]].fillna("").astype(str).ne("").any().any():
        errors.append("deferred assignment must be blank")
    served = out[out.decision == "served"].copy()
    served["trip_id"] = pd.to_numeric(served.trip_id, errors="coerce")
    if not served.trip_id.isin([1, 2]).all():
        errors.append("trip must be 1 or 2")
    if served.order_ref.duplicated().any():
        errors.append("order split or duplicated")
    joined = served.merge(
        orders, on=["scenario", "order_ref", "outlet_id"], validate="one_to_one"
    )
    lookup = fleet.set_index("vehicle_id")
    for (vehicle_id, trip_id), g in joined.groupby(
        ["vehicle_id", "trip_id"], dropna=False
    ):
        if vehicle_id not in lookup.index:
            errors.append("unknown vehicle " + str(vehicle_id))
            continue
        v = lookup.loc[vehicle_id]
        if v.status != "available":
            errors.append("workshop vehicle " + vehicle_id)
        if g.depot.ne(v.depot).any():
            errors.append("wrong depot " + vehicle_id)
        if g.temp_requirement.eq("chilled").any() and v.temp != "reefer":
            errors.append("chilled on ambient " + vehicle_id)
        if g.parking_constraint.eq("van_only").any() and v.type != "van":
            errors.append("truck at van-only outlet " + vehicle_id)
        if g.brand.nunique() != 1 or g.district.nunique() != 1:
            errors.append("mixed brand/district " + vehicle_id)
            continue
        volume = sum(scaled(x, 1000) for x in g.order_volume_m3)
        weight = sum(scaled(x, 10) for x in g.order_weight_kg)
        if volume > scaled(v.volume_cap_m3, 1000):
            errors.append("volume exceeded " + vehicle_id)
        if weight > scaled(v.weight_cap_kg, 10):
            errors.append("weight exceeded " + vehicle_id)
        duration = trip_minutes(g, travel, allowance)
        trips.append(
            {
                "vehicle_id": vehicle_id,
                "trip_id": int(trip_id),
                "brand": g.brand.iloc[0],
                "district": g.district.iloc[0],
                "orders": len(g),
                "volume_m3": volume / 1000,
                "volume_cap_m3": v.volume_cap_m3,
                "weight_kg": weight / 10,
                "weight_cap_kg": v.weight_cap_kg,
                "minutes": duration,
            }
        )
    trips = pd.DataFrame(trips)
    if not trips.empty:
        for vehicle_id, g in trips.groupby("vehicle_id"):
            if len(g) > 2:
                errors.append("too many trips " + vehicle_id)
            if g.loc[g.brand.eq("Fresh"), "minutes"].sum() > 270:
                errors.append("Fresh time exceeded " + vehicle_id)
            if g.loc[~g.brand.eq("Fresh"), "minutes"].sum() > 480:
                errors.append("Style/Tech time exceeded " + vehicle_id)
    stats = {
        "served_chilled_m3": float(
            joined.loc[
                joined.temp_requirement.eq("chilled") & joined.brand.eq("Fresh"),
                "order_volume_m3",
            ].sum()
        ),
        "previously_deferred_served": int(joined.deferred_yesterday.sum()),
        "orders_served": len(joined),
        "days_since_last_served_sum": int(joined.days_since_last_served.sum()),
        "total_trip_minutes": int(trips.minutes.sum()) if not trips.empty else 0,
        "violations": len(errors),
    }
    return {"metrics": stats, "errors": errors, "trips": trips}


def greedy(orders, fleet, travel, allowance):
    assignment = {}
    available = fleet[fleet.status.eq("available")]
    order_indices = sorted(
        orders.index,
        key=lambda i: (
            orders.loc[i, "temp_requirement"] != "chilled",
            -orders.loc[i, "deferred_yesterday"],
            -orders.loc[i, "days_since_last_served"],
            orders.loc[i, "order_volume_m3"],
        ),
    )
    for i in order_indices:
        order = orders.loc[i]
        candidates = []
        for v in available.itertuples():
            if not compatible(order, v):
                continue
            for trip in [1, 2]:
                trial = {**assignment, i: (v.vehicle_id, trip)}
                rows = orders.loc[
                    [k for k, a in trial.items() if a == (v.vehicle_id, trip)]
                ]
                if rows.brand.nunique() != 1 or rows.district.nunique() != 1:
                    continue
                if sum(scaled(x, 1000) for x in rows.order_volume_m3) > scaled(
                    v.volume_cap_m3, 1000
                ):
                    continue
                if sum(scaled(x, 10) for x in rows.order_weight_kg) > scaled(
                    v.weight_cap_kg, 10
                ):
                    continue
                durations = {"Fresh": 0, "other": 0}
                for t in [1, 2]:
                    r = orders.loc[
                        [k for k, a in trial.items() if a == (v.vehicle_id, t)]
                    ]
                    if len(r):
                        durations[
                            "Fresh" if r.brand.iloc[0] == "Fresh" else "other"
                        ] += trip_minutes(r, travel, allowance)
                if durations["Fresh"] > 270 or durations["other"] > 480:
                    continue
                # Reserve refrigerated and van capacity when ordinary trucks suffice; pack existing trips.
                candidates.append(
                    (
                        (
                            order.temp_requirement != "chilled" and v.temp == "reefer",
                            order.parking_constraint != "van_only" and v.type == "van",
                            len(rows) == 1,
                            v.volume_cap_m3 - rows.order_volume_m3.sum(),
                            v.vehicle_id,
                            trip,
                        ),
                        trial,
                    )
                )
        if candidates:
            assignment = min(candidates, key=lambda x: x[0])[1]
    return assignment


def build_model(orders, fleet, travel, allowance):
    model = cp_model.CpModel()
    x = {}
    z = {}
    durations = {}
    active = {}
    served = {}
    groups = list(orders.groupby(["brand", "district", "depot"]).groups)
    available = fleet[fleet.status.eq("available")]
    for v in available.itertuples():
        for trip in [1, 2]:
            group_z = []
            fresh = []
            other = []
            for brand, district, depot in groups:
                if depot != v.depot:
                    continue
                idx = [
                    i
                    for i in orders.index
                    if orders.loc[i, "brand"] == brand
                    and orders.loc[i, "district"] == district
                    and compatible(orders.loc[i], v)
                ]
                if not idx:
                    continue
                key = (v.vehicle_id, trip, brand, district)
                zg = model.new_bool_var("g_" + str(key))
                z[key] = zg
                group_z.append(zg)
                variables = []
                for i in idx:
                    xi = model.new_bool_var(f"x_{i}_{v.vehicle_id}_{trip}")
                    x[(i, v.vehicle_id, trip)] = xi
                    model.add(xi <= zg)
                    variables.append(xi)
                model.add(sum(variables) >= zg)
                model.add(
                    sum(
                        scaled(orders.loc[i, "order_volume_m3"], 1000)
                        * x[(i, v.vehicle_id, trip)]
                        for i in idx
                    )
                    <= scaled(v.volume_cap_m3, 1000) * zg
                )
                model.add(
                    sum(
                        scaled(orders.loc[i, "order_weight_kg"], 10)
                        * x[(i, v.vehicle_id, trip)]
                        for i in idx
                    )
                    <= scaled(v.weight_cap_kg, 10) * zg
                )
                t = travel.loc[(depot, district)]
                inter = int(t.inter_stop_freeflow_min)
                outbound = int(t.depot_to_district_freeflow_min)
                expression = (outbound - inter) * zg + sum(
                    (inter + int(allowance.loc[(brand, orders.loc[i, "dock_type"])]))
                    * x[(i, v.vehicle_id, trip)]
                    for i in idx
                )
                (fresh if brand == "Fresh" else other).append(expression)
            active[(v.vehicle_id, trip)] = model.new_bool_var(
                f"active_{v.vehicle_id}_{trip}"
            )
            model.add(sum(group_z) == active[(v.vehicle_id, trip)])
            durations[(v.vehicle_id, trip, "Fresh")] = sum(fresh)
            durations[(v.vehicle_id, trip, "other")] = sum(other)
        model.add(active[(v.vehicle_id, 2)] <= active[(v.vehicle_id, 1)])
        model.add(sum(durations[(v.vehicle_id, t, "Fresh")] for t in [1, 2]) <= 270)
        model.add(sum(durations[(v.vehicle_id, t, "other")] for t in [1, 2]) <= 480)
    for i in orders.index:
        served[i] = model.new_bool_var(f"served_{i}")
        model.add(sum(xi for (j, v, t), xi in x.items() if j == i) == served[i])
    objectives = [
        (
            "chilled_volume",
            sum(
                scaled(orders.loc[i, "order_volume_m3"], 1000) * s
                for i, s in served.items()
                if orders.loc[i, "temp_requirement"] == "chilled"
                and orders.loc[i, "brand"] == "Fresh"
            ),
        ),
        (
            "previously_deferred",
            sum(
                int(orders.loc[i, "deferred_yesterday"]) * s for i, s in served.items()
            ),
        ),
        ("orders_served", sum(served.values())),
        (
            "days_since_service",
            sum(
                int(orders.loc[i, "days_since_last_served"]) * s
                for i, s in served.items()
            ),
        ),
        ("lower_trip_minutes", -sum(durations.values())),
    ]
    return model, x, z, active, served, objectives


def add_hint(model, x, z, active, served, assignment, orders):
    model.clear_hints()
    for (i, v, t), var in x.items():
        model.add_hint(var, int(assignment.get(i) == (v, t)))
    for (v, t, b, d), var in z.items():
        model.add_hint(
            var,
            int(
                any(
                    a == (v, t)
                    and orders.loc[i, "brand"] == b
                    and orders.loc[i, "district"] == d
                    for i, a in assignment.items()
                )
            ),
        )
    for (v, t), var in active.items():
        model.add_hint(var, int(any(a == (v, t) for a in assignment.values())))
    for i, var in served.items():
        model.add_hint(var, int(i in assignment))


class Incumbents(cp_model.CpSolverSolutionCallback):
    def __init__(self, run, x, orders, context):
        super().__init__()
        self.run, self.x, self.orders, self.context = run, x, orders, context
        self.rows = []
        self.latest = None

    def on_solution_callback(self):
        assignment = {i: (v, t) for (i, v, t), var in self.x.items() if self.value(var)}
        out = allocation(self.orders, assignment)
        checked = validate(out, *self.context)
        assert not checked["errors"], checked["errors"]
        row = {
            "step": len(self.rows) + 1,
            "elapsed_seconds": self.wall_time,
            "objective": self.objective_value,
            "bound": self.best_objective_bound,
            **checked["metrics"],
        }
        self.rows.append(row)
        self.latest = assignment
        p = self.run.path / f"incumbent_{len(self.rows):04d}.csv"
        out.to_csv(p, index=False)
        self.run.meta.setdefault("solution_checkpoints", []).append(
            {
                "path": p.relative_to(ROOT).as_posix(),
                "sha256": sha(p),
                "step": len(self.rows),
            }
        )
        pd.DataFrame(self.rows).to_csv(self.run.path / "iterations.csv", index=False)
        (self.run.path / "iterations.md").write_text(
            "# Every feasible incumbent\n\n" + table(self.rows), encoding="utf-8"
        )
        print(f"INCUMBENT {self.run.id}: {row} CHECKPOINT {p.name}", flush=True)


def optimize(
    orders, fleet, travel, allowance, initial, policy="lexicographic", limit=120
):
    model, x, z, active, served, objectives = build_model(
        orders, fleet, travel, allowance
    )
    if policy == "maximum_count":
        objectives = [objectives[2], objectives[0]]
    assignment = initial
    summary = []
    for stage, expression in objectives:
        with Run(
            "task2b",
            policy + "_" + stage,
            "S1",
            {
                "max_seconds": limit,
                "workers": TRAIN_THREADS,
                "objective": stage,
                "fixed_prior_stages": summary,
                "scale_volume": 1000,
                "scale_weight": 10,
                "variables": len(x),
                "seed": 42,
            },
        ) as run:
            model.maximize(expression)
            add_hint(model, x, z, active, served, assignment, orders)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = limit
            solver.parameters.num_search_workers = TRAIN_THREADS
            solver.parameters.random_seed = 42
            solver.parameters.log_search_progress = True
            solver.parameters.log_to_stdout = False
            solver.log_callback = lambda message: print(
                message, end="" if message.endswith("\n") else "\n", flush=True
            )
            callback = Incumbents(run, x, orders, (orders, fleet, travel, allowance))
            status = solver.solve(model, callback)
            if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                if callback.latest is None:
                    raise RuntimeError(
                        "No feasible solution: " + solver.status_name(status)
                    )
                assignment = callback.latest
            else:
                assignment = {
                    i: (v, t) for (i, v, t), var in x.items() if solver.value(var)
                }
            out = allocation(orders, assignment)
            checked = validate(out, orders, fleet, travel, allowance)
            assert not checked["errors"], checked["errors"]
            value = int(round(solver.objective_value))
            bound = float(solver.best_objective_bound)
            record = {
                "stage": stage,
                "status": solver.status_name(status),
                "objective": value,
                "bound": bound,
                "absolute_gap": abs(bound - value),
                "relative_gap": abs(bound - value) / max(1, abs(value)),
                "runtime_seconds": solver.wall_time,
                **checked["metrics"],
            }
            summary.append(record)
            run.meta.update(
                metrics=record,
                completed_steps=len(callback.rows),
                best_step=len(callback.rows),
                requested_steps="time-limited exact optimization",
                stopped_reason=solver.status_name(status),
            )
            out.to_csv(run.path / "allocation.csv", index=False)
            checked["trips"].to_csv(run.path / "trip_details.csv", index=False)
            (run.path / "evaluation.md").write_text(
                "# Feasibility and objective\n\n"
                + table([record])
                + "\n"
                + table(checked["trips"]),
                encoding="utf-8",
            )
            write_json(
                run.path / "evaluation.json",
                {"overall": record, "errors": checked["errors"]},
            )
            run.save(
                {"assignment": assignment, "summary": summary}, "allocation.joblib"
            )
            # Preserve the incumbent objective even when the time cap prevents an optimality proof.
            model.add(expression >= value)
            print("SOLVER STAGE COMPLETE:", record, flush=True)
    return assignment, summary


def task2b(require_task2a=True):
    if require_task2a:
        gate = json.loads(
            (ROOT / "reports" / "task2a_complete.json").read_text(encoding="utf-8")
        )
        assert gate.get("fresh_process_verified") and gate.get("documentation_complete")
    print(
        "TASK 2B START: No predictive model or return travel is used for allocation.",
        flush=True,
    )
    orders, fleet, travel, allowance = inputs()
    with Run(
        "task2b",
        "feasible_greedy",
        "S1",
        {"priority": "chilled, previously deferred, overdue, small volume"},
    ) as run:
        initial = greedy(orders, fleet, travel, allowance)
        out = allocation(orders, initial)
        check = validate(out, orders, fleet, travel, allowance)
        assert not check["errors"], check["errors"]
        run.meta.update(metrics=check["metrics"], completed_steps=85, best_step=85)
        out.to_csv(run.path / "allocation.csv", index=False)
        run.save({"assignment": initial})
        (run.path / "evaluation.md").write_text(
            "# Feasible greedy baseline\n\n"
            + table([check["metrics"]])
            + "\n"
            + table(check["trips"]),
            encoding="utf-8",
        )
    final, summary = optimize(orders, fleet, travel, allowance, initial, limit=120)
    out = allocation(orders, final)
    check = validate(out, orders, fleet, travel, allowance)
    assert not check["errors"]
    out.to_csv(ROOT / "submissions" / "submission_task2b.csv", index=False)
    # A separate count-first policy shows the practical cost of the chosen priority.
    alternate, alternate_summary = optimize(
        orders, fleet, travel, allowance, initial, policy="maximum_count", limit=60
    )
    comparison = [
        {
            "policy": "greedy",
            **validate(allocation(orders, initial), orders, fleet, travel, allowance)[
                "metrics"
            ],
        },
        {"policy": "selected lexicographic", **check["metrics"]},
        {
            "policy": "count first",
            **validate(allocation(orders, alternate), orders, fleet, travel, allowance)[
                "metrics"
            ],
        },
    ]
    available = fleet[fleet.status.eq("available")]
    reef = available[available.temp.eq("reefer")]
    shortage = (
        orders.loc[orders.temp_requirement.eq("chilled"), "order_volume_m3"].sum()
        - 2 * reef.volume_cap_m3.sum()
    )
    served_ids = set(out.loc[out.decision.eq("served"), "order_ref"])
    deferred = []
    for i, r in orders.iterrows():
        if r.order_ref in served_ids:
            continue
        eligible = [v for v in available.itertuples() if compatible(r, v)]
        deferred.append(
            {
                "order_ref": r.order_ref,
                "brand": r.brand,
                "district": r.district,
                "temperature": r.temp_requirement,
                "volume_m3": r.order_volume_m3,
                "weight_kg": r.order_weight_kg,
                "deferred_yesterday": r.deferred_yesterday,
                "days_since_last_served": r.days_since_last_served,
                "reason": "individually infeasible: no compatible available vehicle"
                if not eligible
                else "fleet/time/group capacity under selected priority; identity of deferred order is a policy choice",
            }
        )
    report = (
        "# Task 2B allocation complete\n\n## Policy comparison\n\n"
        + table(comparison)
        + "\n## Sequential objectives and proofs\n\n"
        + table(summary)
        + "\n## Count-first comparison proofs\n\n"
        + table(alternate_summary)
        + "\n## Deferred orders\n\n"
        + table(deferred)
        + "\n## Selected trips\n\n"
        + table(check["trips"])
    )
    (ROOT / "reports" / "TASK2B_RESULTS.md").write_text(report, encoding="utf-8")
    check["trips"].to_csv(ROOT / "reports" / "TASK2B_TRIPS.csv", index=False)
    write_json(
        ROOT / "reports" / "task2b_complete.json",
        {
            "status": "passed",
            "rows": 85,
            "metrics": check["metrics"],
            "errors": check["errors"],
            "objectives": summary,
            "comparisons": comparison,
            "unavoidable_refrigeration_shortfall_m3_lower_bound": shortage,
            "submission_sha256": sha(ROOT / "submissions" / "submission_task2b.csv"),
            **experiment_identity(),
        },
    )
    policy = f"""# Peak-day prioritization policy

Allocate whole orders with available home-depot vehicles. Priorities are sequential: maximize served chilled Fresh m³; then previously deferred orders served; then total orders served; then the sum of days since last service among served orders; then minimize total trip minutes. Each later stage preserves the earlier attained objectives. A time-capped stage is an incumbent guarantee, not a proof of the globally optimal policy; the objective bounds and gaps below make that distinction explicit.

{table(comparison)}

There are {len(available)} available vehicles, including {len(reef)} refrigerated vehicles. Chilled demand is {orders.loc[orders.temp_requirement.eq('chilled'),'order_volume_m3'].sum():.3f} m³ versus an optimistic two-trip refrigerated volume ceiling of {2*reef.volume_cap_m3.sum():.3f} m³. At least {shortage:.3f} m³ must therefore remain unserved before accounting for districts, van access, weight, and the 270-minute Fresh budget. The chosen allocation leaves {orders.loc[orders.temp_requirement.eq('chilled'),'order_volume_m3'].sum()-check['metrics']['served_chilled_m3']:.3f} m³ chilled unserved. The shortage is unavoidable; which individually feasible chilled orders lose capacity depends on the priority policy.

S1-078 is a whole Style order of 40.660 m³; the largest available vehicle holds {available.volume_cap_m3.max():.3f} m³. Its deferral is individually unavoidable. Other specific deferrals are listed in TASK2B_RESULTS.md. Their cost is recorded as missed orders, chilled volume, and previously deferred/overdue service; no invented monetary prices are used. Reserve reefers and vans for orders that require them, combine compatible orders within each district, and allow reloading once. Reconsider deferred orders first on the next operating day.

Every trip uses one brand and district, satisfies exact integer-scaled weight and volume, and counts every order as a separate stop. Time = outbound free-flow minutes + (orders − 1) × inter-stop minutes + supplied brand/dock handling allowances. No return journey is added. Per vehicle, Fresh trip minutes sum to at most 270, Style plus Tech sum to at most 480, and all trips together number at most two. An independent validator found zero violations in all 85 decisions. Detailed bounds and trip calculations are in TASK2B_RESULTS.md.
"""
    (ROOT / "reports" / "ALLOCATION_POLICY.md").write_text(policy, encoding="utf-8")
    print("TASK 2B GATE PASSED:", check["metrics"], flush=True)


if __name__ == "__main__":
    from runtime import install_logging

    install_logging()
    task2b()
