"""Schemas for device GPS fixes."""

from __future__ import annotations


import datetime as dt

from pydantic import ConfigDict
from waypoint_contracts.common import ContractModel as BaseModel


class PositionIn(BaseModel):
    vehicle_id: str
    lat: float
    lng: float
    accuracy: float
    recorded_at: dt.datetime


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle_id: str
    lat: float
    lng: float
    accuracy: float
    recorded_at: dt.datetime
