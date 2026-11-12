from functools import lru_cache
from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_expire_minutes: int = 480
    jwt_previous_secret: str | None = None
    environment: str = "local"

    @model_validator(mode="after")
    def secure(self):
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
def get_settings():
    return Settings()
