"""Analytics router — dispatchers see depot demand history and the forecast."""

from __future__ import annotations

from pydantic import TypeAdapter
from waypoint_contracts.runtime import DemandForecast

from fastapi import HTTPException, status
from waypoint_security import Actor as CurrentUser
from app.core.config import get_settings
from app.services.demand_forecast import compute


_DISPATCHER = None


def demand_forecast(current_user: CurrentUser, _: None = _DISPATCHER) -> DemandForecast:
    data_root = get_settings().data_dir.rsplit("/General Data", 1)[0]
    try:
        return TypeAdapter(DemandForecast).validate_python(compute(data_root))
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATA_MISSING", "message": "Authorized demand data is not configured."},
        ) from exc
