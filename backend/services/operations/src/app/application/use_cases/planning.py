from __future__ import annotations
import logging
from fastapi import HTTPException, status
from app.core import clock
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.plan import Plan
from app.services.audit import log_action
from app.services.state_machine import transition_order

log = logging.getLogger("waypoint.planning")


def run(db, current_user, date=None, strategy=None):
    """
    Run the greedy bin-packing allocation algorithm for `date` (default: tomorrow).
    Creates a DRAFT plan. Supersedes any previous DRAFT for the same date.
    """
    from app.domain.planning.allocate import allocate
    from app.infrastructure.db.planning import build_context, persist_plan
    from app.domain.planning.validate import validate_plan
    from app.infrastructure.db.models.reference import CalendarDay

    delivery_date = date or clock.delivery_date()
    from app.application.use_cases.locking import lock_run

    lock_run(db, delivery_date)

    # Validate the date is an operating day
    cal = db.get(CalendarDay, delivery_date)
    if cal and not cal.is_operating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NOT_OPERATING",
                "message": f"{delivery_date} is not an operating day.",
            },
        )

    # Check there are orders to plan; auto-confirm any PLACED orders first
    placed_orders = (
        db.query(Order).filter(Order.delivery_date == delivery_date, Order.status == "PLACED").all()
    )
    for po in placed_orders:
        transition_order(po, "CONFIRMED")
        transition_order(po, "QUEUED")
    if placed_orders:
        db.flush()

    orders_count = (
        db.query(Order)
        .filter(
            Order.delivery_date == delivery_date,
            Order.status.in_(["QUEUED", "CONFIRMED"]),
        )
        .count()
    )
    if orders_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_ORDERS",
                "message": f"No QUEUED/CONFIRMED orders for {delivery_date}.",
            },
        )

    log.info("auto-plan: building context for %s (%d orders)", delivery_date, orders_count)

    ctx = build_context(db, delivery_date)
    planner_plan = strategy.allocate(ctx) if strategy is not None else allocate(ctx)

    # Supersede any previous DRAFT for the same date
    existing_drafts = (
        db.query(Plan).filter(Plan.delivery_date == delivery_date, Plan.status == "DRAFT").all()
    )
    for draft in existing_drafts:
        draft.status = "SUPERSEDED"

    plan = persist_plan(db, planner_plan, created_by=current_user.id)

    # Compute summary
    n_trips = len(planner_plan.trips)
    n_orders = sum(len(s.order_ids) for t in planner_plan.trips for s in t.stops)
    n_deferred = len(planner_plan.deferrals)
    plan.summary_json = {
        "trips": n_trips,
        "orders_planned": n_orders,
        "orders_deferred": n_deferred,
        "total_km": round(sum(t.planned_distance for t in planner_plan.trips), 1),
        "total_fuel_l": round(sum(t.planned_fuel for t in planner_plan.trips), 1),
    }

    log.info(
        "auto-plan: %d trips, %d orders planned, %d deferred",
        n_trips,
        n_orders,
        n_deferred,
    )

    violations = validate_plan(planner_plan, ctx)
    errors = [v for v in violations if v.severity == "ERROR"]
    if errors:
        log.warning("auto-plan: %d constraint violations", len(errors))
        raise HTTPException(
            422,
            detail={
                "code": "CONSTRAINT_VIOLATIONS",
                "message": "Planner produced an invalid result.",
            },
        )

    log_action(
        db, "AUTO_PLAN", "Plan", plan.id, actor_user_id=current_user.id, after=plan.summary_json
    )
    db.flush()
    return plan
