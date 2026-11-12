"""Plan / Trip / Stop schemas."""

from __future__ import annotations


import datetime as dt
from typing import Any, Optional, Literal

from pydantic import Field, model_validator
from waypoint_contracts.common import ContractModel as BaseModel

from waypoint_contracts.common import OrmModel


class StopOut(OrmModel):
    id: int
    trip_id: int
    outlet_id: str
    sequence: int
    planned_eta: Optional[dt.datetime] = None
    actual_arrival: Optional[dt.datetime] = None
    actual_departure: Optional[dt.datetime] = None
    status: str
    district: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    window_open: Optional[str] = None
    window_close: Optional[str] = None
    order_ids: list[int] = []
    total_cases: Optional[int] = 0
    proof_id: Optional[str] = None


class TripOut(OrmModel):
    id: int
    plan_id: int
    vehicle_id: str
    trip_number: int
    planned_depart: Optional[dt.datetime] = None
    planned_return: Optional[dt.datetime] = None
    planned_distance: Optional[float] = None
    planned_fuel: Optional[float] = None
    planned_weight: Optional[float] = 0.0
    planned_volume: Optional[float] = 0.0
    status: str
    stops: list[StopOut] = []
    photo_path: Optional[str] = None


class PlanOut(OrmModel):
    id: int
    delivery_date: dt.date
    version: int
    status: str
    created_at: dt.datetime
    published_at: Optional[dt.datetime] = None
    summary_json: Optional[dict[str, Any]] = None
    trips: list[TripOut] = []


class DeferralOut(OrmModel):
    id: int
    plan_id: int
    order_id: int
    reason_code: str
    explanation: Optional[str] = None
    consecutive_count: int
    decided_by: str
    decided_at: dt.datetime
    next_run_date: Optional[dt.date] = None
    is_override: bool


class LoadFlagIn(BaseModel):
    order_id: Optional[int] = None
    status: Literal["OK", "MISSING", "DAMAGED"]
    note: Optional[str] = Field(default=None, max_length=4000)
    photo_path: Optional[str] = None


class DeliveryEventIn(BaseModel):
    client_op_id: str = Field(min_length=1, max_length=100)
    stop_id: int
    order_id: Optional[int] = None
    outcome: Literal[
        "STARTED",
        "ARRIVED",
        "DELIVERED",
        "PARTIAL",
        "REFUSED",
        "CLOSED",
        "FAILED",
        "DELAY",
    ]
    note: Optional[str] = Field(default=None, max_length=4000)
    pod_photo_path: Optional[str] = None
    pod_signature_path: Optional[str] = None
    receiver_name: Optional[str] = Field(default=None, max_length=200)
    receiver_pin_ok: Optional[bool] = None
    recorded_at: Optional[dt.datetime] = None
    device_id: str | None = Field(default=None, min_length=1, max_length=100)
    device_sequence: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def paired_device(self) -> "DeliveryEventIn":
        if (self.device_id is None) != (self.device_sequence is None):
            raise ValueError("device_id and device_sequence must be supplied together")
        if self.recorded_at is not None and self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must include a timezone")
        return self


class DeliveryEventResult(BaseModel):
    client_op_id: str = Field(min_length=1, max_length=100)
    accepted: bool
    message: Optional[str] = None


class SyncBatch(BaseModel):
    events: list[DeliveryEventIn] = Field(max_length=200)


class SyncHistoryEvent(BaseModel):
    client_op_id: str
    device_sequence: int
    received_at: dt.datetime
    event: dict
    result: dict


class SyncHistoryPage(BaseModel):
    device_id: str
    server_cursor: int
    next_cursor: int
    has_more: bool
    events: list[SyncHistoryEvent]
