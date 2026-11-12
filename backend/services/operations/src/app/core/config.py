from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    service_mode: str = "legacy"
    identity_url: str | None = None
    demo_mode: bool = True
    storage_backend: str = "local"
    pod_bucket: str | None = None
    max_upload_bytes: int = 8 * 1024 * 1024
    pool_size: int = 5
    pool_max_overflow: int = 5

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if self.storage_backend != "s3" or not self.pod_bucket:
                raise ValueError("Production requires private S3 proof storage")
            if self.demo_mode or self.seed_on_start:
                raise ValueError("Production cannot enable demo clock or startup seeding")
            if self.service_mode != "operations" or not self.identity_url:
                raise ValueError("Production requires isolated operations mode and identity URL")
            if "*" in self.cors_origins_list:
                raise ValueError("Production requires explicit CORS origins")
        return self

    # Database
    database_url: str = "postgresql+psycopg://waypoint:waypoint@localhost:5432/waypoint"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expire_minutes: int = 480
    jwt_algorithm: str = "HS256"

    # CORS — comma-separated origins stored as a string, parsed into a list
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # File uploads
    upload_dir: str = "/uploads"

    # Data directory (CSV source files)
    data_dir: str = "/data/General Data"

    # Seeding
    seed_on_start: bool = False

    # Business clock (demo)
    # "Today" for the demo: if not set, defaults to one day before demo_delivery_date
    business_date: str | None = None
    demo_delivery_date: str = "2024-04-10"

    # App timezone
    app_timezone: str = "Asia/Colombo"


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, None]
