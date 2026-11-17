"""Construct planned-only feature rows; never send POD outcomes or actual timings to ML."""

from __future__ import annotations
from zoneinfo import ZoneInfo
import datetime as dt
from typing import Literal
from app.domain.planning.allocate import service_minutes
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from waypoint_security import Actor
from waypoint_contracts.intelligence import (
    PlannedDelivery,
    PlannedPredictionRequest,
    PredictionResponse,
)
from app.core import clock
from app.infrastructure.db.models.plan import Plan, Trip, Stop, StopOrder
from app.infrastructure.db.models.reference import Depot, Vehicle
from app.domain.planning.distance import road_distance_km
from app.infrastructure.intelligence import predict


def plan_predictions(
    db: Session, user: Actor, authorization: str | None, plan_id: int | None = None
) -> PredictionResponse:
    query = db.query(Plan).options(
        selectinload(Plan.trips)
        .selectinload(Trip.stops)
        .selectinload(Stop.stop_orders)
        .selectinload(StopOrder.order_rel),
        selectinload(Plan.trips).selectinload(Trip.stops).selectinload(Stop.outlet_rel),
    )
    if plan_id is not None:
        query = query.filter(Plan.id == plan_id)
    else:
        query = query.filter(
            Plan.delivery_date == clock.delivery_date(), Plan.status.in_(["DRAFT", "PUBLISHED"])
        )
    plan = query.order_by(Plan.created_at.desc()).first()
    if plan is None:
        raise HTTPException(
            404,
            detail={"code": "NO_PLAN", "message": "Create a plan before requesting predictions."},
        )
    rows: list[PlannedDelivery] = []
    local = ZoneInfo("Asia/Colombo")
    for trip in plan.trips:
        vehicle = db.get(Vehicle, trip.vehicle_id)
        if vehicle is None or (user.depot_id and user.depot_id != vehicle.depot_code):
            continue
        depot = db.get(Depot, vehicle.depot_code)
        if not depot or depot.lat is None or depot.lng is None or not trip.planned_depart:
            raise HTTPException(
                422,
                detail={
                    "code": "PLAN_FEATURES_MISSING",
                    "message": "The plan needs depot coordinates and departure estimates.",
                },
            )
        previous = trip.planned_depart.astimezone(local)
        lat, lng = depot.lat, depot.lng
        sequence = 1
        for stop in sorted(trip.stops, key=lambda item: item.sequence):
            outlet = stop.outlet_rel
            if not stop.planned_eta or outlet.lat is None or outlet.lng is None:
                raise HTTPException(
                    422,
                    detail={
                        "code": "PLAN_FEATURES_MISSING",
                        "message": "The plan needs outlet coordinates and arrival estimates.",
                    },
                )
            arrival = stop.planned_eta.astimezone(local)
            distance = road_distance_km(lat, lng, outlet.lat, outlet.lng)
            for link in stop.stop_orders:
                order = link.order_rel
                temperature: Literal["chilled", "ambient"] = (
                    "chilled" if order.temperature_class in ("CHILLED", "FROZEN") else "ambient"
                )
                rows.append(
                    PlannedDelivery(
                        delivery_id=order.reference,
                        route_id=str(trip.id),
                        seq_in_route=sequence,
                        dispatch_date=plan.delivery_date,
                        outlet_id=stop.outlet_id,
                        vehicle_id=trip.vehicle_id,
                        temp_requirement=temperature,
                        order_units=max(1, order.total_cases),
                        order_weight_kg=order.total_weight,
                        order_volume_m3=order.total_volume,
                        planned_depart_time=previous.time().replace(tzinfo=None),
                        planned_arrival_time=arrival.time().replace(tzinfo=None),
                        planned_travel_duration_min=max(
                            0, (arrival - previous).total_seconds() / 60
                        ),
                        distance_km=distance,
                    )
                )
                sequence += 1
            previous = arrival + dt.timedelta(minutes=service_minutes(outlet.dock_type))
            lat, lng = outlet.lat, outlet.lng
    if not rows:
        return PredictionResponse(model_version="no-assigned-orders", predictions=[])
    if len(rows) > 500:
        raise HTTPException(
            413,
            detail={
                "code": "PLAN_TOO_LARGE",
                "message": "At most 500 planned orders can be predicted at once.",
            },
        )
    return predict(PlannedPredictionRequest(deliveries=rows), authorization)
