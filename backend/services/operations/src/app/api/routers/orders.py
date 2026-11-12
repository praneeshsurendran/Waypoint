from __future__ import annotations
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
    _: None = require_role("STORE_MANAGER", "DISPATCHER"),
):
    return use_cases.create_order(body=body, db=db, current_user=current_user, _=_)


@router.get("/stops", response_model=list[StopOut])
def list_order_stops(
    db: DbDep,
    current_user: CurrentUser,
    outlet_id: Optional[str] = Query(None),
    date: Optional[dt.date] = Query(None),
):
    """Returns delivery stops for the store manager's outlet (or scoped by query param for dispatchers)."""
    return use_cases.list_order_stops(
        db=db, current_user=current_user, outlet_id=outlet_id, date=date
    )


@router.get("/intake-status")
def get_intake_status(db: DbDep, current_user: CurrentUser):
    """Return whether cutoff is passed and whether a plan has been published for tomorrow's delivery."""
    return use_cases.get_intake_status(db=db, current_user=current_user)


@router.post("/close", status_code=status.HTTP_200_OK)
def close_intake(
    db: DbDep,
    current_user: CurrentUser,
    _: None = require_role("DISPATCHER"),
    date: Optional[dt.date] = Query(None),
):
    return use_cases.close_intake(db=db, current_user=current_user, _=_, date=date)


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: DbDep,
    current_user: CurrentUser,
    date: Optional[dt.date] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    outlet_id: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    return use_cases.list_orders(
        db=db,
        current_user=current_user,
        date=date,
        status_filter=status_filter,
        outlet_id=outlet_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: DbDep, current_user: CurrentUser):
    return use_cases.get_order(order_id=order_id, db=db, current_user=current_user)


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    body: OrderUpdate,
    db: DbDep,
    current_user: CurrentUser,
    _: None = require_role("STORE_MANAGER", "DISPATCHER"),
):
    return use_cases.update_order(
        order_id=order_id, body=body, db=db, current_user=current_user, _=_
    )


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    db: DbDep,
    current_user: CurrentUser,
    _: None = require_role("STORE_MANAGER", "DISPATCHER"),
):
    return use_cases.cancel_order(order_id=order_id, db=db, current_user=current_user, _=_)


@router.post("/{order_id}/confirm", status_code=status.HTTP_200_OK)
def confirm_order(
    order_id: int, db: DbDep, current_user: CurrentUser, _: None = require_role("DISPATCHER")
):
    return use_cases.confirm_order(order_id=order_id, db=db, current_user=current_user, _=_)


@router.post("/{order_id}/receipt", status_code=status.HTTP_201_CREATED)
def confirm_receipt(
    order_id: int,
    body: ReceiptCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: None = require_role("STORE_MANAGER"),
):
    return use_cases.confirm_receipt(
        order_id=order_id, body=body, db=db, current_user=current_user, _=_
    )


@router.post("/{order_id}/issues", status_code=status.HTTP_201_CREATED)
def report_issue(
    order_id: int,
    body: IssueCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: None = require_role("STORE_MANAGER"),
):
    return use_cases.report_issue(
        order_id=order_id, body=body, db=db, current_user=current_user, _=_
    )
