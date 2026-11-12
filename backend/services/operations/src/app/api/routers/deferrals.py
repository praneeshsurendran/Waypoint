from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

import datetime as dt
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.order import DeferralCreate, DeferralHistoryOut
from waypoint_contracts.plan import DeferralOut
from app.application.use_cases import deferrals as use_cases

router = APIRouter(prefix="/deferrals", tags=["deferrals"])
_DISPATCHER = require_role("DISPATCHER")


@router.post("", response_model=DeferralOut, status_code=status.HTTP_201_CREATED)
def create_deferral(
    body: DeferralCreate, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> DeferralOut:
    return TypeAdapter(DeferralOut).validate_python(
        use_cases.create_deferral(body=body, db=db, current_user=current_user, _=None)
    )


@router.get("", response_model=list[DeferralOut])
def list_deferrals(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    date: Optional[dt.date] = Query(None),
) -> list[DeferralOut]:
    return TypeAdapter(list[DeferralOut]).validate_python(
        use_cases.list_deferrals(db=db, current_user=current_user, _=None, date=date)
    )


@router.get("/outlets/{outlet_id}/history", response_model=list[DeferralHistoryOut])
def outlet_deferral_history(
    outlet_id: str, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> list[DeferralHistoryOut]:
    """Returns the deferral history for a specific outlet (via its orders)."""
    return TypeAdapter(list[DeferralHistoryOut]).validate_python(
        use_cases.outlet_deferral_history(
            outlet_id=outlet_id, db=db, current_user=current_user, _=None
        )
    )
