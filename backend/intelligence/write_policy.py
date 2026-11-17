"""Write an auditable one-page allocation policy alongside private submission artifacts."""

from runtime import ROOT
from task2b import inputs, validate
import pandas as pd


def main():
    orders, fleet, travel, allowance = inputs()
    decisions = pd.read_csv(ROOT / "submissions/submission_task2b.csv")
    checked = validate(decisions, orders, fleet, travel, allowance)
    if checked["errors"]:
        raise ValueError(checked["errors"])
    deferred = decisions.loc[decisions.decision.eq("deferred")].merge(
        orders, on=["scenario", "order_ref", "outlet_id"], validate="one_to_one"
    )
    available = fleet.loc[fleet.status.eq("available")]
    reefers = available.loc[available.temp.eq("reefer")]
    chilled = float(
        orders.loc[orders.temp_requirement.eq("chilled"), "order_volume_m3"].sum()
    )
    ceiling = float(2 * reefers.volume_cap_m3.sum())
    metrics = checked["metrics"]
    text = f"""# Peak-day prioritization policy

Whole orders use available home-depot vehicles. Prioritize chilled Fresh volume, then previously
deferred orders, total served orders, days since last service and lower trip time, in that order.
The bounded CP-SAT run fixes each achieved earlier objective before considering the next.
Its recorded bounds describe remaining optimality gaps; a time-limited incumbent is not a proof
that the chosen deferrals are globally unavoidable.

The independently checked allocation serves {metrics['orders_served']} of 85 orders, including
{metrics['served_chilled_m3']:.3f} m³ chilled and {metrics['previously_deferred_served']} previously
deferred orders. It uses {metrics['total_trip_minutes']} trip-minutes with zero violations.
Chilled demand is {chilled:.3f} m³ versus an optimistic two-trip reefer ceiling of {ceiling:.3f} m³:
at least {max(0, chilled-ceiling):.3f} m³ cannot be served even before access, district, weight or
handling-time limits. Actual unserved chilled demand is {chilled-metrics['served_chilled_m3']:.3f} m³.
A whole order exceeding the largest available {available.volume_cap_m3.max():.3f} m³ vehicle is
individually infeasible. Other listed deferrals reflect the policy and interacting constraints.

Each trip has one brand/district, exact integer-scaled volume/weight and eligible reefer/van access.
Time = outbound + (number of orders − 1) × inter-stop + sum of every order's handling allowance,
including separate orders for the same outlet. No return time is added. Each vehicle has at most
two trips overall; Fresh trip minutes sum to ≤270, Style+Tech minutes to ≤480 independently.
Detailed calculations are in allocation_trips.csv. Costs below are missed orders and volume;
no monetary rates were supplied. Reconsider deferred service on the next operating day.

| Deferred order | Brand | Volume m³ | Prior deferral | Cause |
|---|---|---:|---|---|
"""
    for row in deferred.itertuples():
        cause = (
            "Exceeds every available vehicle"
            if row.order_volume_m3 > available.volume_cap_m3.max()
            else "Priority allocation under constrained eligible fleet/time"
        )
        text += f"| {row.order_ref} | {row.brand} | {row.order_volume_m3:.3f} | {row.deferred_yesterday} | {cause} |\n"
    (ROOT / "reports/ALLOCATION_POLICY.md").write_text(text)
    checked["trips"].to_csv(ROOT / "reports/allocation_trips.csv", index=False)
    print("Wrote private allocation policy and per-trip calculations")


if __name__ == "__main__":
    main()
