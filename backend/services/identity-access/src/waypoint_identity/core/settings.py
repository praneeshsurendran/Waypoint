from functools import lru_cache
import os
from typing import Literal
from pydantic import model_validator, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_expire_minutes: int = Field(default=480, ge=1, le=1440)
    jwt_issuer: str = Field(default="waypoint-identity", min_length=1)
    jwt_audience: str = Field(default="waypoint-api", min_length=1)
    jwt_previous_secret: str | None = None
    environment: str = "local"

    @model_validator(mode="after")
    def secure(self) -> "Settings":
        if self.environment == "production" and any(
            len(secret) < 32
            for secret in (self.jwt_secret, self.jwt_previous_secret)
            if secret is not None
        ):
            raise ValueError(
                "Production JWT signing secrets must have at least 32 characters"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET is required")
    return Settings(jwt_secret=secret)
