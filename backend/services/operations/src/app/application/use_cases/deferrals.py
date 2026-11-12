"""Deferrals router — dispatcher views and manages deferrals."""

from __future__ import annotations
import datetime as dt
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbDep
from waypoint_security import Principal as CurrentUser
from app.core import clock
from app.infrastructure.db.models.deferral import Deferral
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.plan import Plan
from app.infrastructure.db.models.reference import CalendarDay
from waypoint_contracts.order import DeferralCreate
from app.services.audit import log_action
from app.application.use_cases.plans import _detach_order_from_plan
from app.services.calendar import previous_operating_day
from app.services.state_machine import transition_order


_DISPATCHER = None


def create_deferral(
    body: DeferralCreate, db: DbDep, current_user: CurrentUser, _: None = _DISPATCHER
):
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Order not found."},
        )
    plan = (
        db.query(Plan)
        .filter(Plan.delivery_date == order.delivery_date, Plan.status.in_(["DRAFT", "PUBLISHED"]))
        .order_by(Plan.id.desc())
        .first()
    )
    if not plan:
        plan = Plan(delivery_date=order.delivery_date, status="DRAFT", created_by=current_user.id)
        db.add(plan)
        db.flush()
    _detach_order_from_plan(db, order.id, plan.id)
    previous_day = previous_operating_day(db, order.delivery_date)
    last_deferral = (
        db.query(Deferral)
        .join(Order, Deferral.order_id == Order.id)
        .filter(Order.outlet_id == order.outlet_id, Order.delivery_date == previous_day)
        .order_by(Deferral.decided_at.desc())
        .first()
        if previous_day
        else None
    )
    consec = last_deferral.consecutive_count + 1 if last_deferral else 1
    if consec >= 2 and (not body.is_override):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "CONSECUTIVE_DEFERRAL_LIMIT",
                "message": f"Outlet {order.outlet_id} cannot be deferred 2 consecutive operating days without override.",
            },
        )
    next_day_row = (
        db.query(CalendarDay)
        .filter(CalendarDay.date > order.delivery_date, CalendarDay.is_operating.is_(True))
        .order_by(CalendarDay.date.asc())
        .first()
    )
    next_date = next_day_row.date if next_day_row else order.delivery_date + dt.timedelta(days=1)
    deferral = Deferral(
        plan_id=plan.id,
        order_id=order.id,
        reason_code=body.reason_code,
        explanation=body.explanation or f"Deferred by dispatcher: {body.reason_code}",
        consecutive_count=consec,
        decided_by=str(current_user.id),
        decided_at=clock.now(),
        next_run_date=next_date,
        is_override=body.is_override,
    )
    db.add(deferral)
    transition_order(order, "DEFERRED")
    log_action(
        db,
        "DEFER_ORDER",
        "Order",
        order.id,
        actor_user_id=current_user.id,
        after={"reason_code": body.reason_code, "consecutive_count": consec},
    )
    db.commit()
    db.refresh(deferral)
    return deferral


def list_deferrals(
    db: DbDep,
    current_user: CurrentUser,
    _: None = _DISPATCHER,
    date: Optional[dt.date] = None,
):
    q = db.query(Deferral)
    if date:
        from app.infrastructure.db.models.plan import Plan

        q = q.join(Plan, Deferral.plan_id == Plan.id).filter(Plan.delivery_date == date)
    return q.order_by(Deferral.decided_at.desc()).all()


def outlet_deferral_history(
    outlet_id: str, db: DbDep, current_user: CurrentUser, _: None = _DISPATCHER
):
    """Returns the deferral history for a specific outlet (via its orders)."""
    return (
        db.query(Deferral)
        .join(Order, Deferral.order_id == Order.id)
        .filter(Order.outlet_id == outlet_id)
        .order_by(Deferral.decided_at.desc())
        .all()
    )
