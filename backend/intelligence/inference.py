"""Inference always loads saved artifacts; it never trains."""

import argparse
import joblib
import numpy as np
import pandas as pd
from runtime import ROOT
from features import prepare_task1, read
from task1 import predict


def infer_task1():
    d = prepare_task1(True)
    models = {
        t: joblib.load(ROOT / "artifacts" / f"{t}.joblib") for t in ["service", "late"]
    }
    values = pd.DataFrame(
        {
            "delivery_id": d.delivery_id,
            "pred_service_min": predict(models["service"], d),
            "pred_late_prob": predict(models["late"], d),
        }
    )
    template = read("Submission Templates", "submission_task1.csv")
    out = template[["delivery_id"]].merge(
        values, on="delivery_id", sort=False, validate="one_to_one"
    )
    assert out.delivery_id.equals(template.delivery_id) and len(out) == 5014
    assert np.isfinite(out.iloc[:, 1:].to_numpy()).all()
    assert out.pred_service_min.ge(0).all() and out.pred_late_prob.between(0, 1).all()
    p = ROOT / "submissions" / "submission_task1.csv"
    if p.exists():
        previous = pd.read_csv(p)
        assert previous.delivery_id.equals(out.delivery_id)
        assert np.allclose(
            previous.iloc[:, 1:], out.iloc[:, 1:], rtol=1e-10, atol=1e-10
        ), "Fresh inference differs from frozen export"
    out.to_csv(p, index=False)
    print(
        "Task 1 inputs:",
        d[
            [
                "delivery_id",
                "brand",
                "order_weight_kg",
                "order_volume_m3",
                "planned_arrival_time",
            ]
        ]
        .head()
        .to_string(index=False),
    )
    print("Task 1 saved-model predictions:", out.head().to_string(index=False))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["task1", "task2a", "all"], default="task1")
    args = ap.parse_args()
    if args.task in ["task1", "all"]:
        infer_task1()
    if args.task in ["task2a", "all"]:
        from task2a import infer_task2a

        infer_task2a()
