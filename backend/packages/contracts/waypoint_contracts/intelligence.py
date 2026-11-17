"""Validated, versioned ML transport; no training labels are accepted at inference."""

from __future__ import annotations
import datetime as dt
from typing import Literal
from pydantic import ConfigDict, Field, model_validator
from waypoint_contracts.common import ContractModel
from waypoint_contracts.runtime import Backtest


class PredictionRequest(ContractModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    delivery_ids: list[str] = Field(min_length=1, max_length=500)


class StopPrediction(ContractModel):
    delivery_id: str
    pred_service_min: float = Field(ge=0)
    pred_late_prob: float = Field(ge=0, le=1)


class PredictionResponse(ContractModel):
    model_version: str
    predictions: list[StopPrediction]


class ForecastRow(ContractModel):
    row_id: str
    depot: str
    brand: Literal["Fresh", "Style", "Tech"]
    iso_year: int
    iso_week: int = Field(ge=1, le=53)
    total_m3: float = Field(ge=0)
    chilled_m3: float = Field(ge=0)

    @model_validator(mode="after")
    def chilled_subset(self) -> ForecastRow:
        if self.chilled_m3 > self.total_m3 or (
            self.brand != "Fresh" and self.chilled_m3 != 0
        ):
            raise ValueError("chilled demand must be a Fresh subset of total demand")
        return self


class ForecastResponse(ContractModel):
    model_version: str
    method: str
    data_as_of: dt.date
    rows: list[ForecastRow]
    backtest: Backtest


class PlannedDelivery(ContractModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    delivery_id: str = Field(min_length=1, max_length=100)
    route_id: str = Field(min_length=1, max_length=100)
    seq_in_route: int = Field(ge=0)
    dispatch_date: dt.date
    outlet_id: str
    vehicle_id: str
    temp_requirement: Literal["ambient", "chilled", "frozen"]
    order_units: int = Field(ge=1)
    order_weight_kg: float = Field(gt=0)
    order_volume_m3: float = Field(gt=0)
    planned_depart_time: dt.time
    planned_arrival_time: dt.time
    planned_travel_duration_min: float = Field(ge=0)
    distance_km: float = Field(ge=0)


class PlannedPredictionRequest(ContractModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    deliveries: list[PlannedDelivery] = Field(min_length=1, max_length=500)
