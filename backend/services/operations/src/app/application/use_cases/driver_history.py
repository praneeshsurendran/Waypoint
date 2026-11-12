"""Scoped, durable driver timeline from the operations audit ledger."""

from sqlalchemy import String, and_, cast, or_, select
from app.infrastructure.db.models.audit import AuditLog
from app.infrastructure.db.models.plan import Plan, Stop, Trip
from app.infrastructure.db.models.reference import Vehicle


def read_history(db, user, limit, offset):
    query = (
        select(AuditLog, Trip, Stop, Plan.delivery_date)
        .select_from(AuditLog)
        .outerjoin(
            Stop, and_(AuditLog.entity_type == "Stop", AuditLog.entity_id == cast(Stop.id, String))
        )
        .join(
            Trip,
            or_(
                and_(AuditLog.entity_type == "Trip", AuditLog.entity_id == cast(Trip.id, String)),
                and_(AuditLog.entity_type == "Stop", Stop.trip_id == Trip.id),
            ),
        )
        .join(Plan, Trip.plan_id == Plan.id)
        .join(Vehicle, Trip.vehicle_id == Vehicle.vehicle_id)
        .where(
            AuditLog.action.in_(
                [
                    "START_TRIP",
                    "START_LOADING_TRIP",
                    "RELEASE_TRIP",
                    "LOAD_FLAG",
                    "DELIVERY_EVENT",
                    "RETRY_STOP",
                ]
            )
        )
    )
    if user.role == "DRIVER":
        if not user.vehicle_id:
            return []
        query = query.where(Trip.vehicle_id == user.vehicle_id)
    elif user.depot_id:
        query = query.where(Vehicle.depot_code == user.depot_id)
    rows = db.execute(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).offset(offset)
    ).all()
    events = []
    for audit, trip, stop, day in rows:
        data = audit.after_json or {}
        outcome = data.get("outcome", "")
        kind = {
            "START_TRIP": "started",
            "START_LOADING_TRIP": "loaderConfirmed",
            "RELEASE_TRIP": "released",
            "LOAD_FLAG": "loaderConfirmed",
            "RETRY_STOP": "reopened",
        }.get(audit.action)
        if kind is None:
            kind = {
                "STARTED": "started",
                "ARRIVED": "arrived",
                "DELAY": "delay",
                "DELIVERED": "accepted",
                "PARTIAL": "accepted",
            }.get(outcome, "attempt")
        events.append(
            {
                "id": f"audit-{audit.id}",
                "at": audit.created_at.isoformat(),
                "day": day.isoformat(),
                "vehicleId": trip.vehicle_id,
                "trip": trip.trip_number,
                "revision": trip.revision,
                "kind": kind,
                "detail": f"{audit.action.replace('_', ' ').title()}{': ' + outcome if outcome else ''}",
                "stopId": str(stop.id) if stop else None,
                "outletId": stop.outlet_id if stop else None,
            }
        )
    return events
