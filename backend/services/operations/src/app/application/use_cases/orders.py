"""Orders router — store managers place orders; dispatchers manage them."""

from __future__ import annotations
import datetime as dt
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm import Session as DbDep
from waypoint_security import Principal as CurrentUser
from app.core import clock
from app.infrastructure.db.models.audit import AuditLog
from app.infrastructure.db.models.deferral import Deferral
from app.infrastructure.db.models.issue import Issue
from app.infrastructure.db.models.order import Order, OrderLine
from app.infrastructure.db.models.plan import Plan, Stop, StopOrder, Trip
from app.infrastructure.db.models.receipt import Receipt
from app.infrastructure.db.models.reference import CalendarDay, Outlet
from waypoint_contracts.order import IssueCreate, OrderCreate, OrderUpdate, ReceiptCreate
from app.services.audit import log_action
from app.services.calendar import previous_operating_day
from app.services.order_sizing import MAX_UNITS, TECH_ITEM_KG, estimate_load
from app.services.state_machine import transition_order


def _generate_reference(db: Session, delivery_date: dt.date) -> str:
    count = (
        db.query(func.count(Order.id)).filter(Order.delivery_date == delivery_date).scalar() or 0
    )
    return f"ORD-{delivery_date.strftime('%Y%m%d')}-{count + 1:04d}"


def _intake_closed(db: Session, delivery_date: dt.date) -> bool:
    """True once orders for `delivery_date` can no longer join its plan."""
    from app.infrastructure.messaging.models import IntakeClosure

    if db.get(IntakeClosure, delivery_date):
        return True
    published_plan = (
        db.query(Plan)
        .filter(Plan.delivery_date == delivery_date, Plan.status == "PUBLISHED")
        .first()
    )
    unclosed_count = (
        db.query(Order)
        .filter(Order.delivery_date == delivery_date, Order.status.in_(["PLACED", "CONFIRMED"]))
        .count()
    )
    total_count = db.query(Order).filter(Order.delivery_date == delivery_date).count()
    intake_closed_log = any(
        (
            (log.after_json or {}).get("delivery_date") == str(delivery_date)
            for log in db.query(AuditLog).filter(
                AuditLog.action == "CLOSE_INTAKE", AuditLog.entity_type == "Intake"
            )
        )
    )
    return (
        clock.is_past_cutoff()
        or intake_closed_log
        or (total_count > 0 and unclosed_count == 0)
        or (published_plan is not None)
    )


def _next_operating_day(db, after):
    from app.services.calendar import next_operating_day

    return next_operating_day(db, after)


def _order_day(db: Session) -> dt.date:
    """The day an order placed now is delivered. After the cutoff it waits for the following run."""
    planning_day = clock.delivery_date()
    row = db.get(CalendarDay, planning_day)
    if row is not None and not row.is_operating:
        planning_day = _next_operating_day(db, planning_day)
    return (
        _next_operating_day(db, planning_day) if _intake_closed(db, planning_day) else planning_day
    )


def _annotate_departures(db: Session, orders: list[Order]) -> list[Order]:
    """Attach `departed_at`: when the trip carrying each order left, from the trip-start audit entry."""
    trip_of: dict[int, str] = {}
    for order in orders:
        for so in order.stop_orders or []:
            if so.stop_rel and so.stop_rel.trip_rel:
                trip_of[order.id] = str(so.stop_rel.trip_rel.id)
                break
    if trip_of:
        left = dict(
            db.query(AuditLog.entity_id, func.min(AuditLog.created_at))
            .filter(
                AuditLog.action == "START_TRIP",
                AuditLog.entity_type == "Trip",
                AuditLog.entity_id.in_(set(trip_of.values())),
            )
            .group_by(AuditLog.entity_id)
            .all()
        )
        for order in orders:
            order.departed_at = left.get(trip_of.get(order.id, ""))
    return orders


def _check_quantity(
    brand: str, units: int, temperature_class: str, weight: Optional[float] = None
) -> None:
    """Reject orders the business cannot have: bad counts, chilled goods outside Fresh, odd Tech weights."""
    if temperature_class not in ("CHILLED", "AMBIENT"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_TEMPERATURE",
                "message": "Temperature must be CHILLED or AMBIENT.",
            },
        )
    if temperature_class == "CHILLED" and brand != "Fresh":
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_TEMPERATURE", "message": "Only Fresh orders can be chilled."},
        )
    most = MAX_UNITS.get(brand, MAX_UNITS["Fresh"])
    if units < 1 or units > most:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUANTITY", "message": f"An order has 1 to {most} units."},
        )
    if weight is not None and brand == "Tech":
        low, high = (TECH_ITEM_KG[0] * units, TECH_ITEM_KG[1] * units)
        if not low <= weight <= high:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_WEIGHT",
                    "message": f"{units} Tech item(s) weigh between {low:g} and {high:g} kg.",
                },
            )


def create_order(
    body: OrderCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: None = None,
):
    if current_user.role == "STORE_MANAGER" and body.outlet_id != current_user.outlet_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "You can only place orders for your own outlet.",
            },
        )
    from app.application.use_cases.locking import lock_run
    from app.infrastructure.messaging.models import IntakeClosure

    outlet = db.query(Outlet).filter(Outlet.outlet_id == body.outlet_id).first()
    if outlet is None:
        raise HTTPException(404, detail={"code": "UNKNOWN_OUTLET", "message": "Outlet not found."})
    if body.brand and body.brand != outlet.brand:
        raise HTTPException(
            422, detail={"code": "INVALID_BRAND", "message": "Order brand must match its outlet."}
        )
    brand = body.brand or (outlet.brand if outlet else "Fresh")
    delivery_date = body.delivery_date or _order_day(db)
    lock_run(db, delivery_date)
    earliest = _order_day(db)
    if delivery_date < earliest or db.get(IntakeClosure, delivery_date):
        raise HTTPException(
            409,
            detail={
                "code": "INTAKE_CLOSED",
                "message": "This delivery run is closed; select the next operating day.",
            },
        )
    calendar = db.get(CalendarDay, delivery_date)
    if (
        calendar
        and (not calendar.is_operating)
        or (calendar is None and delivery_date.weekday() == 6)
    ):
        raise HTTPException(
            422, detail={"code": "NOT_OPERATING", "message": "Select an operating delivery day."}
        )
    total_cases = body.total_cases if body.total_cases > 0 else body.cases or 0
    stated_weight = body.total_weight if (body.total_weight or 0) > 0 else None
    _check_quantity(brand, total_cases, body.temperature_class, stated_weight)
    if brand in ("Fresh", "Style"):
        same_kind = [Order.temperature_class == body.temperature_class] if brand == "Fresh" else []
        existing = (
            db.query(Order)
            .filter(
                Order.outlet_id == body.outlet_id,
                Order.delivery_date == delivery_date,
                Order.brand == brand,
                Order.status != "CANCELLED",
                *same_kind,
            )
            .first()
        )
        if existing:
            kind = (
                "Style"
                if brand == "Style"
                else "chilled"
                if body.temperature_class == "CHILLED"
                else "dry"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_ORDER",
                    "message": f"A {kind} order already exists for {delivery_date:%d %B}; edit it instead.",
                    "order_id": existing.id,
                },
            )
    total_weight, total_volume = estimate_load(brand, total_cases)
    if brand == "Tech" and stated_weight is not None:
        total_weight = stated_weight
    if current_user.role == "DISPATCHER":
        if body.total_weight is not None and body.total_weight > 0:
            total_weight = body.total_weight
        if body.total_volume is not None and body.total_volume > 0:
            total_volume = body.total_volume
    past_cutoff = clock.is_past_cutoff() or delivery_date != clock.delivery_date()
    skipped_yesterday = (
        db.query(Deferral)
        .join(Order, Deferral.order_id == Order.id)
        .filter(
            Order.outlet_id == body.outlet_id,
            Order.delivery_date == previous_operating_day(db, delivery_date),
        )
        .first()
        is not None
    )
    order = Order(
        reference=_generate_reference(db, delivery_date),
        outlet_id=body.outlet_id,
        brand=brand,
        temperature_class=body.temperature_class,
        delivery_date=delivery_date,
        status="PLACED",
        total_weight=total_weight,
        total_volume=total_volume,
        total_cases=total_cases,
        priority=body.priority or skipped_yesterday,
        placed_at=clock.now(),
        cutoff_missed=past_cutoff,
        placed_by_user_id=current_user.id,
        notes=body.notes,
    )
    db.add(order)
    db.flush()
    for line in body.lines:
        db.add(OrderLine(order_id=order.id, **line.model_dump()))
    log_action(
        db,
        "CREATE_ORDER",
        "Order",
        order.id,
        actor_user_id=current_user.id,
        after={"reference": order.reference, "status": order.status},
    )
    db.commit()
    db.refresh(order)
    return order


def list_order_stops(
    db: DbDep,
    current_user: CurrentUser,
    outlet_id: Optional[str] = None,
    date: Optional[dt.date] = None,
):
    """Returns delivery stops for the store manager's outlet (or scoped by query param for dispatchers)."""
    target_outlet = (
        current_user.outlet_id
        if current_user.role == "STORE_MANAGER"
        else outlet_id or current_user.outlet_id
    )
    target_date = date or clock.delivery_date()
    q = (
        db.query(Stop)
        .join(Trip, Stop.trip_id == Trip.id)
        .join(Plan, Trip.plan_id == Plan.id)
        .options(
            selectinload(Stop.outlet_rel),
            selectinload(Stop.trip_rel),
            selectinload(Stop.delivery_events),
            selectinload(Stop.stop_orders).selectinload(StopOrder.order_rel),
        )
    )
    if current_user.role == "DRIVER":
        if not current_user.vehicle_id:
            return []
        q = q.filter(Trip.vehicle_id == current_user.vehicle_id, Plan.status == "PUBLISHED")
    if current_user.role == "LOADER":
        if not current_user.depot_id:
            return []
        from app.infrastructure.db.models.reference import Vehicle

        q = q.join(Vehicle, Trip.vehicle_id == Vehicle.vehicle_id).filter(
            Vehicle.depot_code == current_user.depot_id
        )
    store_view = current_user.role == "STORE_MANAGER"
    if store_view:
        q = q.filter(Plan.status == "PUBLISHED")
    if target_outlet:
        q = q.filter(Stop.outlet_id == target_outlet)
    if target_date:
        q = q.filter(Plan.delivery_date == target_date)
    stops = q.order_by(Stop.id.desc()).all()
    if (
        not stops
        and target_outlet
        and current_user.role in ("STORE_MANAGER", "DISPATCHER", "ADMIN")
    ):
        earlier = (
            db.query(Stop)
            .join(Trip, Stop.trip_id == Trip.id)
            .join(Plan, Trip.plan_id == Plan.id)
            .options(
                selectinload(Stop.outlet_rel),
                selectinload(Stop.trip_rel),
                selectinload(Stop.delivery_events),
                selectinload(Stop.stop_orders).selectinload(StopOrder.order_rel),
            )
            .filter(Stop.outlet_id == target_outlet)
        )
        if store_view:
            earlier = earlier.filter(Plan.status == "PUBLISHED")
        stops = earlier.order_by(Stop.id.desc()).limit(10).all()
    return stops


def get_intake_status(db: DbDep, current_user: CurrentUser):
    """Return whether cutoff is passed and whether a plan has been published for tomorrow's delivery."""
    delivery_date = clock.delivery_date()
    published_plan = (
        db.query(Plan)
        .filter(Plan.delivery_date == delivery_date, Plan.status == "PUBLISHED")
        .first()
    )
    return {
        "cutoff_closed": _intake_closed(db, delivery_date),
        "published": published_plan is not None,
        "delivery_date": str(delivery_date),
        "next_delivery_date": str(_order_day(db)),
        "now": clock.now().isoformat(),
    }


def close_intake(
    db: DbDep,
    current_user: CurrentUser,
    _: None = None,
    date: Optional[dt.date] = None,
    commit=True,
):
    target_date = date or clock.delivery_date()
    from app.application.use_cases.locking import lock_run
    from app.infrastructure.messaging.models import IntakeClosure
    from app.infrastructure.messaging.outbox import enqueue

    lock_run(db, target_date)
    existing = db.get(IntakeClosure, target_date)
    if existing:
        return {"closed": 0, "delivery_date": str(target_date)}
    orders = (
        db.query(Order)
        .filter(Order.delivery_date == target_date, Order.status.in_(["PLACED", "CONFIRMED"]))
        .all()
    )
    for order in orders:
        before = {"status": order.status}
        if order.status == "PLACED":
            transition_order(order, "CONFIRMED")
        transition_order(order, "QUEUED")
        log_action(
            db,
            "CLOSE_INTAKE",
            "Order",
            order.id,
            actor_user_id=current_user.id,
            before=before,
            after={"status": order.status},
        )
    snapshot = [
        {
            "id": o.id,
            "reference": o.reference,
            "outlet_id": o.outlet_id,
            "weight": o.total_weight,
            "volume": o.total_volume,
            "cases": o.total_cases,
        }
        for o in orders
    ]
    db.add(
        IntakeClosure(delivery_date=target_date, order_snapshot=snapshot, closed_by=current_user.id)
    )
    enqueue(
        db,
        "orders.closed",
        str(target_date),
        {"delivery_date": str(target_date), "orders": snapshot, "actor_user_id": current_user.id},
    )
    log_action(
        db,
        "CLOSE_INTAKE",
        "Intake",
        0,
        actor_user_id=current_user.id,
        after={"closed": len(orders), "delivery_date": str(target_date)},
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return {"closed": len(orders), "delivery_date": str(target_date)}


def list_orders(
    db: DbDep,
    current_user: CurrentUser,
    date: Optional[dt.date] = None,
    status_filter: Optional[str] = None,
    outlet_id: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
):
    q = db.query(Order).options(
        selectinload(Order.lines),
        selectinload(Order.outlet_rel),
        selectinload(Order.receipts),
        selectinload(Order.issues),
        selectinload(Order.delivery_events),
        selectinload(Order.stop_orders)
        .selectinload(StopOrder.stop_rel)
        .selectinload(Stop.trip_rel)
        .selectinload(Trip.plan_rel),
    )
    from app.application.use_cases.authorization import scope_orders

    q = scope_orders(q, db, current_user)
    if current_user.role == "STORE_MANAGER":
        q = q.filter(Order.outlet_id == current_user.outlet_id)
    elif outlet_id:
        q = q.filter(Order.outlet_id == outlet_id)
    if date:
        q = q.filter(Order.delivery_date == date)
    if status_filter:
        q = q.filter(Order.status == status_filter)
    return _annotate_departures(
        db, q.order_by(Order.placed_at.desc(), Order.id.desc()).offset(offset).limit(limit).all()
    )


def get_order(order_id: int, db: DbDep, current_user: CurrentUser):
    order = db.get(
        Order,
        order_id,
        options=[
            selectinload(Order.lines),
            selectinload(Order.outlet_rel),
            selectinload(Order.receipts),
            selectinload(Order.issues),
            selectinload(Order.delivery_events),
            selectinload(Order.stop_orders)
            .selectinload(StopOrder.stop_rel)
            .selectinload(Stop.trip_rel)
            .selectinload(Trip.plan_rel),
        ],
    )
    if not order:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found."}
        )
    if current_user.role == "STORE_MANAGER" and order.outlet_id != current_user.outlet_id:
        raise HTTPException(
            status_code=403, detail={"code": "FORBIDDEN", "message": "Not your outlet."}
        )
    from app.application.use_cases.authorization import require_order

    require_order(db, order, current_user)
    _annotate_departures(db, [order])
    return order


def update_order(
    order_id: int,
    body: OrderUpdate,
    db: DbDep,
    current_user: CurrentUser,
    _: None = None,
):
    order = db.get(
        Order,
        order_id,
        options=[
            selectinload(Order.lines),
            selectinload(Order.outlet_rel),
            selectinload(Order.receipts),
            selectinload(Order.issues),
            selectinload(Order.delivery_events),
            selectinload(Order.stop_orders)
            .selectinload(StopOrder.stop_rel)
            .selectinload(Stop.trip_rel)
            .selectinload(Trip.plan_rel),
        ],
    )
    if not order:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found."}
        )
    if current_user.role == "STORE_MANAGER":
        if order.outlet_id != current_user.outlet_id:
            raise HTTPException(
                status_code=403, detail={"code": "FORBIDDEN", "message": "Not your outlet."}
            )
        if order.status not in ("PLACED", "CONFIRMED", "QUEUED", "PLANNED"):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_STATE",
                    "message": f"Cannot modify order in {order.status} state.",
                },
            )
        published = (
            db.query(Plan)
            .filter(Plan.delivery_date == order.delivery_date, Plan.status == "PUBLISHED")
            .first()
        )
        if published and order.status in ("PLANNED", "LOADED", "IN_TRANSIT", "DELIVERED"):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "PLAN_PUBLISHED",
                    "message": "Cannot modify order once plan is published.",
                },
            )
    from app.application.use_cases.locking import lock_run
    from app.infrastructure.messaging.models import IntakeClosure

    lock_run(db, order.delivery_date)
    if current_user.role == "STORE_MANAGER" and db.get(IntakeClosure, order.delivery_date):
        raise HTTPException(
            409,
            detail={
                "code": "INTAKE_CLOSED",
                "message": "Orders cannot be changed after run closure.",
            },
        )
    before = {
        "total_cases": order.total_cases,
        "total_weight": order.total_weight,
        "total_volume": order.total_volume,
    }
    new_cases = body.cases if body.cases is not None else body.total_cases
    if new_cases is not None:
        stated = body.total_weight if (body.total_weight or 0) > 0 else None
        _check_quantity(order.brand, new_cases, order.temperature_class, stated)
        order.total_cases = new_cases
        order.total_weight, order.total_volume = estimate_load(order.brand, new_cases)
        if order.brand == "Tech" and stated is not None:
            order.total_weight = stated
        if current_user.role == "DISPATCHER":
            if body.total_weight is not None and body.total_weight > 0:
                order.total_weight = body.total_weight
            if body.total_volume is not None and body.total_volume > 0:
                order.total_volume = body.total_volume
    if body.notes is not None:
        order.notes = body.notes
    log_action(
        db,
        "UPDATE_ORDER",
        "Order",
        order.id,
        actor_user_id=current_user.id,
        before=before,
        after={"total_cases": order.total_cases, "total_weight": order.total_weight},
    )
    db.commit()
    db.refresh(order)
    return order


def cancel_order(
    order_id: int,
    db: DbDep,
    current_user: CurrentUser,
    _: None = None,
):
    order = db.get(
        Order,
        order_id,
        options=[
            selectinload(Order.lines),
            selectinload(Order.outlet_rel),
            selectinload(Order.receipts),
            selectinload(Order.issues),
            selectinload(Order.delivery_events),
            selectinload(Order.stop_orders)
            .selectinload(StopOrder.stop_rel)
            .selectinload(Stop.trip_rel)
            .selectinload(Trip.plan_rel),
        ],
    )
    if not order:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found."}
        )
    if current_user.role == "STORE_MANAGER":
        if order.outlet_id != current_user.outlet_id:
            raise HTTPException(
                status_code=403, detail={"code": "FORBIDDEN", "message": "Not your outlet."}
            )
        if order.status in ("LOADED", "IN_TRANSIT", "DELIVERED", "PARTIAL", "FAILED", "CANCELLED"):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_STATE",
                    "message": f"Cannot cancel order in {order.status} state.",
                },
            )
    before = {"status": order.status}
    transition_order(order, "CANCELLED")
    db.query(StopOrder).filter(StopOrder.order_id == order.id).delete()
    log_action(
        db,
        "CANCEL_ORDER",
        "Order",
        order.id,
        actor_user_id=current_user.id,
        before=before,
        after={"status": order.status},
    )
    db.commit()
    db.refresh(order)
    return order


def confirm_order(order_id: int, db: DbDep, current_user: CurrentUser, _: None = None):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found."}
        )
    before = {"status": order.status}
    transition_order(order, "CONFIRMED")
    log_action(
        db,
        "CONFIRM_ORDER",
        "Order",
        order.id,
        actor_user_id=current_user.id,
        before=before,
        after={"status": order.status},
    )
    db.commit()
    return {"ok": True, "status": order.status}


def confirm_receipt(
    order_id: int,
    body: ReceiptCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: None = None,
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found."}
        )
    if order.outlet_id != current_user.outlet_id:
        raise HTTPException(
            status_code=403, detail={"code": "FORBIDDEN", "message": "Not your outlet."}
        )
    if order.status not in ("LOADED", "IN_TRANSIT", "DELIVERED", "PARTIAL"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_STATE",
                "message": "Receipt can be confirmed once the order has been delivered.",
            },
        )
    outcome = (body.outcome or "").upper()
    receipt_status = body.status
    if outcome == "FULL":
        receipt_status = "FULL"
    elif outcome == "SHORT":
        receipt_status = "PARTIAL"
    elif outcome == "DAMAGED":
        receipt_status = "DISPUTED"
    elif not receipt_status:
        receipt_status = "FULL"
    import hashlib
    import json
    from app.application.use_cases.locking import lock_run

    lock_run(db, order.delivery_date)
    request_data = {
        "actor": current_user.id,
        "order_id": order.id,
        "status": receipt_status,
        "received": body.received_qty,
        "affected": body.affected_qty,
        "notes": body.notes,
    }
    command_key = hashlib.sha256(json.dumps(request_data, sort_keys=True).encode()).hexdigest()
    existing_receipt = (
        db.query(Receipt)
        .filter(Receipt.order_id == order.id, Receipt.command_key == command_key)
        .first()
    )
    if existing_receipt:
        return {"ok": True, "receipt_status": existing_receipt.status, "idempotent": True}
    received = body.received_qty if body.received_qty is not None else order.total_cases
    affected = body.affected_qty or 0
    if not 0 <= received <= order.total_cases or not 0 <= affected <= order.total_cases:
        raise HTTPException(
            422,
            detail={
                "code": "INVALID_RECEIPT_QUANTITY",
                "message": "Receipt quantities must be within the ordered quantity.",
            },
        )
    if outcome == "SHORT" and received + affected != order.total_cases:
        raise HTTPException(
            422,
            detail={
                "code": "INVALID_RECEIPT_QUANTITY",
                "message": "Received and missing quantities must sum to the order.",
            },
        )
    if outcome == "DAMAGED" and affected > received:
        raise HTTPException(
            422,
            detail={
                "code": "INVALID_RECEIPT_QUANTITY",
                "message": "Damaged quantity cannot exceed received quantity.",
            },
        )
    receipt = Receipt(
        order_id=order.id,
        confirmed_by=current_user.id,
        status=receipt_status,
        command_key=command_key,
    )
    db.add(receipt)
    if outcome in ("SHORT", "DAMAGED") or receipt_status in ("PARTIAL", "DISPUTED"):
        import json

        issue_type = "SHORT" if outcome == "SHORT" or receipt_status == "PARTIAL" else "DAMAGED"
        desc_json = json.dumps(
            {
                "received": body.received_qty
                if body.received_qty is not None
                else order.total_cases,
                "affected": body.affected_qty or 0,
                "notes": body.notes or "",
            }
        )
        issue = Issue(
            order_id=order.id, reported_by=current_user.id, type=issue_type, description=desc_json
        )
        db.add(issue)
    if receipt_status == "PARTIAL":
        if order.status in ("LOADED", "IN_TRANSIT", "DELIVERED"):
            order.status = "PARTIAL"
    elif receipt_status == "FULL":
        if order.status in ("LOADED", "IN_TRANSIT"):
            order.status = "DELIVERED"
    log_action(
        db,
        "CONFIRM_RECEIPT",
        "Order",
        order.id,
        actor_user_id=current_user.id,
        after={"receipt_status": receipt_status, "outcome": outcome},
    )
    db.commit()
    return {"ok": True, "receipt_status": receipt_status}


def report_issue(
    order_id: int,
    body: IssueCreate,
    db: DbDep,
    current_user: CurrentUser,
    _: None = None,
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "Order not found."}
        )
    if order.outlet_id != current_user.outlet_id:
        raise HTTPException(
            status_code=403, detail={"code": "FORBIDDEN", "message": "Not your outlet."}
        )
    issue = Issue(
        order_id=order.id, reported_by=current_user.id, type=body.type, description=body.description
    )
    db.add(issue)
    log_action(
        db,
        "REPORT_ISSUE",
        "Order",
        order.id,
        actor_user_id=current_user.id,
        after={"type": body.type},
    )
    db.commit()
    return {"ok": True}
