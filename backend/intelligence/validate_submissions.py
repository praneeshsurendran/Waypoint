"""Verify all template keys/columns, fresh-process predictions and allocation feasibility."""

from pathlib import Path
import subprocess
import sys
import pandas as pd
import numpy as np
from runtime import ROOT, write_json, sha, table
from features import read
from task2b import validate


def verify():
    rows = []
    for name, id_cols, count in [
        ("task1", ["delivery_id"], 5014),
        ("task2a", ["row_id"], 60),
        ("task2b", ["scenario", "order_ref", "outlet_id"], 85),
    ]:
        p = ROOT / "submissions" / f"submission_{name}.csv"
        d = pd.read_csv(p)
        template = read("Submission Templates", p.name)
        assert list(d.columns) == list(template.columns), (name, list(d.columns))
        assert len(d) == count and d[id_cols].equals(template[id_cols]), name
        if name != "task2b":
            assert np.isfinite(d.drop(columns=id_cols).to_numpy()).all()
            assert d.drop(columns=id_cols).ge(0).all().all()
        if name == "task1":
            assert d.pred_late_prob.between(0, 1).all()
        if name == "task2a":
            assert d.pred_chilled_volume_m3.le(d.pred_total_volume_m3 + 1e-9).all()
            keys = read("Test Data", "task2a_test_inputs.csv")
            aligned = d.merge(keys, on="row_id", validate="one_to_one")
            assert (
                aligned.loc[
                    aligned.brand.isin(["Style", "Tech"]), "pred_chilled_volume_m3"
                ]
                .eq(0)
                .all()
            )
        rows.append(
            {"task": name, "rows": count, "sha256": sha(p), "template_verified": True}
        )
    result = subprocess.run(
        [sys.executable, "-u", "inference.py", "--task", "all"],
        cwd=Path(__file__).resolve().parent,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    checked = validate(pd.read_csv(ROOT / "submissions" / "submission_task2b.csv"))
    assert not checked["errors"], checked["errors"]
    (ROOT / "reports" / "SUBMISSION_VERIFICATION.md").write_text(
        "# Submission verification\n\n"
        + table(rows)
        + "\n## Allocation feasibility\n\n"
        + table([checked["metrics"]])
        + "\n## Fresh saved-model inference\n\n```text\n"
        + result.stdout
        + result.stderr
        + "\n```\n",
        encoding="utf-8",
    )
    write_json(
        ROOT / "reports" / "SUBMISSION_VERIFICATION.json",
        {
            "submissions": rows,
            "allocation_metrics": checked["metrics"],
            "errors": checked["errors"],
            "fresh_process_predictions_verified": True,
        },
    )
    print("ALL SUBMISSIONS VERIFIED", rows, checked["metrics"], flush=True)
    return rows


if __name__ == "__main__":
    verify()
