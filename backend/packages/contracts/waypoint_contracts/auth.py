"""Auth schemas."""

from __future__ import annotations


from typing import Optional
from pydantic import Field
from waypoint_contracts.runtime import Role

from waypoint_contracts.common import ContractModel as BaseModel

from waypoint_contracts.common import OrmModel


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserProfile"


class UserProfile(OrmModel):
    id: int
    username: str
    full_name: str
    role: Role
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    outlet_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    depot_id: Optional[str] = None
