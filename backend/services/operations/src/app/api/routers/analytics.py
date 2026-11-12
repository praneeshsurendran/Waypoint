from __future__ import annotations
from fastapi import APIRouter
from app.api.deps import CurrentUser, require_role
from app.application.use_cases import analytics as use_cases

router = APIRouter(prefix="/analytics", tags=["analytics"])
_DISPATCHER = require_role("DISPATCHER")


@router.get("/demand-forecast")
def demand_forecast(current_user: CurrentUser, _: None = _DISPATCHER):
    return use_cases.demand_forecast(current_user=current_user, _=_)
