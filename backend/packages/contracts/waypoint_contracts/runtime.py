"""Explicit v1 response contracts for actions and operational read models."""

import datetime as dt
from typing import Literal, TypedDict, NotRequired
from pydantic import Field, JsonValue, ConfigDict, FiniteFloat
from waypoint_contracts.common import ContractModel as BaseModel

Role = Literal["ADMIN", "DISPATCHER", "LOADER", "DRIVER", "STORE_MANAGER"]
JobState = Literal["pending", "running", "succeeded", "failed", "cancelled"]


class OkResult(BaseModel):
    ok: bool


class StatusResult(OkResult):
    status: str


class DeviceResult(TypedDict):
    ok: bool
    idempotent: NotRequired[bool | None]


class ReceiptResult(OkResult):
    receipt_status: str
    idempotent: bool | None = None


class IntakeStatus(BaseModel):
    cutoff_closed: bool
    published: bool
    delivery_date: dt.date
    next_delivery_date: dt.date
    now: dt.datetime


class ClosureResult(BaseModel):
    closed: int
    delivery_date: dt.date


class UploadResult(BaseModel):
    path: str


class DownloadResult(BaseModel):
    url: str
    expires_in: int
    requires_authorization: bool


class CreatedResult(BaseModel):
    created: int


class JobResult(BaseModel):
    job_id: str
    status: JobState


class JobStatus(JobResult):
    plan_id: int | None
    error_code: str | None


class LiveHealth(BaseModel):
    status: Literal["ok"]
    service: str


class ReadyHealth(BaseModel):
    status: Literal["ready"]
    db: str | None = None


class ClockAdvanceRequest(BaseModel):
    business_date: str


class ClockResult(BaseModel):
    business_date: dt.date
    now: dt.datetime
    delivery_date: dt.date | None = None
    past_cutoff: bool | None = None


class EventLogEntry(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    after: dict[str, JsonValue] | None
    created_at: dt.datetime


class EventPage(BaseModel):
    events: list[EventLogEntry]
    count: int
    next_cursor: int | None = None


class DriverHistoryEvent(BaseModel):
    id: str
    at: dt.datetime
    day: dt.date
    vehicleId: str
    trip: int
    revision: int
    kind: Literal[
        "loaderConfirmed",
        "released",
        "started",
        "arrived",
        "proofSaved",
        "accepted",
        "delay",
        "breakdown",
        "attempt",
        "reopened",
        "completed",
    ]
    detail: str
    stopId: str | None = None
    outletId: str | None = None


class NotificationDecision(BaseModel):
    model_config = ConfigDict(extra="allow")
    reason_code: str | None = None


class NotificationPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    outlet_id: str | None = None
    stop_id: int | None = None
    vehicle_id: str | None = None
    depot_id: str | None = None
    order_id: int | None = None
    note: str | None = None
    decision: NotificationDecision | None = None


class NotificationOut(BaseModel):
    id: str
    type: str
    data: NotificationPayload
    created_at: dt.datetime
    read: bool


class ManagerContact(BaseModel):
    id: int
    full_name: str
    phone: str | None
    outlet_id: str | None


class PlanViolation(BaseModel):
    rule: str
    severity: str
    trip_vehicle_id: str | None
    stop_outlet_id: str | None
    order_id: int | str | None
    message: str


class PlanValidation(BaseModel):
    plan_id: int
    violations: list[PlanViolation]
    valid: bool


class PublishResult(TypedDict):
    plan_id: int
    status: str
    published_at: dt.datetime
    orders_planned: int
    trips: int


class PlanMove(BaseModel):
    order_id: int = Field(gt=0)
    to_trip_id: int | None = Field(default=None, gt=0)
    sequence: int | None = Field(default=None, ge=1)


class PlanEdit(BaseModel):
    moves: list[PlanMove] = Field(default_factory=list, max_length=200)
    expected_version: int | None = Field(default=None, ge=1)


class DemandTotals(BaseModel):
    orders: int
    total_weight_kg: float
    total_volume_m3: float
    chilled_weight_kg: float
    chilled_volume_m3: float
    orders_deferred: int


class FleetTotals(BaseModel):
    total_weight_kg: float
    total_volume_m3: float
    reefer_weight_kg: float
    reefer_volume_m3: float


class Utilisation(BaseModel):
    weight_pct: float | None
    volume_pct: float | None
    reefer_weight_pct: float | None
    reefer_volume_pct: float | None


class DepotCapacity(BaseModel):
    capacity_weight_kg: float
    capacity_volume_m3: float
    reefer_weight_kg: float
    reefer_volume_m3: float
    vehicles_total: int
    vehicles_fuel_ok: int


class CapacityCalendar(BaseModel):
    is_operating: bool | None
    is_payday: bool | None
    festival: str | None
    festival_ramp: float | None
    is_monsoon: bool | None


class CapacityForecast(BaseModel):
    date: dt.date
    calendar: CapacityCalendar
    demand: DemandTotals
    fleet: FleetTotals
    utilisation: Utilisation
    depots: dict[str, DepotCapacity]


class StatusCounts(BaseModel):
    total: int
    by_status: dict[str, int]


class OrderCounts(StatusCounts):
    delivered: int
    failed: int
    deferred: int


class TripCounts(StatusCounts):
    completed: int


class DailySummary(BaseModel):
    date: dt.date
    orders: OrderCounts
    trips: TripCounts
    stops: StatusCounts


class FuelUsage(BaseModel):
    vehicle_id: str
    depot_code: str
    type: str
    is_refrigerated: bool
    quota_l: float
    used_l: float
    remaining_l: float
    pct_used: float
    near_limit: bool


class FuelSummary(BaseModel):
    iso_year: int
    iso_week: int
    vehicles: list[FuelUsage]


class DemandWeek(TypedDict):
    depot: str
    brand: str
    iso_year: int
    iso_week: int
    total_m3: FiniteFloat
    chilled_m3: FiniteFloat
    is_event_week: bool
    row_id: NotRequired[str | None]
    in_test_horizon: NotRequired[bool]


class WeekCapacity(TypedDict):
    depot: str
    iso_year: int
    iso_week: int
    total_m3: FiniteFloat
    chilled_m3: FiniteFloat
    operating_days: int
    vehicles_needed: int
    vehicles_available: int
    reefers_needed: int
    reefers_available: int
    drivers_needed: int
    drivers_available: int
    shortfall_drivers: int
    shortfall_vehicles: int
    shortfall_reefers: int


class Backtest(TypedDict):
    weeks: list[str]
    wape_percent: FiniteFloat | None
    by_depot: dict[str, FiniteFloat | None]


class DemandForecast(TypedDict):
    method: str
    history: list[DemandWeek]
    forecast: list[DemandWeek]
    capacity: list[WeekCapacity]
    backtest: Backtest
