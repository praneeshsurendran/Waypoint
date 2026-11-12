"""Driver router — current trip, stop events, offline sync, photo upload."""

from __future__ import annotations
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.infrastructure.db.models.position import VehiclePosition
from waypoint_contracts.position import PositionIn
from sqlalchemy.orm import Session as DbDep
from waypoint_security import Principal as CurrentUser
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.plan import Stop, StopOrder, Trip
from waypoint_contracts.plan import DeliveryEventIn, DeliveryEventResult, SyncBatch
from app.services.audit import log_action
from app.services.state_machine import transition_order, transition_trip


_DRIVER = None
_UPLOAD_ROLES = None


def current_trip(db: DbDep, current_user: CurrentUser, _: None = _DRIVER):
    """Return the driver's active trip (LOADING, LOADED, or IN_TRANSIT)."""
    q = (
        db.query(Trip)
        .options(
            selectinload(Trip.stops).selectinload(Stop.outlet_rel),
            selectinload(Trip.stops)
            .selectinload(Stop.stop_orders)
            .selectinload(StopOrder.order_rel),
            selectinload(Trip.stops).selectinload(Stop.delivery_events),
            selectinload(Trip.load_checks),
        )
        .filter(Trip.status.in_(["LOADING", "LOADED", "IN_TRANSIT"]))
    )
    if current_user.role == "DRIVER" and (not current_user.vehicle_id):
        return None
    if current_user.vehicle_id:
        q = q.filter(Trip.vehicle_id == current_user.vehicle_id)
    trip = q.order_by(Trip.planned_depart).first()
    return trip


def _orders_in_transit(db: DbDep, trip: Trip, user_id: Optional[int] = None) -> None:
    """Orders on a trip that has left the depot are in transit, so stores can see them en route."""
    log_action(
        db,
        "START_TRIP",
        "Trip",
        trip.id,
        actor_user_id=user_id,
        before={"status": "LOADED"},
        after={"status": "IN_TRANSIT"},
    )
    stop_ids = [stop.id for stop in trip.stops]
    if not stop_ids:
        return
    for link in db.query(StopOrder).filter(StopOrder.stop_id.in_(stop_ids)).all():
        order = db.get(Order, link.order_id)
        if order and order.status == "LOADED":
            transition_order(order, "IN_TRANSIT")


def start_driver_trip(db: DbDep, current_user: CurrentUser, _: None = _DRIVER):
    """Mark the driver's current trip as IN_TRANSIT (LOADED -> IN_TRANSIT)."""
    q = db.query(Trip).options(selectinload(Trip.stops)).filter(Trip.status == "LOADED")
    if current_user.vehicle_id:
        q = q.filter(Trip.vehicle_id == current_user.vehicle_id)
    if current_user.role == "DRIVER" and (not current_user.vehicle_id):
        raise HTTPException(
            403, detail={"code": "FORBIDDEN", "message": "Vehicle assignment required."}
        )
    trip = q.with_for_update().first()
    if not trip:
        trip_in_transit = db.query(Trip).filter(Trip.status == "IN_TRANSIT")
        if current_user.vehicle_id:
            trip_in_transit = trip_in_transit.filter(Trip.vehicle_id == current_user.vehicle_id)
        if trip_in_transit.first():
            return {"ok": True, "status": "IN_TRANSIT"}
        raise HTTPException(
            status_code=400,
            detail={"code": "NO_LOADED_TRIP", "message": "No loaded trip ready for departure."},
        )
    transition_trip(trip, "IN_TRANSIT")
    _orders_in_transit(db, trip, current_user.id)
    db.commit()
    return {"ok": True, "status": trip.status}


def record_stop_event(
    stop_id: int, body: DeliveryEventIn, db: DbDep, current_user: CurrentUser, _: None = _DRIVER
):
    from app.application.use_cases.delivery import apply_event

    stop = db.get(Stop, stop_id)
    if stop is None:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Stop not found."})
    result = apply_event(db, stop, body, current_user)
    db.commit()
    return result


def sync_events(body: SyncBatch, db: DbDep, current_user: CurrentUser, _: None = _DRIVER):
    from app.application.use_cases.delivery import apply_event

    results = []
    for item in body.events:
        try:
            with db.begin_nested():
                stop = db.get(Stop, item.stop_id)
                if stop is None:
                    results.append(
                        DeliveryEventResult(
                            client_op_id=item.client_op_id, accepted=False, message="stop_not_found"
                        )
                    )
                    continue
                response = apply_event(db, stop, item, current_user)
                db.flush()
            results.append(
                DeliveryEventResult(
                    client_op_id=item.client_op_id,
                    accepted=True,
                    message="duplicate" if response.get("idempotent") else None,
                )
            )
        except HTTPException as exc:
            results.append(
                DeliveryEventResult(
                    client_op_id=item.client_op_id,
                    accepted=False,
                    message=exc.detail["code"].lower(),
                )
            )
        except IntegrityError:
            results.append(
                DeliveryEventResult(
                    client_op_id=item.client_op_id, accepted=False, message="sync_conflict"
                )
            )
    db.commit()
    return results


def upload_pod(
    file: UploadFile,
    db: DbDep,
    current_user: CurrentUser,
    stop_id: Optional[str] = None,
    _: None = _UPLOAD_ROLES,
):
    from app.application.use_cases.proofs import upload

    return upload(db, current_user, file, stop_id)


def record_position(body: PositionIn, db: DbDep, current_user: CurrentUser, _: None = _DRIVER):
    """Store one GPS fix from the driver's device for the vehicle they are assigned to."""
    if current_user.role == "DRIVER" and (
        not current_user.vehicle_id or body.vehicle_id != current_user.vehicle_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You can only report your assigned vehicle."},
        )
    if not (-90 <= body.lat <= 90 and -180 <= body.lng <= 180) or body.accuracy < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "BAD_POSITION", "message": "The GPS position is invalid."},
        )
    db.add(
        VehiclePosition(
            vehicle_id=body.vehicle_id,
            user_id=current_user.id,
            lat=body.lat,
            lng=body.lng,
            accuracy=body.accuracy,
            recorded_at=body.recorded_at,
        )
    )
    db.commit()
    return {"ok": True}


def latest_positions(db: DbDep, current_user: CurrentUser, _: None = _DRIVER):
    """The most recent fix for each vehicle that has reported one."""
    query = db.query(VehiclePosition)
    if current_user.role == "DRIVER":
        if not current_user.vehicle_id:
            return []
        query = query.filter(VehiclePosition.vehicle_id == current_user.vehicle_id)
    rows = (
        query.distinct(VehiclePosition.vehicle_id)
        .order_by(VehiclePosition.vehicle_id, VehiclePosition.recorded_at.desc())
        .all()
    )
    return rows
