"""Task 1: chronological development, independent holdout, saved-artifact inference."""

import json
import time
import numpy as np
import pandas as pd
import joblib
from catboost import CatBoostRegressor, CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.isotonic import IsotonicRegression
from lightgbm import (
    LGBMRegressor,
    LGBMClassifier,
    early_stopping,
    log_evaluation,
    record_evaluation,
)
from runtime import (
    ROOT,
    Run,
    metric,
    eval_report,
    history_and_checkpoints,
    write_json,
    table,
    sha,
    catboost_options,
    TRAIN_THREADS,
    cache_signature,
    experiment_identity,
    identity_matches,
)
from features import prepare_task1, features, read

FOLDS = [("dev1", "2025-10-13", "2025-11-22"), ("dev2", "2025-11-24", "2026-01-03")]
CONFIGS = {
    "basic": {
        "feature_set": "basic",
        "depth": 6,
        "learning_rate": 0.05,
        "l2_leaf_reg": 10,
    },
    "full": {
        "feature_set": "full",
        "depth": 6,
        "learning_rate": 0.05,
        "l2_leaf_reg": 10,
    },
    "log_full": {
        "feature_set": "full",
        "depth": 6,
        "learning_rate": 0.05,
        "l2_leaf_reg": 10,
        "log_target": True,
    },
    "tune_shallow": {
        "feature_set": "full",
        "depth": 4,
        "learning_rate": 0.07,
        "l2_leaf_reg": 20,
    },
    "tune_deep": {
        "feature_set": "full",
        "depth": 8,
        "learning_rate": 0.03,
        "l2_leaf_reg": 5,
    },
    "tune_regularized": {
        "feature_set": "full",
        "depth": 5,
        "learning_rate": 0.04,
        "l2_leaf_reg": 30,
    },
    "upstream": {
        "feature_set": "upstream",
        "depth": 6,
        "learning_rate": 0.05,
        "l2_leaf_reg": 10,
    },
    "lightgbm": {"feature_set": "full", "num_leaves": 31, "learning_rate": 0.05},
    "lightgbm_regularized": {
        "feature_set": "full",
        "num_leaves": 15,
        "learning_rate": 0.03,
    },
    "linear": {"feature_set": "linear", "alpha": 10},
    "baseline": {"feature_set": "basic"},
}


def linear_model(x, cats, task, alpha=10):
    nums = [c for c in x if c not in cats]
    prep = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), cats),
            (
                "num",
                make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
                nums,
            ),
        ]
    )
    model = (
        Ridge(alpha=alpha, solver="lsqr")
        if task == "service"
        else LogisticRegression(C=1 / alpha, max_iter=1000, solver="lbfgs")
    )
    return make_pipeline(prep, model)


def predict(bundle, d):
    kind = bundle["kind"]
    task = bundle["task"]
    if kind == "blend":
        p = sum(w * predict(b, d) for w, b in bundle["components"])
    elif kind == "brands":
        p = np.empty(len(d))
        for brand, model in bundle["models"].items():
            mask = d.brand.eq(brand).to_numpy()
            p[mask] = predict(model, d.loc[mask])
    elif kind == "baseline":
        p = (
            d.service_group.map(bundle["groups"]).fillna(bundle["default"]).to_numpy()
            if task == "service"
            else np.full(len(d), bundle["default"])
        )
    else:
        if bundle.get("upstream_source"):
            d = augment_upstream(d, bundle["upstream_source"])
        x, _ = features(d, bundle["feature_set"])
        x = x[bundle["columns"]]
        p = (
            bundle["model"].predict_proba(x)[:, 1]
            if task == "late"
            else np.asarray(bundle["model"].predict(x)).ravel()
        )
        if bundle.get("log_target"):
            p = np.expm1(p) * bundle.get("bias_correction", 1)
    if bundle.get("calibration"):
        method, cal = bundle["calibration"]
        p = (
            cal.predict_proba(
                np.log(
                    np.clip(p, 1e-7, 1 - 1e-7) / (1 - np.clip(p, 1e-7, 1 - 1e-7))
                ).reshape(-1, 1)
            )[:, 1]
            if method == "sigmoid"
            else cal.predict(p)
        )
    return np.maximum(p, 0) if task == "service" else np.clip(p, 1e-7, 1 - 1e-7)


def augment_upstream(d, source=None, oof=None):
    d = d.copy()
    p = np.asarray(oof) if oof is not None else predict(source, d)
    d["_pred_service"] = p
    d["prefix_pred_service"] = (
        d.groupby("route_id")._pred_service.cumsum() - d._pred_service
    )
    d["prefix_service_excess"] = d.prefix_pred_service - d.prefix_service_allowance_min
    return d


def fit_one(train, stop, task, variant, fold, source=None, config=None):
    cfg = dict(config or CONFIGS[variant])
    cfg["iterations"] = 3000
    cfg.update(
        train_rows=len(train),
        stop_rows=len(stop),
        train_start=train.dispatch_date.min(),
        train_end=train.dispatch_date.max(),
        stop_start=stop.dispatch_date.min(),
        stop_end=stop.dispatch_date.max(),
        hypothesis=variant,
    )
    target = "service" if task == "service" else "late"
    x, cats = features(train, cfg["feature_set"])
    v, _ = features(stop, cfg["feature_set"])
    signature = cache_signature(
        {**cfg, **catboost_options()},
        [x.assign(_target=train[target]), v.assign(_target=stop[target])],
        source,
    )
    base = f"task1_{task}__{variant}__{fold}"
    caches = [
        p
        for p in (ROOT / "runs").glob(base + "*")
        if p.name == base or p.name.startswith(base + "__attempt_")
    ]
    for cache in sorted(caches, reverse=True):
        if (cache / "metadata.json").exists() and (cache / "model.joblib").exists():
            metadata = json.loads((cache / "metadata.json").read_text(encoding="utf-8"))
            if (
                metadata["status"] == "completed"
                and metadata.get("cache_signature") == signature
                and metadata.get("model_sha256") == sha(cache / "model.joblib")
            ):
                print(
                    f'REUSE verified completed experiment {metadata["run_id"]}',
                    flush=True,
                )
                result = joblib.load(cache / "model.joblib")
                run = type("CachedRun", (), {"path": cache, "meta": metadata})()
                return result, run
    with Run("task1_" + task, variant, fold, cfg) as run:
        run.meta["cache_signature"] = signature
        y = train[target].to_numpy()
        z = stop[target].to_numpy()
        bundle = {
            "task": task,
            "feature_set": cfg["feature_set"],
            "columns": list(x),
            "categories": cats,
        }
        if variant == "baseline":
            bundle.update(
                kind="baseline",
                groups=train.groupby("service_group").service.mean().to_dict()
                if task == "service"
                else {},
                default=float(np.mean(y)),
            )
            run.meta.update(
                completed_steps="not applicable", best_step="not applicable"
            )
        elif variant == "linear":
            model = linear_model(x, cats, task, cfg.get("alpha", 10))
            model.fit(x, y)
            bundle.update(kind="linear", model=model)
            n = getattr(model[-1], "n_iter_", None)
            run.meta.update(
                completed_steps=np.asarray(n).tolist()
                if n is not None
                else "not applicable",
                best_step="not applicable",
            )
        elif variant.startswith("lightgbm"):
            prep = ColumnTransformer(
                [
                    ("cat", OneHotEncoder(handle_unknown="ignore"), cats),
                    (
                        "num",
                        SimpleImputer(strategy="median"),
                        [c for c in x if c not in cats],
                    ),
                ]
            )
            xt = prep.fit_transform(x)
            vt = prep.transform(v)
            cls = LGBMClassifier if task == "late" else LGBMRegressor
            model = cls(
                n_estimators=3000,
                num_leaves=cfg["num_leaves"],
                learning_rate=cfg["learning_rate"],
                min_child_samples=50,
                reg_lambda=10,
                verbosity=-1,
                n_jobs=TRAIN_THREADS,
                random_state=42,
            )
            hist = {}
            capture = {"best": float("inf"), "step": 0, "snapshot_at": time.monotonic()}

            def preserve(env):
                step = env.iteration + 1
                score = next(
                    item[2]
                    for item in env.evaluation_result_list
                    if item[0] == "validation"
                    and item[1] == ("binary_logloss" if task == "late" else "rmse")
                )
                if score < capture["best"]:
                    capture.update(best=score, step=step)
                if step % 100 == 0:
                    cp = ROOT / "checkpoints" / run.id / f"step_{step:05d}.txt"
                    cp.parent.mkdir(parents=True, exist_ok=True)
                    env.model.save_model(str(cp), num_iteration=step)
                    print(
                        f'CHECKPOINT {run.id} round={step} best={capture["best"]:.8f} best_round={capture["step"]} rounds_since_best={step-capture["step"]}',
                        flush=True,
                    )
                if time.monotonic() - capture["snapshot_at"] >= 60:
                    env.model.save_model(
                        str(run.path / "recovery_lightgbm.txt"), num_iteration=step
                    )
                    capture["snapshot_at"] = time.monotonic()
                    print(f"RECOVERY SNAPSHOT {run.id} round={step}", flush=True)
                if step == 3000 or step - capture["step"] >= 200:
                    env.model.save_model(
                        str(run.path / "full_model.txt"), num_iteration=step
                    )

            preserve.order = 25
            model.fit(
                xt,
                y,
                eval_set=[(xt, y), (vt, z)],
                eval_names=["train", "validation"],
                eval_metric="binary_logloss" if task == "late" else "rmse",
                callbacks=[
                    early_stopping(200, first_metric_only=True),
                    log_evaluation(1),
                    record_evaluation(hist),
                    preserve,
                ],
            )
            bundle.update(kind="linear", model=make_pipeline(prep, model))
            scores = hist["validation"]["binary_logloss" if task == "late" else "rmse"]
            n = len(scores)
            best = model.best_iteration_
            run.meta.update(
                completed_steps=n,
                best_step=best,
                overfitting_observed=scores[-1] > scores[best - 1] * 1.001,
            )
            hh = pd.DataFrame(
                {
                    f"{k}_{m}": vals
                    for k, items in hist.items()
                    for m, vals in items.items()
                }
            )
            hh.insert(0, "step", range(1, n + 1))
            hh.to_csv(run.path / "iterations.csv", index=False)
            (run.path / "iterations.md").write_text(
                "# Every iteration\n\n" + table(hh), encoding="utf-8"
            )
            run.meta["checkpoints"] = []
            from lightgbm import Booster

            full = Booster(model_file=str(run.path / "full_model.txt"))
            assert full.num_trees() == n, (full.num_trees(), n)
            for step in sorted(set(list(range(100, n + 1, 100)) + [best, n])):
                cp = ROOT / "checkpoints" / run.id / f"step_{step:05d}.txt"
                cp.parent.mkdir(parents=True, exist_ok=True)
                full.save_model(str(cp), num_iteration=step)
                run.meta["checkpoints"].append(
                    {
                        "run": run.id,
                        "step": step,
                        "validation_metric": scores[step - 1],
                        "best": step == best,
                        "path": str(cp.relative_to(ROOT)),
                        "sha256": sha(cp),
                    }
                )
            bestfile = run.path / "best_model.txt"
            full.save_model(str(bestfile), num_iteration=best)
            restored = Booster(model_file=str(bestfile))
            expected = (
                model.predict_proba(vt)[:, 1] if task == "late" else model.predict(vt)
            )
            assert np.allclose(expected, restored.predict(vt), rtol=1e-10, atol=1e-10)
        else:
            logtarget = bool(cfg.get("log_target"))
            yt = np.log1p(y) if logtarget else y
            zt = np.log1p(z) if logtarget else z
            cls = CatBoostClassifier if task == "late" else CatBoostRegressor
            params = {k: cfg[k] for k in ["depth", "learning_rate", "l2_leaf_reg"]}
            total = 3000
            while True:
                # A fitted CatBoost estimator cannot change parameters. A fresh
                # estimator resumes the same snapshot when extending the cap.
                model = cls(
                    **params,
                    iterations=total,
                    loss_function="Logloss" if task == "late" else "RMSE",
                    eval_metric="Logloss" if task == "late" else "RMSE",
                    **catboost_options(),
                    random_seed=42,
                    metric_period=1,
                    train_dir=str(run.path / "catboost"),
                    allow_writing_files=True,
                )
                model.fit(
                    x,
                    yt,
                    cat_features=cats,
                    eval_set=(v, zt),
                    early_stopping_rounds=200,
                    use_best_model=False,
                    verbose=1,
                    save_snapshot=True,
                    snapshot_file=str(run.path / "recovery.snapshot"),
                    snapshot_interval=60,
                )
                if model.tree_count_ < total or total == 10000:
                    break
                hist = model.get_evals_result()["validation"]
                vals = next(iter(hist.values()))
                if np.argmin(vals) < total - 200:
                    break
                total = 6000 if total == 3000 else 10000
                print(
                    f"EXTEND {run.id} validation still improving; new cap={total}",
                    flush=True,
                )
            run.meta["config"]["iterations"] = total
            best = history_and_checkpoints(
                run, model, model.get_evals_result(), task == "late"
            )
            bundle.update(
                kind="catboost", model=best, log_target=logtarget, bias_correction=1.0
            )
            # Bias adjustment is estimated only from training residuals, never outer validation.
            if logtarget:
                residual = np.log1p(y) - best.predict(x)
                bundle["bias_correction"] = float(np.mean(np.exp(residual)))
            reloaded = cls()
            reloaded.load_model(str(run.path / "best_model.cbm"))
            assert np.allclose(
                best.predict(x.iloc[:20]), reloaded.predict(x.iloc[:20]), atol=1e-10
            )
        if source:
            bundle["upstream_source"] = source
        p = predict(bundle, stop)
        run.meta["metrics"] = eval_report(run.path, stop, z, p, task)
        run.meta["training_metrics"] = metric(y, predict(bundle, train), task)
        run.save(bundle)
        run.meta["model_sha256"] = sha(run.path / "model.joblib")
        write_json(
            run.path / "feature_schema.json",
            {"columns": list(x), "categories": cats, "target": target},
        )
    return bundle, run


def split_before(d, start):
    past = d[d.dispatch_date < start].copy()
    cut = (pd.Timestamp(start) - pd.Timedelta(days=28)).strftime("%Y-%m-%d")
    return past[past.dispatch_date < cut].copy(), past[past.dispatch_date >= cut].copy()


def upstream_oof(d):
    values = np.zeros(len(d))
    quarters = pd.to_datetime(d.dispatch_date).dt.to_period("Q")
    for period in sorted(quarters.unique()):
        mask = (quarters == period).to_numpy()
        past = d[quarters < period]
        if len(past) < 1000:
            values[mask] = d.loc[mask, "service_allowance_min"]
            continue
        # Historical service model uses only earlier quarters, with its own chronological stop period.
        stopcut = (
            pd.Timestamp(past.dispatch_date.max()) - pd.Timedelta(days=14)
        ).strftime("%Y-%m-%d")
        model, _ = fit_one(
            past[past.dispatch_date < stopcut],
            past[past.dispatch_date >= stopcut],
            "service",
            "linear",
            "upstream_" + str(period),
        )
        values[mask] = predict(model, d.loc[mask])
    return values


def task1():
    print("TASK 1 START: label construction and join assertions", flush=True)
    d = prepare_task1()
    test = prepare_task1(True)
    assert len(d) == 91894 and len(test) == 5014
    write_json(
        ROOT / "reports" / "task1_data_audit.json",
        {
            "labelled_orders": len(d),
            "test_orders": len(test),
            "unrun_excluded": 413,
            "late_rate": d.late.mean(),
            "service_quantiles": d.service.quantile([0, 0.5, 0.99, 1]).to_dict(),
            "formula": "leave - max(arrival, opening); late = arrival > closing",
        },
    )
    selections = (
        json.loads(
            (ROOT / "reports" / "task1_selection.json").read_text(encoding="utf-8")
        )
        if (ROOT / "reports" / "task1_selection.json").exists()
        else {}
    )
    comparison = []
    dev_predictions = {}
    dev_models = {}
    existing = ROOT / "reports" / "TASK1_COMPARISON.md"
    if existing.exists():
        lines = [
            line
            for line in existing.read_text(encoding="utf-8").splitlines()
            if line.startswith("|")
        ]
        if len(lines) > 2:
            keys = [s.strip() for s in lines[0].split("|")[1:-1]]
            for line in lines[2:]:
                vals = [s.strip() for s in line.split("|")[1:-1]]
                row = dict(zip(keys, vals))
                if row.get("task") == "service":
                    comparison.append(row)
    for task in ["service", "late"]:
        completed_service = [
            json.loads(p.read_text())
            for p in (ROOT / "runs").glob(
                "task1_service__locked_selection__final_holdout*/metadata.json"
            )
        ]
        verified_service = (
            any(
                m.get("status") == "completed"
                and identity_matches(m)
                and m.get("export_sha256") == sha(ROOT / "artifacts" / "service.joblib")
                for m in completed_service
            )
            if (ROOT / "artifacts" / "service.joblib").exists()
            else False
        )
        if task == "service" and "service" in selections and verified_service:
            print(
                "RESUME: preserve frozen service model and its already-evaluated holdout; continue lateness.",
                flush=True,
            )
            continue
        print(
            f"TASK 1 {task}: baseline -> feature variants -> tuning -> challengers",
            flush=True,
        )
        variants = [
            "baseline",
            "linear",
            "basic",
            "full",
            "tune_shallow",
            "tune_deep",
            "tune_regularized",
            "lightgbm",
            "lightgbm_regularized",
        ]
        if task == "service":
            variants.insert(4, "log_full")
            variants.append("brands")
        else:
            oof = upstream_oof(d[d.dispatch_date < "2026-01-05"].copy())
            historical = d[d.dispatch_date < "2026-01-05"].copy()
            historical = augment_upstream(historical, oof=oof)
            d = d.merge(
                historical[
                    ["delivery_id", "prefix_pred_service", "prefix_service_excess"]
                ],
                on="delivery_id",
                how="left",
                validate="one_to_one",
            )
            variants.insert(4, "upstream")
        scores = {v: [] for v in variants}
        preds = {}
        models = {}
        for fold, start, end in FOLDS:
            train, stop = split_before(d, start)
            val = d[d.dispatch_date.between(start, end)].copy()
            source = None
            if task == "late":
                source, _ = fit_one(
                    train, stop, "service", "linear", fold + "_upstream_source"
                )
            for variant in variants:
                if variant == "brands":
                    brand_models = {}
                    for brand in ["Fresh", "Style", "Tech"]:
                        brand_models[brand], _ = fit_one(
                            train[train.brand == brand],
                            stop[stop.brand == brand],
                            task,
                            "full",
                            fold + "_" + brand,
                        )
                    bundle = {"kind": "brands", "task": task, "models": brand_models}
                    with Run(
                        "task1_service",
                        "brands",
                        fold,
                        {"hypothesis": "specialized per-brand service models"},
                    ) as run:
                        p = predict(bundle, val)
                        run.meta["metrics"] = eval_report(
                            run.path, val, val.service, p, task
                        )
                        run.meta["completed_steps"] = "see child runs"
                        run.save(bundle)
                else:
                    tr = train
                    st = stop
                    if variant == "upstream":
                        st = augment_upstream(stop, source)
                    bundle, run = fit_one(
                        tr,
                        st,
                        task,
                        variant,
                        fold,
                        source=source if variant == "upstream" else None,
                    )
                    p = predict(bundle, val)
                stats = metric(val[task], p, task)
                primary = stats["RMSE" if task == "service" else "Logloss"]
                scores[variant].append(primary)
                preds[(fold, variant)] = p
                models[(fold, variant)] = bundle
                comparison.append(
                    {"task": task, "fold": fold, "variant": variant, **stats}
                )
                pd.DataFrame(
                    {
                        "delivery_id": val.delivery_id,
                        "actual": val[task],
                        "prediction": p,
                    }
                ).to_csv(run.path / "outer_predictions.csv", index=False)
                eval_report(
                    run.path / "outer"
                    if (run.path / "outer").mkdir(exist_ok=True) is None
                    else run.path,
                    val,
                    val[task],
                    p,
                    task,
                )
                print(f"OUTER {task} {fold} {variant}: {stats}", flush=True)
                (ROOT / "reports" / "TASK1_COMPARISON.md").write_text(
                    "# Task 1 development evaluations\n\n" + table(comparison),
                    encoding="utf-8",
                )
        ranking = sorted(scores, key=lambda k: np.mean(scores[k]))
        chosen = ranking[0]
        second = ranking[1]
        from itertools import combinations

        reference = float(np.mean(scores[chosen]))
        bestscore = reference
        bestweight = 1.0
        candidates = list(
            dict.fromkeys(ranking[:3] + (["linear"] if task == "service" else []))
        )
        pair = (chosen, second)
        for left, right in combinations(candidates, 2):
            for weight in np.arange(0.1, 1.0, 0.1):
                ss = []
                for fold, start, end in FOLDS:
                    val = d[d.dispatch_date.between(start, end)]
                    pp = (
                        weight * preds[(fold, left)]
                        + (1 - weight) * preds[(fold, right)]
                    )
                    ss.append(
                        metric(val[task], pp, task)[
                            "RMSE" if task == "service" else "Logloss"
                        ]
                    )
                with Run(
                    "task1_" + task,
                    "blend_" + left + "_" + right + "_" + str(round(weight, 1)),
                    "development",
                    {
                        "components": [left, right],
                        "weight": weight,
                        "hypothesis": "blend complementary models using development folds only",
                    },
                ) as run:
                    run.meta.update(
                        metrics={"primary": float(np.mean(ss))},
                        completed_steps="not applicable",
                        best_step="component checkpoints",
                    )
                if np.mean(ss) < bestscore and np.mean(ss) < reference * 0.99:
                    bestscore = float(np.mean(ss))
                    bestweight = float(weight)
                    pair = (left, right)
        if bestweight < 1:
            chosen, second = pair
        selection = {
            "variant": chosen,
            "second": second,
            "weight": bestweight,
            "development_primary": float(bestscore),
            "ranking": {k: float(np.mean(scores[k])) for k in ranking},
        }
        if task == "late":
            vals = []
            ys = []
            for fold, start, end in FOLDS:
                vals.append(
                    bestweight * preds[(fold, chosen)]
                    + (1 - bestweight) * preds[(fold, second)]
                )
                ys.append(d[d.dispatch_date.between(start, end)].late.to_numpy())
            choices = {"none": metric(ys[1], vals[1], "late")["Logloss"]}
            calibrators = {}
            for method in ["sigmoid", "isotonic"]:
                with Run(
                    "task1_late",
                    "calibration_" + method,
                    "development",
                    {
                        "train": "dev1 out-of-fold probabilities",
                        "evaluation": "dev2 out-of-fold probabilities",
                    },
                ) as run:
                    cal = (
                        LogisticRegression(C=100, max_iter=1000)
                        if method == "sigmoid"
                        else IsotonicRegression(out_of_bounds="clip")
                    )

                    def logits(p):
                        return np.log(
                            np.clip(p, 1e-7, 1 - 1e-7)
                            / (1 - np.clip(p, 1e-7, 1 - 1e-7))
                        ).reshape(-1, 1)

                    cal.fit(logits(vals[0]) if method == "sigmoid" else vals[0], ys[0])
                    q = (
                        cal.predict_proba(logits(vals[1]))[:, 1]
                        if method == "sigmoid"
                        else cal.predict(vals[1])
                    )
                    choices[method] = metric(ys[1], q, "late")["Logloss"]
                    run.meta["metrics"] = metric(ys[1], q, "late")
                    run.save(cal)
                    run.meta["completed_steps"] = getattr(
                        cal, "n_iter_", "not applicable"
                    )
            method = min(choices, key=choices.get)
            if choices[method] >= choices["none"] * 0.99:
                method = "none"
            selection["calibration"] = method
            if method != "none":
                pp = np.concatenate(vals)
                yy = np.concatenate(ys)
                cal = (
                    LogisticRegression(C=100, max_iter=1000)
                    if method == "sigmoid"
                    else IsotonicRegression(out_of_bounds="clip")
                )
                cal.fit(logits(pp) if method == "sigmoid" else pp, yy)
                calibrators[method] = cal
        selections[task] = selection
        dev_predictions[task] = preds
        dev_models[task] = models
        write_json(ROOT / "reports" / "task1_selection.json", selections)
        # Locked configuration is retrained with a later internal stop window, then independently evaluated once.
        finaltrain = d[d.dispatch_date < "2025-12-22"].copy()
        finalstop = d[d.dispatch_date.between("2025-12-22", "2026-01-03")].copy()
        source = None
        if task == "late":
            source = joblib.load(ROOT / "artifacts" / "service.joblib")

        def finalfit(v):
            if v == "brands":
                return {
                    "kind": "brands",
                    "task": task,
                    "models": {
                        brand: fit_one(
                            finaltrain[finaltrain.brand == brand],
                            finalstop[finalstop.brand == brand],
                            task,
                            "full",
                            "final_" + brand,
                        )[0]
                        for brand in ["Fresh", "Style", "Tech"]
                    },
                }
            st = augment_upstream(finalstop, source) if v == "upstream" else finalstop
            return fit_one(
                finaltrain,
                st,
                task,
                v,
                "final",
                source=source if v == "upstream" else None,
            )[0]

        final = finalfit(chosen)
        if bestweight < 1:
            final = {
                "kind": "blend",
                "task": task,
                "components": [(bestweight, final), (1 - bestweight, finalfit(second))],
            }
        if task == "late" and selection.get("calibration") != "none":
            final["calibration"] = (
                selection["calibration"],
                calibrators[selection["calibration"]],
            )
        hold = d[d.dispatch_date.between("2026-01-05", "2026-02-14")].copy()
        with Run(
            "task1_" + task,
            "locked_selection",
            "final_holdout",
            {
                "selection": selection,
                "holdout": "2026-01-05 through 2026-02-14; not used for configuration selection",
            },
        ) as run:
            hp = predict(final, hold)
            run.meta["metrics"] = eval_report(run.path, hold, hold[task], hp, task)
            run.meta["completed_steps"] = "selected component checkpoints"
            run.save(final)
            pd.DataFrame(
                {
                    "delivery_id": hold.delivery_id,
                    "actual": hold[task],
                    "prediction": hp,
                }
            ).to_csv(run.path / "predictions.csv", index=False)
            joblib.dump(final, ROOT / "artifacts" / f"{task}.joblib")
            run.meta["export_sha256"] = sha(ROOT / "artifacts" / f"{task}.joblib")
            re = joblib.load(ROOT / "artifacts" / f"{task}.joblib")
            assert np.allclose(hp, predict(re, hold), atol=1e-10)
            print(f'FINAL TASK1 {task} HOLDOUT {run.meta["metrics"]}', flush=True)
    output = read("Submission Templates", "submission_task1.csv")
    inference = pd.DataFrame(
        {
            "delivery_id": test.delivery_id,
            "pred_service_min": predict(
                joblib.load(ROOT / "artifacts" / "service.joblib"), test
            ),
            "pred_late_prob": predict(
                joblib.load(ROOT / "artifacts" / "late.joblib"), test
            ),
        }
    )
    output = output[["delivery_id"]].merge(
        inference, on="delivery_id", validate="one_to_one", sort=False
    )
    original = read("Submission Templates", "submission_task1.csv")
    assert output.delivery_id.equals(original.delivery_id)
    assert (
        np.isfinite(output.iloc[:, 1:].to_numpy()).all()
        and output.pred_service_min.ge(0).all()
        and output.pred_late_prob.between(0, 1).all()
    )
    output.to_csv(ROOT / "submissions" / "submission_task1.csv", index=False)
    write_json(
        ROOT / "reports" / "task1_complete.json",
        {
            "status": "passed",
            "rows": len(output),
            "selection": selections,
            "submission_sha256": sha(ROOT / "submissions" / "submission_task1.csv"),
            **experiment_identity(),
        },
    )
    print(
        "TASK 1 COMPLETION GATE PASSED: models frozen, logs saved, 5,014 predictions verified.",
        flush=True,
    )


if __name__ == "__main__":
    from runtime import install_logging

    install_logging()
    task1()
