"""Direct ten-week forecasts with calendar-aware component models and temporal backtests."""

import json
import numpy as np
import pandas as pd
import joblib
from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from runtime import (
    ROOT,
    Run,
    write_json,
    table,
    sha,
    history_and_checkpoints,
    catboost_options,
    experiment_identity,
)
from features import read


def history():
    a = read("Training Data", "deliveries_train.csv")
    t = read("Test Data", "task1_test_inputs.csv")
    orders = pd.concat([a, t], ignore_index=True)
    assert not orders.delivery_id.duplicated().any()
    cal = read("General Data", "calendar.csv")
    cal["week_start"] = (
        pd.to_datetime(cal.date) - pd.to_timedelta(cal.dow, unit="D")
    ).dt.strftime("%Y-%m-%d")
    wc = (
        cal.groupby(["iso_year", "iso_week"], sort=False)
        .agg(
            week_start=("week_start", "min"),
            operating_days=("is_operating", "sum"),
            paydays=("is_payday", "sum"),
            holidays=("is_holiday", "sum"),
            festival_ramp_sum=("festival_ramp", "sum"),
            festival_ramp_max=("festival_ramp", "max"),
            monsoon=("monsoon", "mean"),
            festival=("festival", lambda x: "+".join(sorted(set(x.dropna())))),
        )
        .reset_index()
        .sort_values("week_start")
        .reset_index(drop=True)
    )
    wc["week_idx"] = np.arange(len(wc))
    wc["annual_sin"] = np.sin(2 * np.pi * wc.iso_week / 52.18)
    wc["annual_cos"] = np.cos(2 * np.pi * wc.iso_week / 52.18)
    for dow in range(6):
        daily = cal[cal.dow == dow].groupby(["iso_year", "iso_week"]).is_operating.sum()
        wc["operating_dow_" + str(dow)] = [
            daily.get((r.iso_year, r.iso_week), 0) for r in wc.itertuples()
        ]
    orders = orders.merge(
        cal[["date", "iso_year", "iso_week"]],
        left_on="order_date",
        right_on="date",
        validate="many_to_one",
    )
    orders["component"] = orders.brand + "_" + orders.temp_requirement
    orders["series"] = orders.depot + "|" + orders.component
    keys = sorted(orders["series"].unique())
    assert len(keys) == 8 and len(orders) == 97321
    aggregate = orders.groupby(["series", "iso_year", "iso_week"]).order_volume_m3.sum()
    last = int(wc.loc[wc.week_start <= orders.order_date.max(), "week_idx"].max())
    records = []
    for series in keys:
        depot, component = series.split("|")
        brand, temp = component.split("_")
        for r in wc.itertuples():
            records.append(
                {
                    "series": series,
                    "depot": depot,
                    "brand": brand,
                    "temp": temp,
                    "week_idx": r.week_idx,
                    "iso_year": r.iso_year,
                    "iso_week": r.iso_week,
                    "volume": float(aggregate.get((series, r.iso_year, r.iso_week), 0))
                    if r.week_idx <= last
                    else np.nan,
                }
            )
    panel = pd.DataFrame(records)
    write_json(
        ROOT / "reports" / "task2a_data_audit.json",
        {
            "orders": len(orders),
            "historical_weeks": last + 1,
            "series": keys,
            "total_source_volume_m3": orders.order_volume_m3.sum(),
            "total_panel_volume_m3": panel.volume.sum(),
            "last_observed_week": last,
            "demand_date": "order_date",
            "all_statuses_counted": True,
        },
    )
    assert np.isclose(orders.order_volume_m3.sum(), panel.volume.sum())
    return panel, wc, last


CALCOLS = [
    "operating_days",
    "paydays",
    "holidays",
    "festival_ramp_sum",
    "festival_ramp_max",
    "monsoon",
    "annual_sin",
    "annual_cos",
] + ["operating_dow_" + str(i) for i in range(6)]
CATS = ["series", "depot", "brand", "temp", "festival"]


def examples(panel, wc, origins):
    rows = []
    for series, group in panel.groupby("series", sort=True):
        vals = group.set_index("week_idx").volume
        depot = group.depot.iloc[0]
        brand = group.brand.iloc[0]
        temp = group.temp.iloc[0]
        for origin in origins:
            for h in range(1, 11):
                target = origin + h
                if target >= len(wc):
                    continue
                calendar = wc.iloc[target]
                row = {
                    "series": series,
                    "depot": depot,
                    "brand": brand,
                    "temp": temp,
                    "festival": calendar.festival or "_none_",
                    "origin": origin,
                    "target": target,
                    "horizon": h,
                    "volume": vals.get(target, np.nan),
                    "week_idx": target,
                }
                row.update({c: calendar[c] for c in CALCOLS})
                for lag in [0, 1, 2, 3, 7, 12, 25, 51]:
                    row["lag_" + str(lag)] = (
                        vals.get(origin - lag, np.nan) if origin - lag >= 0 else np.nan
                    )
                for window in [4, 8, 13]:
                    v = vals.loc[max(0, origin - window + 1) : origin]
                    row["mean_" + str(window)] = v.mean()
                    row["std_" + str(window)] = v.std(ddof=0)
                row["annual_lag"] = (
                    vals.get(target - 52, np.nan) if target - 52 >= 0 else np.nan
                )
                # The annual target-week lag is always before origin for h <= 10.
                assert target - 52 <= origin
                rows.append(row)
    return pd.DataFrame(rows)


def transform(frame, scales, variant):
    columns = CATS + ["horizon", "week_idx"] + CALCOLS
    if variant not in ["calendar"]:
        columns += (
            ["lag_" + str(lag) for lag in [0, 1, 2, 3, 7, 12, 25, 51]]
            + ["mean_" + str(w) for w in [4, 8, 13]]
            + ["std_" + str(w) for w in [4, 8, 13]]
            + ["annual_lag"]
        )
    x = frame[columns].copy()
    for c in CATS:
        x[c] = x[c].fillna("_none_").astype(str)
    s = frame.series.map(scales).to_numpy()
    for c in x:
        if c.startswith(("lag_", "mean_", "std_")) or c == "annual_lag":
            x[c] = x[c] / s
    return x


def forecast(bundle, frame):
    if bundle["kind"] == "blend":
        return sum(w * forecast(b, frame) for w, b in bundle["components"])
    if bundle["kind"] == "segmented":
        p = np.empty(len(frame))
        for key, model in bundle["models"].items():
            mask = frame[bundle["segment"]].eq(key).to_numpy()
            p[mask] = forecast(model, frame.loc[mask])
        return p
    if bundle["kind"] == "recent":
        return np.maximum(
            frame.mean_4.to_numpy()
            * frame.operating_days.to_numpy()
            / bundle["recent_operating_denominator"],
            0,
        )
    if bundle["kind"] == "annual":
        return np.maximum(frame.annual_lag.fillna(frame.mean_4).to_numpy(), 0)
    x = transform(frame, bundle["scales"], bundle["features"])
    p = bundle["model"].predict(x)
    return np.maximum(p * frame.series.map(bundle["scales"]).to_numpy(), 0)


def outputs(frame, p, wc):
    d = frame[["depot", "brand", "temp", "series", "target", "horizon"]].copy()
    d["prediction"] = p
    d["actual"] = frame.volume.to_numpy()
    totals = (
        d.groupby(["depot", "brand", "target", "horizon"])
        .agg(prediction=("prediction", "sum"), actual=("actual", "sum"))
        .reset_index()
    )
    totals["output"] = "total"
    chilled = d[(d.brand == "Fresh") & (d.temp == "chilled")][
        ["depot", "brand", "target", "horizon", "prediction", "actual"]
    ].copy()
    chilled["output"] = "chilled"
    out = pd.concat([totals, chilled], ignore_index=True)
    out = out.merge(
        wc[["week_idx", "iso_year", "iso_week", "festival_ramp_max"]],
        left_on="target",
        right_on="week_idx",
        validate="many_to_one",
    )
    return out


def scores(frame, p, wc):
    out = outputs(frame, p, wc)
    out["error"] = (out.prediction - out.actual).abs()
    groups = out.groupby(["depot", "brand", "output"]).agg(
        error=("error", "sum"), actual=("actual", "sum")
    )
    return {
        "macro_WAPE": float((groups.error / groups.actual.clip(lower=1e-9)).mean()),
        "aggregate_WAPE": float(out.error.sum() / out.actual.sum()),
        "MAE": float(out.error.mean()),
        "RMSE": float(np.sqrt(np.mean((out.prediction - out.actual) ** 2))),
    }, out


def fit(panel, wc, cutoff, variant, fold, depth=4, rate=0.05, l2=20, alpha=10):
    raw = examples(panel, wc, range(12, cutoff))
    raw = raw[raw.target <= cutoff].copy()
    stopcut = cutoff - 3
    train = raw[raw.target < stopcut]
    stop = raw[raw.target >= stopcut]
    # Scales use each underlying observed training week once, not replicated direct-horizon rows.
    scales = (
        panel[(panel.week_idx < stopcut) & panel.volume.notna()]
        .groupby("series")
        .volume.mean()
        .clip(lower=0.01)
        .to_dict()
    )
    config = {
        "cutoff": cutoff,
        "internal_stop_target_weeks": list(range(stopcut, cutoff + 1)),
        "feature_variant": variant,
        "train_rows": len(train),
        "stop_rows": len(stop),
        "depth": depth,
        "learning_rate": rate,
        "l2_leaf_reg": l2,
        "alpha": alpha,
        "iterations": 3000,
        "direct_horizons": list(range(1, 11)),
    }
    with Run("task2a", variant, fold, config) as run:
        if variant == "recent":
            operating = float(
                wc.iloc[max(0, cutoff - 3) : cutoff + 1].operating_days.mean()
            )
            bundle = {"kind": "recent", "recent_operating_denominator": operating}
            run.meta.update(
                completed_steps="not applicable", best_step="not applicable"
            )
        elif variant == "annual":
            bundle = {"kind": "annual"}
            run.meta.update(
                completed_steps="not applicable", best_step="not applicable"
            )
        else:
            f = "calendar" if variant == "calendar" else "full"
            x = transform(train, scales, f)
            v = transform(stop, scales, f)
            y = train.volume / train.series.map(scales)
            z = stop.volume / stop.series.map(scales)
            if variant.startswith("ridge"):
                nums = [c for c in x if c not in CATS]

                def ridge():
                    prep = ColumnTransformer(
                        [
                            ("cat", OneHotEncoder(handle_unknown="ignore"), CATS),
                            (
                                "num",
                                make_pipeline(
                                    SimpleImputer(
                                        strategy="median", keep_empty_features=True
                                    ),
                                    StandardScaler(),
                                ),
                                nums,
                            ),
                        ]
                    )
                    return make_pipeline(prep, Ridge(alpha=alpha, solver="lsqr"))

                if variant.startswith(("ridge_brand_", "ridge_series_")):
                    segment = (
                        "brand" if variant.startswith("ridge_brand_") else "series"
                    )
                    models = {}
                    for key in sorted(train[segment].unique()):
                        mask = train[segment].eq(key).to_numpy()
                        child = ridge()
                        child.fit(x.loc[mask], y.loc[mask])
                        models[key] = {
                            "kind": "model",
                            "features": f,
                            "scales": scales,
                            "model": child,
                        }
                    model = None
                    run.meta.update(
                        completed_steps="separate ridge fits",
                        best_step="not applicable",
                    )
                else:
                    model = ridge()
                    model.fit(x, y)
                    run.meta.update(
                        completed_steps=np.asarray(model[-1].n_iter_).tolist(),
                        best_step="not applicable",
                    )
            else:
                total = 3000
                while True:
                    model = CatBoostRegressor(
                        iterations=total,
                        depth=depth,
                        learning_rate=rate,
                        l2_leaf_reg=l2,
                        loss_function="RMSE",
                        **catboost_options(),
                        random_seed=42,
                        train_dir=str(run.path / "catboost"),
                        metric_period=1,
                    )
                    model.fit(
                        x,
                        y,
                        cat_features=CATS,
                        eval_set=(v, z),
                        use_best_model=False,
                        early_stopping_rounds=200,
                        verbose=1,
                        save_snapshot=True,
                        snapshot_interval=60,
                        snapshot_file=str(run.path / "recovery.snapshot"),
                    )
                    hist = model.get_evals_result()["validation"]["RMSE"]
                    if (
                        model.tree_count_ < total
                        or total == 10000
                        or np.argmin(hist) < total - 200
                    ):
                        break
                    total = 6000 if total == 3000 else 10000
                    print(f"EXTEND {run.id} cap={total}", flush=True)
                run.meta["config"]["iterations"] = total
                model = history_and_checkpoints(run, model, model.get_evals_result())
                reload = CatBoostRegressor()
                reload.load_model(str(run.path / "best_model.cbm"))
                assert np.allclose(model.predict(v), reload.predict(v), atol=1e-10)
            bundle = {
                "kind": "model",
                "features": f,
                "scales": scales,
                "model": model,
                "run_id": run.id,
                "best_step": run.meta["best_step"],
            }
            if variant.startswith(("ridge_brand_", "ridge_series_")):
                bundle.update(kind="segmented", segment=segment, models=models)
        internal = examples(panel, wc, [max(12, cutoff - 4)])
        internal = internal[internal.target <= cutoff]
        stats, out = scores(internal, forecast(bundle, internal), wc)
        run.meta["metrics"] = stats
        (run.path / "evaluation.md").write_text(
            "# Internal chronological evaluation\n\n"
            + table([stats])
            + "\n"
            + table(out),
            encoding="utf-8",
        )
        out.to_csv(run.path / "internal_predictions.csv", index=False)
        run.save(bundle)
    return bundle, run


def evaluation(runpath, frame, p, wc):
    stats, out = scores(frame, p, wc)
    tables = []
    for cols in [["depot", "brand", "output"], ["horizon"]]:
        for key, g in out.groupby(cols):
            tables.append(
                {
                    "group": "/".join(cols),
                    "value": str(key),
                    "n": len(g),
                    "WAPE": float(
                        (g.prediction - g.actual).abs().sum() / g.actual.sum()
                    ),
                    "MAE": float((g.prediction - g.actual).abs().mean()),
                }
            )
    festival = out[out.festival_ramp_max.gt(0)]
    if len(festival):
        tables.append(
            {
                "group": "festival",
                "value": "ramp > 0",
                "n": len(festival),
                "WAPE": float(
                    (festival.prediction - festival.actual).abs().sum()
                    / festival.actual.sum()
                ),
            }
        )
    write_json(runpath / "outer_evaluation.json", {"overall": stats, "groups": tables})
    out.to_csv(runpath / "outer_predictions.csv", index=False)
    (runpath / "outer_evaluation.md").write_text(
        "# Ten-week outer evaluation\n\n"
        + table([stats])
        + "\n## Subgroups\n\n"
        + table(tables),
        encoding="utf-8",
    )
    return stats


def infer_task2a():
    panel, wc, last = history()
    bundle = joblib.load(ROOT / "artifacts" / "forecast.joblib")
    frame = examples(panel, wc, [last])
    p = forecast(bundle, frame)
    out = outputs(frame, p, wc)
    template = read("Submission Templates", "submission_task2a.csv")
    inputs = read("Test Data", "task2a_test_inputs.csv")
    values = out.pivot(
        index=["depot", "brand", "iso_year", "iso_week"],
        columns="output",
        values="prediction",
    ).reset_index()
    values["chilled"] = values.chilled.fillna(0)
    values = inputs.merge(
        values, on=["depot", "brand", "iso_year", "iso_week"], validate="one_to_one"
    )
    sub = (
        template[["row_id"]]
        .merge(
            values[["row_id", "total", "chilled"]],
            on="row_id",
            sort=False,
            validate="one_to_one",
        )
        .rename(
            columns={
                "total": "pred_total_volume_m3",
                "chilled": "pred_chilled_volume_m3",
            }
        )
    )
    assert len(sub) == 60 and sub.row_id.equals(template.row_id)
    assert (
        np.isfinite(sub.iloc[:, 1:].to_numpy()).all()
        and sub.iloc[:, 1:].ge(0).all().all()
    )
    assert sub.pred_chilled_volume_m3.le(sub.pred_total_volume_m3 + 1e-9).all()
    export = ROOT / "submissions" / "submission_task2a.csv"
    if export.exists():
        previous = pd.read_csv(export)
        assert previous.row_id.equals(sub.row_id)
        assert np.allclose(
            previous.iloc[:, 1:], sub.iloc[:, 1:], rtol=1e-10, atol=1e-10
        ), "Reloaded forecast differs from frozen export"
    sub.to_csv(export, index=False)
    print("Task 2A inputs:", inputs.head().to_string(index=False), flush=True)
    print(
        "Task 2A saved-model predictions:",
        sub.head().to_string(index=False),
        flush=True,
    )
    return sub


def task2a(require_task1=True):
    if require_task1:
        gate = json.loads(
            (ROOT / "reports" / "task1_complete.json").read_text(encoding="utf-8")
        )
        assert gate.get("fresh_process_verified") and gate.get("documentation_complete")
    print(
        "TASK 2A START: Demand includes all statuses and Task 1 test orders.",
        flush=True,
    )
    panel, wc, last = history()
    specs = {
        "recent": {},
        "annual": {},
        "calendar": {},
        "ridge_1": {"alpha": 1},
        "ridge_10": {"alpha": 10},
        "ridge_100": {"alpha": 100},
        "ridge_1000": {"alpha": 1000},
        "ridge_brand_10": {"alpha": 10},
        "ridge_brand_100": {"alpha": 100},
        "ridge_series_10": {"alpha": 10},
        "ridge_series_100": {"alpha": 100},
        "full": {},
        "shallow": {"depth": 3, "rate": 0.07, "l2": 30},
        "deeper": {"depth": 5, "rate": 0.03, "l2": 10},
        "regularized": {"depth": 4, "rate": 0.04, "l2": 50},
    }

    def origin(year, week):
        return int(
            wc.loc[(wc.iso_year == year) & (wc.iso_week == week), "week_idx"].iloc[0]
        )

    dev = [("dev1", origin(2025, 13)), ("dev2", origin(2025, 39))]
    preds = {}
    stats = {name: [] for name in specs}
    comparison = []
    for fold, cut in dev:
        frame = examples(panel, wc, [cut])
        assert frame.volume.notna().all()
        for variant, config in specs.items():
            bundle, run = fit(panel, wc, cut, variant, fold, **config)
            p = forecast(bundle, frame)
            m = evaluation(run.path, frame, p, wc)
            stats[variant].append(m["macro_WAPE"])
            preds[(fold, variant)] = p
            comparison.append({"fold": fold, "variant": variant, **m})
            (ROOT / "reports" / "TASK2A_COMPARISON.md").write_text(
                "# Forecast development variants\n\n" + table(comparison),
                encoding="utf-8",
            )
            print(f"OUTER Task2A {fold} {variant}: {m}", flush=True)
    rank = sorted(stats, key=lambda k: np.mean(stats[k]))
    choice = rank[0]
    best = float(np.mean(stats[choice]))
    second = rank[1]
    weight = 1.0
    for other in [name for name in rank[:4] if name != choice]:
        for w in np.arange(0.1, 1.0, 0.1):
            values = [
                scores(
                    examples(panel, wc, [cut]),
                    w * preds[(fold, choice)] + (1 - w) * preds[(fold, other)],
                    wc,
                )[0]["macro_WAPE"]
                for fold, cut in dev
            ]
            with Run(
                "task2a",
                "blend_" + choice + "_" + other + "_" + str(round(w, 1)),
                "development",
                {"components": [choice, other], "weight": w},
            ) as run:
                run.meta.update(
                    metrics={"macro_WAPE": float(np.mean(values))},
                    completed_steps="not applicable",
                    best_step="component checkpoints",
                )
            if (
                np.mean(values) < best
                and np.mean(values) < np.mean(stats[choice]) * 0.99
            ):
                best = float(np.mean(values))
                second = other
                weight = float(w)
    selection = {
        "variant": choice,
        "second": second,
        "weight": weight,
        "development_macro_WAPE": best,
        "ranking": {name: float(np.mean(stats[name])) for name in rank},
        "final_training_origin": "2026 week 3",
        "inference_history_through": "2026 week 13",
        "no_post_holdout_refit": True,
    }
    write_json(ROOT / "reports" / "task2a_selection.json", selection)
    cut = origin(2026, 3)
    final, run = fit(panel, wc, cut, choice, "final", **specs[choice])
    if weight < 1:
        other, _ = fit(panel, wc, cut, second, "final", **specs[second])
        final = {"kind": "blend", "components": [(weight, final), (1 - weight, other)]}
    frame = examples(panel, wc, [cut])
    assert frame.volume.notna().all()
    with Run("task2a", "locked_selection", "final_holdout", selection) as run:
        m = evaluation(run.path, frame, forecast(final, frame), wc)
        run.meta.update(metrics=m, completed_steps="selected component checkpoints")
        run.save(final)
        joblib.dump(final, ROOT / "artifacts" / "forecast.joblib")
        restored = joblib.load(ROOT / "artifacts" / "forecast.joblib")
        assert np.allclose(
            forecast(final, frame), forecast(restored, frame), atol=1e-10
        )
    sub = infer_task2a()
    (ROOT / "reports" / "TASK2A_RESULTS.md").write_text(
        "# Task 2A complete\n\n## Independent ten-week holdout\n\n"
        + table([m])
        + "\n## Locked selection\n\n```json\n"
        + json.dumps(selection, indent=2)
        + "\n```\n\nThe exact evaluated model is saved; there is no post-holdout refit. Future inference uses all 117 observed weeks, including Task 1 test orders, to construct origin-available lag features. Configuration selection used only the two development origins.\n",
        encoding="utf-8",
    )
    write_json(
        ROOT / "reports" / "task2a_complete.json",
        {
            "status": "passed",
            "rows": len(sub),
            "selection": selection,
            "holdout_metrics": m,
            "submission_sha256": sha(ROOT / "submissions" / "submission_task2a.csv"),
            **experiment_identity(),
        },
    )
    print("TASK 2A MODEL GATE PASSED:", m, flush=True)


if __name__ == "__main__":
    from runtime import install_logging

    install_logging()
    task2a()
