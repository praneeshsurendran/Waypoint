"""Bounded HTTP adapter; no ML framework or competition model lives in operations."""

from __future__ import annotations
from functools import lru_cache
import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from waypoint_observability import correlation_id, traceparent
from app.core.config import get_settings
from waypoint_contracts.intelligence import (
    ForecastResponse,
    PredictionResponse,
    PlannedPredictionRequest,
)


@lru_cache(maxsize=1)
def client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(15, connect=2),
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        follow_redirects=False,
    )


def remote(
    path: str, authorization: str | None, body: PlannedPredictionRequest | None = None
) -> object:
    base = get_settings().intelligence_url
    if not base:
        raise HTTPException(
            503,
            detail={
                "code": "MODELS_UNAVAILABLE",
                "message": "Prediction service is not configured.",
            },
        )
    if not authorization:
        raise HTTPException(
            401, detail={"code": "MISSING_TOKEN", "message": "Authentication required."}
        )
    try:
        response = client().request(
            "POST" if body else "GET",
            base.rstrip("/") + "/api/v1/intelligence/" + path,
            headers={
                "Authorization": authorization,
                "X-Correlation-ID": correlation_id.get(),
                "traceparent": traceparent.get() or "",
            },
            json=body.model_dump(mode="json") if body else None,
        )
        response.raise_for_status()
        result: object = response.json()
        return result
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            503,
            detail={
                "code": "MODELS_UNAVAILABLE",
                "message": "Predictions are temporarily unavailable; the saved plan remains valid.",
            },
        ) from error


def forecast(authorization: str | None) -> ForecastResponse:
    try:
        return ForecastResponse.model_validate(remote("forecast", authorization))
    except ValidationError as error:
        raise HTTPException(
            503,
            detail={
                "code": "INVALID_MODEL_RESPONSE",
                "message": "Prediction service returned an invalid response.",
            },
        ) from error


def predict(body: PlannedPredictionRequest, authorization: str | None) -> PredictionResponse:
    try:
        return PredictionResponse.model_validate(remote("planned-predictions", authorization, body))
    except ValidationError as error:
        raise HTTPException(
            503,
            detail={
                "code": "INVALID_MODEL_RESPONSE",
                "message": "Prediction service returned an invalid response.",
            },
        ) from error


def close() -> None:
    if client.cache_info().currsize:
        client().close()
        client.cache_clear()
