"""Auth schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from waypoint_contracts.common import OrmModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserProfile"


class UserProfile(OrmModel):
    id: int
    username: str
    full_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    outlet_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    depot_id: Optional[str] = None
