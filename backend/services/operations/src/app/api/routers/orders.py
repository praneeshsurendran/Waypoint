from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_contracts.runtime import (
    ClosureResult,
    IntakeStatus,
    OkResult,
    ReceiptResult,
    StatusResult,
)
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.order import IssueCreate, OrderCreate, OrderOut, OrderUpdate, ReceiptCreate
from waypoint_contracts.plan import StopOut
from app.application.use_cases import orders as use_cases

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    body: OrderCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, require_role("STORE_MANAGER", "DISPATCHER")],
) -> OrderOut:
    return TypeAdapter(OrderOut).validate_python(
        use_cases.create_order(body=body, db=db, current_user=current_user, _=None)
    )


@router.get("/stops", response_model=list[StopOut])
def list_order_stops(
    db: DbDep,
    current_user: CurrentUser,
    outlet_id: Optional[str] = Query(None),
    date: Optional[dt.date] = Query(None),
) -> list[StopOut]:
    """Returns delivery stops for the store manager's outlet (or scoped by query param for dispatchers)."""
    return TypeAdapter(list[StopOut]).validate_python(
        use_cases.list_order_stops(db=db, current_user=current_user, outlet_id=outlet_id, date=date)
    )


@router.get("/intake-status", response_model=IntakeStatus, response_model_exclude_unset=True)
def get_intake_status(db: DbDep, current_user: CurrentUser) -> IntakeStatus:
    """Return whether cutoff is passed and whether a plan has been published for tomorrow's delivery."""
    return TypeAdapter(IntakeStatus).validate_python(
        use_cases.get_intake_status(db=db, current_user=current_user)
    )


@router.post(
    "/close",
    status_code=status.HTTP_200_OK,
    response_model=ClosureResult,
    response_model_exclude_unset=True,
)
def close_intake(
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, require_role("DISPATCHER")],
    date: Optional[dt.date] = Query(None),
) -> ClosureResult:
    return TypeAdapter(ClosureResult).validate_python(
        use_cases.close_intake(db=db, current_user=current_user, _=None, date=date)
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: DbDep,
    current_user: CurrentUser,
    date: Optional[dt.date] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    outlet_id: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[OrderOut]:
    return TypeAdapter(list[OrderOut]).validate_python(
        use_cases.list_orders(
            db=db,
            current_user=current_user,
            date=date,
            status_filter=status_filter,
            outlet_id=outlet_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: DbDep, current_user: CurrentUser) -> OrderOut:
    return TypeAdapter(OrderOut).validate_python(
        use_cases.get_order(order_id=order_id, db=db, current_user=current_user)
    )


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    body: OrderUpdate,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, require_role("STORE_MANAGER", "DISPATCHER")],
) -> OrderOut:
    return TypeAdapter(OrderOut).validate_python(
        use_cases.update_order(
            order_id=order_id, body=body, db=db, current_user=current_user, _=None
        )
    )


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, require_role("STORE_MANAGER", "DISPATCHER")],
) -> OrderOut:
    return TypeAdapter(OrderOut).validate_python(
        use_cases.cancel_order(order_id=order_id, db=db, current_user=current_user, _=None)
    )


@router.post(
    "/{order_id}/confirm",
    status_code=status.HTTP_200_OK,
    response_model=StatusResult,
    response_model_exclude_unset=True,
)
def confirm_order(
    order_id: int,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, require_role("DISPATCHER")],
) -> StatusResult:
    return TypeAdapter(StatusResult).validate_python(
        use_cases.confirm_order(order_id=order_id, db=db, current_user=current_user, _=None)
    )


@router.post(
    "/{order_id}/receipt",
    status_code=status.HTTP_201_CREATED,
    response_model=ReceiptResult,
    response_model_exclude_unset=True,
)
def confirm_receipt(
    order_id: int,
    body: ReceiptCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, require_role("STORE_MANAGER")],
) -> ReceiptResult:
    return TypeAdapter(ReceiptResult).validate_python(
        use_cases.confirm_receipt(
            order_id=order_id, body=body, db=db, current_user=current_user, _=None
        )
    )


@router.post(
    "/{order_id}/issues",
    status_code=status.HTTP_201_CREATED,
    response_model=OkResult,
    response_model_exclude_unset=True,
)
def report_issue(
    order_id: int,
    body: IssueCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, require_role("STORE_MANAGER")],
) -> OkResult:
    return TypeAdapter(OkResult).validate_python(
        use_cases.report_issue(
            order_id=order_id, body=body, db=db, current_user=current_user, _=None
        )
    )
