from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_contracts.runtime import DemandForecast
from fastapi import APIRouter
from app.api.deps import CurrentUser, require_role
from app.application.use_cases import analytics as use_cases

router = APIRouter(prefix="/analytics", tags=["analytics"])
_DISPATCHER = require_role("DISPATCHER")


@router.get("/demand-forecast", response_model=DemandForecast, response_model_exclude_unset=True)
def demand_forecast(current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]) -> DemandForecast:
    return TypeAdapter(DemandForecast).validate_python(
        use_cases.demand_forecast(current_user=current_user, _=None)
    )
