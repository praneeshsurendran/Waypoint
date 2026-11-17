"""Stateless inference API; fitting is an explicit offline command, never an HTTP action."""

from __future__ import annotations
from typing import Annotated
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from waypoint_security import Principal, verified_principal
from waypoint_observability import install
from waypoint_contracts.intelligence import (
    PredictionRequest,
    PredictionResponse,
    PlannedPredictionRequest,
    ForecastResponse,
)
from . import engine

CurrentUser = Annotated[Principal, Depends(verified_principal)]


def dispatcher(user: CurrentUser) -> Principal:
    if user.role not in ("ADMIN", "DISPATCHER"):
        raise HTTPException(
            403,
            detail={
                "code": "FORBIDDEN",
                "message": "Planning predictions require a dispatcher.",
            },
        )
    return user


Dispatcher = Annotated[Principal, Depends(dispatcher)]


def create_app() -> FastAPI:
    if os.getenv("ENVIRONMENT") == "production":
        from urllib.parse import urlparse

        identity = urlparse(os.getenv("IDENTITY_URL", ""))
        if identity.scheme != "https" or not identity.hostname or identity.username:
            raise ValueError(
                "Production inference requires a verified HTTPS identity endpoint"
            )
        if not os.getenv("REDIS_URL", "").startswith("rediss://"):
            raise ValueError("Production inference requires authenticated TLS Redis")
    app = FastAPI(title="Waypoint intelligence", version="1.0.0")
    install(app)
    origins = [
        value.strip()
        for value in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if value.strip()
    ]
    if "*" in origins:
        raise ValueError("Explicit CORS origins required")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Correlation-ID",
            "traceparent",
        ],
        expose_headers=["Retry-After", "X-Correlation-ID", "traceparent"],
    )

    @app.exception_handler(FileNotFoundError)
    @app.exception_handler(engine.ModelUnavailable)
    async def unavailable(_request: Request, _error: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "MODELS_UNAVAILABLE",
                    "message": "Verified prediction artifacts are not configured.",
                }
            },
        )

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok", "service": "intelligence"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        engine.demand_forecast()
        return {"status": "ready"}

    @app.post("/api/v1/intelligence/predictions", response_model=PredictionResponse)
    def predictions(body: PredictionRequest, _user: Dispatcher) -> PredictionResponse:
        try:
            if _user.depot_id:
                frame = engine.test_frame()
                allowed = set(frame.loc[frame.depot == _user.depot_id, "delivery_id"])
                if not set(body.delivery_ids).issubset(allowed):
                    raise HTTPException(
                        403,
                        detail={
                            "code": "DEPOT_SCOPE",
                            "message": "Deliveries must belong to your depot.",
                        },
                    )
            return engine.predict_ids(body.delivery_ids)
        except ValueError as error:
            raise HTTPException(
                422, detail={"code": "INVALID_DELIVERY", "message": str(error)}
            ) from error

    @app.post(
        "/api/v1/intelligence/planned-predictions", response_model=PredictionResponse
    )
    def planned_predictions(
        body: PlannedPredictionRequest, _user: Dispatcher
    ) -> PredictionResponse:
        try:
            if _user.depot_id:
                outlets = engine.read("General Data", "outlets.csv")
                allowed = set(outlets.loc[outlets.depot == _user.depot_id, "outlet_id"])
                if any(row.outlet_id not in allowed for row in body.deliveries):
                    raise HTTPException(
                        403,
                        detail={
                            "code": "DEPOT_SCOPE",
                            "message": "Deliveries must belong to your depot.",
                        },
                    )
            return engine.predict_planned(body.deliveries)
        except ValueError as error:
            raise HTTPException(
                422, detail={"code": "INVALID_PLAN_FEATURES", "message": str(error)}
            ) from error

    @app.get("/api/v1/intelligence/forecast", response_model=ForecastResponse)
    def forecast(_user: Dispatcher) -> ForecastResponse:
        result = engine.demand_forecast()
        backtest = result.backtest
        if _user.depot_id:
            value = backtest["by_depot"].get(_user.depot_id)
            backtest = {
                **backtest,
                "wape_percent": value,
                "by_depot": {_user.depot_id: value},
            }
        return result.model_copy(
            update={
                "backtest": backtest,
                "rows": [
                    row
                    for row in result.rows
                    if not _user.depot_id or row.depot == _user.depot_id
                ],
            }
        )

    return app


app = create_app()
