"""Trusted local artifacts, loaded once after SHA-256 verification; never accept uploaded pickle."""

from __future__ import annotations
import datetime as dt
import hashlib
import json
from functools import lru_cache
from typing import Any
import joblib
import pandas as pd
from waypoint_contracts.runtime import Backtest
from waypoint_contracts.intelligence import (
    ForecastResponse,
    ForecastRow,
    PredictionResponse,
    StopPrediction,
    PlannedDelivery,
)
from .paths import ROOT
from .features import prepare_task1, read, enrich
from .predict import predict
from .forecast import history, examples, forecast, outputs


class ModelUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=3)
def bundle(name: str) -> dict[str, Any]:
    if name not in ("service", "late", "forecast"):
        raise ModelUnavailable("Unknown model")
    path = ROOT / "artifacts" / (name + ".joblib")
    try:
        manifest = json.loads((ROOT / "artifacts" / "manifest.json").read_text())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if manifest["sha256"].get(path.name) != digest:
            raise ModelUnavailable("Model integrity check failed")
        import warnings
        from sklearn.exceptions import InconsistentVersionWarning

        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            model = joblib.load(path)
        if not isinstance(model, dict) or "kind" not in model:
            raise ModelUnavailable("Unsupported model bundle")
        return model
    except (OSError, KeyError, ValueError, UserWarning) as error:
        raise ModelUnavailable("Verified model artifacts are not configured") from error


def model_version() -> str:
    for name in ("service", "late", "forecast"):
        bundle(name)
    return hashlib.sha256(
        (ROOT / "artifacts" / "manifest.json").read_bytes()
    ).hexdigest()[:16]


@lru_cache(maxsize=1)
def test_frame() -> Any:
    return prepare_task1(True).set_index("delivery_id", drop=False)


def predict_frame(frame: Any) -> PredictionResponse:
    if frame.delivery_id.duplicated().any():
        raise ValueError("Delivery identifiers must be unique")
    service, late = predict(bundle("service"), frame), predict(bundle("late"), frame)
    return PredictionResponse(
        model_version=model_version(),
        predictions=[
            StopPrediction(
                delivery_id=str(identity),
                pred_service_min=float(minutes),
                pred_late_prob=float(probability),
            )
            for identity, minutes, probability in zip(
                frame.delivery_id, service, late, strict=True
            )
        ],
    )


def predict_ids(identities: list[str]) -> PredictionResponse:
    frame = test_frame()
    if len(set(identities)) != len(identities) or not set(identities).issubset(
        frame.index
    ):
        raise ValueError("Unknown or duplicate delivery identifier")
    return predict_frame(frame.loc[identities].reset_index(drop=True))


def predict_planned(deliveries: list[PlannedDelivery]) -> PredictionResponse:
    frame = pd.DataFrame([row.model_dump(mode="json") for row in deliveries])
    outlets = read("General Data", "outlets.csv").set_index("outlet_id")
    vehicles = read("General Data", "vehicles.csv").set_index("vehicle_id")
    calendar = read("General Data", "calendar.csv").set_index("date")
    if (
        not set(frame.outlet_id).issubset(outlets.index)
        or not set(frame.vehicle_id).issubset(vehicles.index)
        or not set(frame.dispatch_date).issubset(calendar.index)
    ):
        raise ValueError("Plan references unavailable outlet, vehicle or calendar data")
    for column in ("brand", "district", "depot"):
        frame[column] = frame.outlet_id.map(outlets[column])
    frame["vehicle_type"] = frame.vehicle_id.map(vehicles.type)
    frame["vehicle_temp"] = frame.vehicle_id.map(vehicles.temp)
    frame["monsoon"] = frame.dispatch_date.map(calendar.monsoon)
    frame["dow"] = frame.dispatch_date.map(calendar.dow)
    frame["seq"] = frame.seq_in_route
    # Feature engineering consumes local HH:MM; seconds are not silently interpreted as hours.
    for column in ("planned_depart_time", "planned_arrival_time"):
        frame[column] = frame[column].str.slice(0, 5)
    windows = outlets[["window_open_time", "window_close_time"]]
    frame["window_open_time"] = frame.outlet_id.map(windows.window_open_time)
    frame["window_close_time"] = frame.outlet_id.map(windows.window_close_time)
    return predict_frame(enrich(frame))


@lru_cache(maxsize=1)
def demand_forecast() -> ForecastResponse:
    panel, weeks, last = history()
    frame = examples(panel, weeks, [last])
    values = outputs(frame, forecast(bundle("forecast"), frame), weeks)
    template = read("Test Data", "task2a_test_inputs.csv")
    rows = []
    for row in template.itertuples():
        selected = values[
            (values.depot == row.depot)
            & (values.brand == row.brand)
            & (values.iso_year == row.iso_year)
            & (values.iso_week == row.iso_week)
        ]
        total = float(selected.loc[selected.output == "total", "prediction"].iloc[0])
        chilled = (
            float(selected.loc[selected.output == "chilled", "prediction"].iloc[0])
            if row.brand == "Fresh"
            else 0.0
        )
        rows.append(
            ForecastRow(
                row_id=str(row.row_id),
                depot=row.depot,
                brand=row.brand,
                iso_year=int(row.iso_year),
                iso_week=int(row.iso_week),
                total_m3=total,
                chilled_m3=min(chilled, total),
            )
        )
    # Re-evaluate the saved artifact at its locked chronological holdout origin.
    holdout_origin = int(
        weeks.loc[(weeks.iso_year == 2026) & (weeks.iso_week == 3), "week_idx"].iloc[0]
    )
    holdout_frame = examples(panel, weeks, [holdout_origin])
    held = outputs(holdout_frame, forecast(bundle("forecast"), holdout_frame), weeks)
    held["error"] = (held.prediction - held.actual).abs()

    def wape(rows: Any) -> float | None:
        actual = float(rows.actual.sum())
        return float(100 * rows.error.sum() / actual) if actual > 0 else None

    backtest: Backtest = {
        "weeks": [f"2026-W{week:02}" for week in range(4, 14)],
        "wape_percent": wape(held),
        "by_depot": {str(depot): wape(group) for depot, group in held.groupby("depot")},
    }
    return ForecastResponse(
        model_version=model_version(),
        method="Saved datathon Ridge ensemble; chronological fitting; requested-week demand including deferred orders",
        data_as_of=dt.date.fromisoformat(
            str(read("Test Data", "task1_test_inputs.csv").order_date.max())
        ),
        rows=rows,
        backtest=backtest,
    )
