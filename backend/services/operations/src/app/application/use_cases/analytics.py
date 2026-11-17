"""Analytics router — dispatchers see depot demand history and the forecast."""

from __future__ import annotations

from pydantic import TypeAdapter
from waypoint_contracts.runtime import DemandForecast

from fastapi import HTTPException, status
from waypoint_security import Actor as CurrentUser
from app.core.config import get_settings
from app.services.demand_forecast import compute, project_capacity
from app.infrastructure import intelligence
from waypoint_contracts.runtime import DemandWeek


_DISPATCHER = None


def demand_forecast(
    current_user: CurrentUser, _: None = _DISPATCHER, authorization: str | None = None
) -> DemandForecast:
    data_root = get_settings().data_dir.rsplit("/General Data", 1)[0]
    try:
        result = TypeAdapter(DemandForecast).validate_python(compute(data_root))
        if get_settings().intelligence_url:
            learned = intelligence.forecast(authorization)
            events = {
                (row["iso_year"], row["iso_week"])
                for row in result["forecast"]
                if row["is_event_week"]
            }
            predictions: list[DemandWeek] = [
                {
                    "row_id": row.row_id,
                    "depot": row.depot,
                    "brand": row.brand,
                    "iso_year": row.iso_year,
                    "iso_week": row.iso_week,
                    "total_m3": row.total_m3,
                    "chilled_m3": row.chilled_m3,
                    "is_event_week": (row.iso_year, row.iso_week) in events,
                    "in_test_horizon": True,
                }
                for row in learned.rows
            ]
            result["method"] = (
                f"{learned.method}; history through {learned.data_as_of}; model {learned.model_version}. Holdout WAPE covers total/chilled outputs."
            )
            result["forecast"] = predictions
            result["capacity"] = project_capacity(data_root, predictions)
            result["backtest"] = learned.backtest
        if current_user.depot_id:
            depot = current_user.depot_id
            for key in ("history", "forecast"):
                result[key] = [row for row in result[key] if row["depot"] == depot]
            result["capacity"] = [row for row in result["capacity"] if row["depot"] == depot]
            previous = result["backtest"]
            result["backtest"] = {
                **previous,
                "wape_percent": previous["by_depot"].get(depot),
                "by_depot": {depot: previous["by_depot"].get(depot)},
            }
        return result
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATA_MISSING", "message": "Authorized demand data is not configured."},
        ) from exc
