from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_contracts.runtime import PlanValidation, PublishResult
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Body, Query, status
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.plan import PlanOut
from waypoint_contracts.runtime import PlanEdit
from app.application.use_cases import plans as use_cases

router = APIRouter(prefix="/plans", tags=["plans"])
_DISPATCHER = require_role("DISPATCHER")


@router.get("", response_model=list[PlanOut])
def list_plans(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    date: Optional[dt.date] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
) -> list[PlanOut]:
    return TypeAdapter(list[PlanOut]).validate_python(
        use_cases.list_plans(
            db=db, current_user=current_user, _=None, date=date, status_filter=status_filter
        )
    )


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: int, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> PlanOut:
    return TypeAdapter(PlanOut).validate_python(
        use_cases.get_plan(plan_id=plan_id, db=db, current_user=current_user, _=None)
    )


@router.post("/auto-plan", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def auto_plan(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    date: Optional[dt.date] = Query(None),
) -> PlanOut:
    return TypeAdapter(PlanOut).validate_python(
        use_cases.auto_plan(db=db, current_user=current_user, _=None, date=date)
    )


@router.post(
    "/{plan_id}/validate", response_model=PlanValidation, response_model_exclude_unset=True
)
def validate_plan_endpoint(
    plan_id: int, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> PlanValidation:
    """Run all constraint validators against the plan and return violations."""
    return TypeAdapter(PlanValidation).validate_python(
        use_cases.validate_plan_endpoint(plan_id=plan_id, db=db, current_user=current_user, _=None)
    )


@router.patch(
    "/{plan_id}",
    status_code=status.HTTP_200_OK,
    response_model=PlanOut,
    response_model_exclude_unset=True,
)
def edit_plan(
    plan_id: int,
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _DISPATCHER],
    body: PlanEdit = Body(...),
) -> PlanOut:
    """Manual plan edit. Supported operations in `body.moves`:
    ```json
    {
      "moves": [
        {"order_id": 123, "to_trip_id": 45, "sequence": 3}
      ]
    }
    ```
    Validates WEIGHT/VOLUME/TEMP constraints after each move."""
    return TypeAdapter(PlanOut).validate_python(
        use_cases.edit_plan(
            plan_id=plan_id,
            db=db,
            current_user=current_user,
            _=None,
            body=body.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/{plan_id}/publish",
    status_code=status.HTTP_200_OK,
    response_model=PublishResult,
    response_model_exclude_unset=True,
)
def publish_plan(
    plan_id: int, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> PublishResult:
    """Publish a DRAFT plan:
    1. Validates — rejects if any ERROR-severity constraint violations exist.
    2. Marks DRAFT → PUBLISHED, supersedes previous PUBLISHED plan.
    3. Advances order statuses: QUEUED/CONFIRMED → PLANNED.
    4. Sets Trip status to PLANNED (→ ready for loader to start LOADING).
    5. Broadcasts notifications to all loaders.
    6. Records audit log entry."""
    return TypeAdapter(PublishResult).validate_python(
        use_cases.publish_plan(plan_id=plan_id, db=db, current_user=current_user, _=None)
    )
