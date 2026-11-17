"""Auditable experiment runtime. All stdout/stderr is mirrored to Markdown."""

from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import sys
import threading
import time
import traceback
import re
import importlib.metadata
import platform
import tempfile
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    log_loss,
    brier_score_loss,
    roc_auc_score,
    average_precision_score,
)

_backend_root = Path(__file__).resolve().parents[1]
_default_workspace = _backend_root / "private" / "intelligence"
_legacy_workspace = _backend_root / "private" / "datathon"
if not _default_workspace.exists() and _legacy_workspace.exists():
    _default_workspace = _legacy_workspace
ROOT = (
    Path(
        os.getenv("WAYPOINT_INTELLIGENCE_WORKSPACE")
        or os.getenv("WAYPOINT_DATATHON_WORKSPACE")
        or _default_workspace
    )
    .expanduser()
    .resolve()
)
ROOT.mkdir(parents=True, exist_ok=True)
DATA_ROOT = (
    Path(os.environ.get("WAYPOINT_DATA_DIR", ROOT / "data")).expanduser().resolve()
)
TRAIN_THREADS = max(1, int(os.environ.get("WAYPOINT_THREADS", "4")))
CATBOOST_DEVICE = os.environ.get("WAYPOINT_CATBOOST_DEVICE", "CPU").upper()
if CATBOOST_DEVICE not in ["CPU", "GPU"]:
    raise ValueError("WAYPOINT_CATBOOST_DEVICE must be CPU or GPU")
TZ = dt.timezone(dt.timedelta(hours=5, minutes=30))
for folder in ["reports", "runs", "artifacts", "submissions", "checkpoints"]:
    (ROOT / folder).mkdir(exist_ok=True)


def stamp():
    return dt.datetime.now(TZ).isoformat(timespec="seconds")


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, Path):
        return str(x.relative_to(ROOT)) if x.is_relative_to(ROOT) else str(x)
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def write_json(p, x):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=p.parent,
        prefix="." + p.name,
        suffix=".tmp",
        delete=False,
    ) as f:
        json.dump(clean(x), f, indent=2, allow_nan=False)
        temporary = f.name
    os.replace(temporary, p)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


_identity = None


def experiment_identity():
    global _identity
    if _identity is None:
        files = sorted(DATA_ROOT.rglob("*.csv"))
        if not files:
            raise FileNotFoundError(
                f"No competition CSV files under {DATA_ROOT}; set WAYPOINT_DATA_DIR"
            )
        manifest = {str(p.relative_to(DATA_ROOT)): sha(p) for p in files}
        write_json(ROOT / "provenance.json", manifest)
        _identity = {
            "dataset_manifest_sha256": hashlib.sha256(
                json.dumps(manifest, sort_keys=True).encode()
            ).hexdigest(),
            "code_sha256": {p.name: sha(p) for p in ROOT.glob("*.py")},
        }
    return _identity


def identity_matches(metadata):
    return all(metadata.get(k) == v for k, v in experiment_identity().items())


def catboost_options():
    params = {"task_type": CATBOOST_DEVICE, "thread_count": TRAIN_THREADS}
    if CATBOOST_DEVICE == "GPU":
        params.update(
            devices=os.environ.get("WAYPOINT_GPU_DEVICES", "0"), gpu_ram_part=0.5
        )
    return params


def cache_signature(config, frames, source=None):
    digest = hashlib.sha256(
        json.dumps(
            clean({"config": config, **experiment_identity()}), sort_keys=True
        ).encode()
    )
    for frame in frames:
        digest.update(json.dumps(list(frame.columns)).encode())
        digest.update(
            pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes()
        )
    if source is not None:
        digest.update(joblib.hash(source).encode())
    return digest.hexdigest()


def table(d):
    if not isinstance(d, pd.DataFrame):
        d = pd.DataFrame(d)
    if d.empty:
        return "(no rows)\n"

    def cell(v):
        return (
            str(v).replace("|", "/").replace("\n", " ")
            if not isinstance(v, float)
            else f"{v:.8g}"
        )

    return (
        "| "
        + " | ".join(map(str, d.columns))
        + " |\n| "
        + " | ".join(["---"] * len(d.columns))
        + " |\n"
        + "".join(
            "| " + " | ".join(cell(v) for v in row) + " |\n"
            for row in d.itertuples(index=False, name=None)
        )
    )


class Router:
    def __init__(self, terminal, task=None):
        self.terminal = terminal
        self.current = None
        self.lock = threading.RLock()
        log = ROOT / "reports" / (f"TRAINING_{task}.md" if task else "TRAINING_LOG.md")
        self.global_log = (
            ROOT / "reports" / "training_log_continuation.md"
            if log.exists()
            and log.read_text(encoding="utf-8").startswith(
                "# Complete console history index"
            )
            else log
        )

    def write(self, s):
        if not s:
            return 0
        original_len = len(s)
        match = re.search(r"^(\d+):.*best:.*\((\d+)\)", s)
        if match:
            s = (
                s.rstrip("\r\n")
                + f" | rounds_since_best={int(match[1])-int(match[2])}\n"
            )
        with self.lock:
            self.terminal.write(s)
            self.terminal.flush()
            with (ROOT / "progress.log").open("a", encoding="utf-8") as f:
                f.write(s)
            with self.global_log.open("a", encoding="utf-8") as f:
                f.write(s)
            if self.current:
                with (self.current / "training.md").open("a", encoding="utf-8") as f:
                    f.write(s)
        return original_len

    def flush(self):
        self.terminal.flush()

    def isatty(self):
        return False


router = None


def install_logging(task=None):
    global router
    router = Router(sys.stdout, task)
    sys.stdout = router
    sys.stderr = router
    print(
        f"\n[{stamp()}] SESSION START device={CATBOOST_DEVICE} training_threads={TRAIN_THREADS}",
        flush=True,
    )


def metric(y, p, task):
    y = np.asarray(y)
    p = np.asarray(p)
    if task == "service":
        return {
            "RMSE": float(np.sqrt(mean_squared_error(y, p))),
            "MAE": float(mean_absolute_error(y, p)),
        }
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return {
        "Logloss": float(log_loss(y, p, labels=[0, 1])),
        "Brier": float(brier_score_loss(y, p)),
        "ROC_AUC": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None,
        "PR_AUC": float(average_precision_score(y, p)) if np.any(y) else None,
    }


def eval_report(runpath, frame, y, p, task):
    rows = []
    for col in ["brand", "depot", "dock_type", "order_size_band", "seq"]:
        if col not in frame:
            continue
        for value, idx in frame.groupby(col, observed=True).indices.items():
            rows.append(
                {
                    "group": col,
                    "value": value,
                    "n": len(idx),
                    **metric(np.asarray(y)[idx], np.asarray(p)[idx], task),
                }
            )
    stats = metric(y, p, task)
    text = "# Evaluation\n\n" + table([stats]) + "\n## Subgroups\n\n" + table(rows)
    if task == "late":
        prob = np.clip(np.asarray(p), 1e-7, 1 - 1e-7)
        bins = (
            pd.DataFrame(
                {
                    "p": prob,
                    "y": np.asarray(y),
                    "bin": np.minimum((prob * 10).astype(int), 9),
                }
            )
            .groupby("bin")
            .agg(n=("y", "size"), predicted=("p", "mean"), observed=("y", "mean"))
            .reset_index()
        )
        text += "\n## Probability reliability\n\n" + table(bins)
    (Path(runpath) / "evaluation.md").write_text(text, encoding="utf-8")
    write_json(Path(runpath) / "evaluation.json", {"overall": stats, "groups": rows})
    return stats


class Run:
    def __init__(self, task, variant, fold, config=None, parent=None):
        self.task, self.variant, self.fold = task, variant, fold
        self.id = f"{task}__{variant}__{fold}"
        base = self.id
        attempt = 1
        while (ROOT / "runs" / self.id / "metadata.json").exists():
            self.id = base + f"__attempt_{attempt:02d}"
            attempt += 1
        self.path = ROOT / "runs" / self.id
        self.path.mkdir(parents=True, exist_ok=True)
        self.meta = {
            "run_id": self.id,
            "task": task,
            "variant": variant,
            "fold": fold,
            "parent": parent,
            "config": config or {},
            "seed": 42,
            "started": stamp(),
            "status": "running",
            **experiment_identity(),
        }
        self.meta["python"] = sys.version
        self.meta["packages"] = {
            p: importlib.metadata.version(p)
            for p in [
                "numpy",
                "pandas",
                "scikit-learn",
                "catboost",
                "lightgbm",
                "ortools",
            ]
        }
        self.meta["hardware"] = {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "training_threads": TRAIN_THREADS,
            "catboost_device": CATBOOST_DEVICE,
        }
        self.start = time.monotonic()
        self.stop = threading.Event()
        self.previous = None

    def __enter__(self):
        (self.path / "training.md").write_text(
            "# "
            + self.id
            + "\n\n## Configuration\n\n```json\n"
            + json.dumps(clean(self.meta), indent=2)
            + "\n```\n\n## Complete console output\n\n```text\n",
            encoding="utf-8",
        )
        if router:
            self.previous = router.current
            router.current = self.path
        print(
            f'\n[{stamp()}] RUN {self.id}: {json.dumps(clean(self.meta["config"]))}',
            flush=True,
        )

        def heartbeat():
            while not self.stop.wait(25):
                print(
                    f"[{stamp()}] HEARTBEAT {self.id} elapsed={time.monotonic()-self.start:.1f}s stage=training/evaluation",
                    flush=True,
                )

        self.thread = threading.Thread(target=heartbeat, daemon=True)
        self.thread.start()
        write_json(self.path / "metadata.json", self.meta)
        return self

    def save(self, obj, name="model.joblib"):
        p = self.path / name
        joblib.dump(obj, p)
        self.meta.setdefault("artifacts", []).append(
            {"path": str(p.relative_to(ROOT)), "sha256": sha(p)}
        )
        return p

    def __exit__(self, typ, value, tb):
        self.stop.set()
        self.thread.join(timeout=2)
        self.meta.update(
            ended=stamp(),
            elapsed_seconds=time.monotonic() - self.start,
            status="failed" if typ else "completed",
        )
        if typ:
            self.meta["error"] = str(value)
            traceback.print_exception(typ, value, tb)
        print(
            f'[{stamp()}] END {self.id} status={self.meta["status"]} elapsed={self.meta["elapsed_seconds"]:.1f}s metrics={self.meta.get("metrics")}',
            flush=True,
        )
        with (self.path / "training.md").open("a", encoding="utf-8") as f:
            f.write("\n```\n")
        if router:
            router.current = self.previous
        write_json(self.path / "metadata.json", self.meta)
        refresh_registry()
        return False


def refresh_registry():
    rows = []
    checkpoints = []
    for p in sorted((ROOT / "runs").glob("*/metadata.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        rows.append(
            {
                "run": d["run_id"],
                "status": d["status"],
                "steps": d.get("completed_steps", "N/A"),
                "requested_steps": d.get(
                    "requested_steps", d.get("config", {}).get("iterations", "N/A")
                ),
                "best_step": d.get("best_step", "N/A"),
                "metrics": json.dumps(d.get("metrics", {})),
                "record": f'[console](../runs/{d["run_id"]}/training.md) [metadata](../runs/{d["run_id"]}/metadata.json)'
                + (
                    f' [iterations](../runs/{d["run_id"]}/iterations.md)'
                    if (p.parent / "iterations.md").exists()
                    else ""
                ),
            }
        )
        checkpoints.extend(d.get("checkpoints", []))
        checkpoints.extend(
            {
                "run": d["run_id"],
                "step": c["step"],
                "path": c["path"],
                "sha256": c["sha256"],
                "kind": "allocation incumbent",
            }
            for c in d.get("solution_checkpoints", [])
        )
    (ROOT / "reports" / "EXPERIMENTS.md").write_text(
        "# Every attempted experiment\n\nEnvironment details and historical limitations: [experiment context](EXPERIMENT_CONTEXT.md). Full variant configuration, features and chronological partitions are in each linked metadata record.\n\n"
        + table(rows),
        encoding="utf-8",
    )
    (ROOT / "reports" / "CHECKPOINTS.md").write_text(
        "# Checkpoint inventory\n\n" + table(checkpoints), encoding="utf-8"
    )


def history_and_checkpoints(run, model, evals, classification=False):
    columns = {
        f"{partition}_{name}": values
        for partition, items in evals.items()
        for name, values in items.items()
    }
    n = max(map(len, columns.values()))
    frame = pd.DataFrame({k: pd.Series(v) for k, v in columns.items()})
    frame.insert(0, "step", np.arange(1, n + 1))
    frame.to_csv(run.path / "iterations.csv", index=False)
    (run.path / "iterations.md").write_text(
        "# Every training iteration\n\n" + table(frame), encoding="utf-8"
    )
    validation = next(k for k in evals if k != "learn")
    main = next(iter(evals[validation]))
    scores = np.asarray(evals[validation][main])
    best = int(np.nanargmin(scores)) + 1
    run.meta.update(
        completed_steps=n,
        best_step=best,
        requested_steps=run.meta["config"].get("iterations", 3000),
        stopped_reason="200 rounds without improvement"
        if n < run.meta["config"].get("iterations", 3000)
        else "iteration cap",
        overfitting_observed=bool(scores[-1] > scores[best - 1] * 1.001),
        validation_deterioration=float(scores[-1] - scores[best - 1]),
    )
    model.save_model(str(run.path / "full_model.cbm"))
    selected = model.copy()
    selected.shrink(ntree_end=best)
    selected.save_model(str(run.path / "best_model.cbm"))
    run.meta["checkpoints"] = []
    for step in sorted(set(list(range(100, n + 1, 100)) + [best, n])):
        cp = model.copy()
        cp.shrink(ntree_end=step)
        p = ROOT / "checkpoints" / run.id / f"step_{step:05d}.cbm"
        p.parent.mkdir(parents=True, exist_ok=True)
        cp.save_model(str(p))
        run.meta["checkpoints"].append(
            {
                "run": run.id,
                "step": step,
                "validation_metric": float(scores[step - 1]),
                "best": step == best,
                "path": str(p.relative_to(ROOT)),
                "sha256": sha(p),
            }
        )
    print(
        f'CHECKPOINT {run.id} completed={n} best_step={best} score={scores[best-1]:.8f} overfitting={run.meta["overfitting_observed"]}',
        flush=True,
    )
    return selected
