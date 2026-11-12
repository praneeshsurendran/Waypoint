from __future__ import annotations
import datetime as dt
from typing import Any, Optional
from fastapi import APIRouter, Body, Query, status
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.plan import PlanOut
from app.application.use_cases import plans as use_cases

router = APIRouter(prefix="/plans", tags=["plans"])
_DISPATCHER = require_role("DISPATCHER")


@router.get("", response_model=list[PlanOut])
def list_plans(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    date: Optional[dt.date] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    return use_cases.list_plans(
        db=db, current_user=current_user, _=_, date=date, status_filter=status_filter
    )


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: DbDep, current_user: CurrentUser, _: None = _DISPATCHER):
    return use_cases.get_plan(plan_id=plan_id, db=db, current_user=current_user, _=_)


@router.post("/auto-plan", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def auto_plan(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    date: Optional[dt.date] = Query(None),
):
    return use_cases.auto_plan(db=db, current_user=current_user, _=_, date=date)


@router.post("/{plan_id}/validate")
def validate_plan_endpoint(
    plan_id: int, db: DbDep, current_user: CurrentUser, _: None = _DISPATCHER
):
    """Run all constraint validators against the plan and return violations."""
    return use_cases.validate_plan_endpoint(plan_id=plan_id, db=db, current_user=current_user, _=_)


@router.patch("/{plan_id}", status_code=status.HTTP_200_OK)
def edit_plan(
    plan_id: int,
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    body: dict[str, Any] = Body(...),
):
    """Manual plan edit. Supported operations in `body.moves`:
    ```json
    {
      "moves": [
        {"order_id": 123, "to_trip_id": 45, "sequence": 3}
      ]
    }
    ```
    Validates WEIGHT/VOLUME/TEMP constraints after each move."""
    return use_cases.edit_plan(plan_id=plan_id, db=db, current_user=current_user, _=_, body=body)


@router.post("/{plan_id}/publish", status_code=status.HTTP_200_OK)
def publish_plan(plan_id: int, db: DbDep, current_user: CurrentUser, _: None = _DISPATCHER):
    """Publish a DRAFT plan:
    1. Validates — rejects if any ERROR-severity constraint violations exist.
    2. Marks DRAFT → PUBLISHED, supersedes previous PUBLISHED plan.
    3. Advances order statuses: QUEUED/CONFIRMED → PLANNED.
    4. Sets Trip status to PLANNED (→ ready for loader to start LOADING).
    5. Broadcasts notifications to all loaders.
    6. Records audit log entry."""
    return use_cases.publish_plan(plan_id=plan_id, db=db, current_user=current_user, _=_)
