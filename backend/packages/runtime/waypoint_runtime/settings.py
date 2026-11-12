"""Explicit runtime settings; Redis is optional only for isolated native/test execution."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    environment: Literal["local", "test", "production"] = "local"
    redis_url: str | None = None
    runtime_namespace: str = Field(default="waypoint", min_length=1, max_length=100)
    trusted_proxy_cidrs: str = ""
    rate_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_login: int = Field(default=10, ge=1)
    rate_client: int = Field(default=6000, ge=1)
    rate_reads: int = Field(default=600, ge=1)
    rate_writes: int = Field(default=120, ge=1)
    rate_planning: int = Field(default=6, ge=1)
    rate_bulk: int = Field(default=30, ge=1)
    reference_cache_ttl_seconds: int = Field(default=30, ge=1, le=300)

    @model_validator(mode="after")
    def production_redis(self) -> "RuntimeSettings":
        import ipaddress

        for network in self.trusted_proxy_cidrs.split(","):
            if network.strip():
                ipaddress.ip_network(network.strip())
        if self.environment == "production":
            if not self.redis_url:
                raise ValueError("Production requires distributed Redis rate limiting")
            parsed = urlparse(self.redis_url)
            if parsed.scheme != "rediss" or not parsed.password:
                raise ValueError("Production Redis requires authenticated TLS (rediss)")
        return self


@lru_cache
def settings() -> RuntimeSettings:
    return RuntimeSettings()
