"""Fit compact Task 1 runtime bundles from scratch; preserve the copied forecast bundle.

This is a bounded deployment candidate, not a claim to reproduce the original full search.
Chronological holdout stays excluded from fitting. Run explicitly, never at API startup.
"""

import json
import hashlib
import joblib
import numpy as np
from features import prepare_task1, features
from task1 import linear_model, predict
from runtime import ROOT, metric, write_json


def main():
    data = prepare_task1()
    train = data[data.dispatch_date < "2026-01-05"].copy()
    holdout = data[data.dispatch_date.between("2026-01-05", "2026-02-14")].copy()
    if train.empty or holdout.empty:
        raise ValueError("Chronological training and holdout must both be available")
    x, cats = features(train, "linear")
    report = {
        "training_rows": len(train),
        "holdout_rows": len(holdout),
        "fit_before": "2026-01-05",
        "candidate": "original linear feature pipeline; compact CPU deployment candidate",
        "models": {},
    }
    for task in ("service", "late"):
        model = linear_model(x, cats, task, alpha=10)
        model.fit(x, train[task])
        bundle = {
            "kind": "linear",
            "task": task,
            "feature_set": "linear",
            "columns": list(x),
            "categories": cats,
            "model": model,
        }
        values = predict(bundle, holdout)
        report["models"][task] = metric(holdout[task], values, task)
        target = ROOT / "artifacts" / (task + ".joblib")
        joblib.dump(bundle, target)
        restored = joblib.load(target)
        np.testing.assert_allclose(
            values, predict(restored, holdout), rtol=1e-10, atol=1e-10
        )
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "artifacts").glob("*.joblib")
    }
    write_json(
        ROOT / "artifacts" / "manifest.json", {"sha256": hashes, "training": report}
    )
    write_json(ROOT / "reports" / "runtime_evaluation.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
