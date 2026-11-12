from fastapi import HTTPException
from sqlalchemy import select
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.plan import Stop, StopOrder, Trip, Plan
from app.infrastructure.db.models.reference import Outlet


def scope_orders(query, db, user):
    if user.role == "STORE_MANAGER":
        return (
            query.filter(Order.outlet_id == user.outlet_id)
            if user.outlet_id
            else query.filter(False)
        )
    if user.role == "DRIVER":
        if not user.vehicle_id:
            return query.filter(False)
        ids = (
            select(StopOrder.order_id)
            .join(Stop, Stop.id == StopOrder.stop_id)
            .join(Trip, Trip.id == Stop.trip_id)
            .join(Plan, Plan.id == Trip.plan_id)
            .where(Trip.vehicle_id == user.vehicle_id, Plan.status == "PUBLISHED")
        )
        return query.filter(Order.id.in_(ids))
    if user.role == "LOADER" or (user.role == "DISPATCHER" and user.depot_id):
        if not user.depot_id:
            return query.filter(False)
        return query.filter(
            Order.outlet_id.in_(select(Outlet.outlet_id).where(Outlet.depot_code == user.depot_id))
        )
    return query


def require_order(db, order, user):
    if scope_orders(db.query(Order), db, user).filter(Order.id == order.id).first() is None:
        raise HTTPException(
            403, detail={"code": "FORBIDDEN", "message": "Order is outside your assignment."}
        )
