"""Original datathon demand aggregation and saved-bundle inference; no training."""

from __future__ import annotations
from typing import Any


import numpy as np
import pandas as pd
from .paths import ROOT
from .features import read


# Training audits are written by explicit training commands, never by HTTP inference.
def write_json(*args: Any) -> Any:
    return None


def history() -> Any:
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


def examples(panel: Any, wc: Any, origins: Any) -> Any:
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


def transform(frame: Any, scales: Any, variant: Any) -> Any:
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


def forecast(bundle: Any, frame: Any) -> Any:
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


def outputs(frame: Any, p: Any, wc: Any) -> Any:
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
