"""Export all three challenge submissions from backend-owned data and verified models."""

import argparse
import json
import pandas as pd
from runtime import ROOT
from task2b import inputs, greedy, allocation, validate, optimize
from waypoint_intelligence import engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Improve the feasible baseline with sequential CP-SAT objectives",
    )
    parser.add_argument(
        "--seconds", type=float, default=20, help="Time cap per optimization stage"
    )
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error("seconds must be between 1 and 3600")
    destination = ROOT / "submissions"
    destination.mkdir(exist_ok=True, parents=True)
    template = pd.read_csv(ROOT / "data/Submission Templates/submission_task1.csv")
    # Preserve the template ordering while bounding each inference batch.
    predictions = []
    identities = template.delivery_id.tolist()
    for start in range(0, len(identities), 500):
        predictions.extend(
            row.model_dump()
            for row in engine.predict_ids(identities[start : start + 500]).predictions
        )
    pd.DataFrame(predictions)[template.columns].to_csv(
        destination / "submission_task1.csv", index=False
    )
    result = engine.demand_forecast()
    forecast = pd.DataFrame(
        [
            {
                "row_id": row.row_id,
                "pred_total_volume_m3": row.total_m3,
                "pred_chilled_volume_m3": row.chilled_m3,
            }
            for row in result.rows
        ]
    )
    forecast.to_csv(destination / "submission_task2a.csv", index=False)
    context = inputs()
    orders, fleet, travel, allowance = context
    selected = ROOT / "artifacts/submission_task2b.csv"
    if selected.exists():
        candidate = pd.read_csv(selected)
    else:
        candidate = allocation(orders, greedy(*context))
    stages = []
    if args.optimize:
        initial = {
            int(orders.index[orders.order_ref.eq(row.order_ref)][0]): (
                row.vehicle_id,
                int(row.trip_id),
            )
            for row in candidate[candidate.decision.eq("served")].itertuples()
        }
        assigned, stages = optimize(*context, initial, limit=args.seconds)
        candidate = allocation(orders, assigned)
    checked = validate(candidate, *context)
    if checked["errors"]:
        raise ValueError(checked["errors"])
    candidate.to_csv(destination / "submission_task2b.csv", index=False)
    report = {
        "model_version": result.model_version,
        "task1_rows": len(predictions),
        "task2a_rows": len(forecast),
        "task2b_rows": len(candidate),
        "allocation": checked["metrics"],
        "errors": checked["errors"],
        "optimization_stages": stages,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/runtime_exports.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
