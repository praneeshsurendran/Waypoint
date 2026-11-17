from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_contracts.runtime import DemandForecast
from fastapi import APIRouter, Header, Query
from waypoint_contracts.intelligence import PredictionResponse
from app.api.deps import DbDep
from app.application.use_cases.predictions import plan_predictions as predict_plan
from app.api.deps import CurrentUser, require_role
from app.application.use_cases import analytics as use_cases

router = APIRouter(prefix="/analytics", tags=["analytics"])
_DISPATCHER = require_role("DISPATCHER")


@router.get("/demand-forecast", response_model=DemandForecast, response_model_exclude_unset=True)
def demand_forecast(
    current_user: CurrentUser,
    _: Annotated[Actor, _DISPATCHER],
    authorization: Annotated[str | None, Header()] = None,
) -> DemandForecast:
    return TypeAdapter(DemandForecast).validate_python(
        use_cases.demand_forecast(current_user=current_user, _=None, authorization=authorization)
    )


@router.get("/plan-predictions", response_model=PredictionResponse)
def plan_predictions(
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, _DISPATCHER],
    authorization: Annotated[str | None, Header()] = None,
    plan_id: int | None = Query(None, ge=1),
) -> PredictionResponse:
    return predict_plan(db, current_user, authorization, plan_id)
