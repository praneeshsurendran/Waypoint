from waypoint_observability import correlation_id, traceparent
import os
from typing import Annotated, Literal, Protocol
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
import httpx
from fastapi import Header, HTTPException, Request
from pydantic import BaseModel
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

"""Verified identity transport; forwarded role headers are never authoritative."""


class Principal(BaseModel):
    id: int
    username: str
    full_name: str
    role: Literal["ADMIN", "DISPATCHER", "LOADER", "DRIVER", "STORE_MANAGER"]
    is_active: Literal[True]
    outlet_id: str | None = None
    vehicle_id: str | None = None
    depot_id: str | None = None
    email: str | None = None
    phone: str | None = None


class Actor(Protocol):
    @property
    def id(self) -> int: ...
    @property
    def username(self) -> str: ...
    @property
    def full_name(self) -> str: ...
    @property
    def role(self) -> str: ...
    @property
    def is_active(self) -> bool: ...
    @property
    def outlet_id(self) -> str | None: ...
    @property
    def vehicle_id(self) -> str | None: ...
    @property
    def depot_id(self) -> str | None: ...
    @property
    def email(self) -> str | None: ...
    @property
    def phone(self) -> str | None: ...


@lru_cache
def _identity_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(3, connect=1),
        limits=httpx.Limits(
            max_connections=20, max_keepalive_connections=10, keepalive_expiry=20
        ),
        follow_redirects=False,
    )


@contextmanager
def client_factory(**kwargs: object) -> Iterator[httpx.Client]:
    # The existing factory seam remains usable by transport tests; production shares the pool.
    yield _identity_client()


def close_identity_client() -> None:
    if _identity_client.cache_info().currsize:
        _identity_client().close()
        _identity_client.cache_clear()


def current_principal(
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            401, detail={"code": "MISSING_TOKEN", "message": "Authentication required."}
        )
    try:
        with client_factory(timeout=httpx.Timeout(3, connect=1)) as client:
            response = client.get(
                os.environ["IDENTITY_URL"] + "/api/v1/auth/me",
                headers={
                    "Authorization": authorization,
                    "X-Correlation-ID": correlation_id.get(),
                    "traceparent": traceparent.get() or "",
                },
            )
        if response.status_code in (401, 403):
            raise HTTPException(
                response.status_code,
                detail={"code": "INVALID_TOKEN", "message": "Authentication failed."},
            )
        if response.status_code == 429:
            retry = response.headers.get("Retry-After", "1")
            raise HTTPException(
                429,
                detail={
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please retry later.",
                },
                headers={"Retry-After": retry if retry.isdigit() else "1"},
            )
        response.raise_for_status()
        return Principal.model_validate(response.json())
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(
            503,
            detail={
                "code": "IDENTITY_UNAVAILABLE",
                "message": "Identity verification unavailable.",
            },
        ) from None


_bearer = HTTPBearer(auto_error=False)


def verified_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    request: Request,
) -> Principal:
    principal = current_principal(
        "Bearer " + credentials.credentials if credentials else None
    )
    from waypoint_runtime.rate_limit import enforce_user

    enforce_user(request, principal.id)
    return principal


def validate_runtime() -> None:
    if os.environ.get("ENVIRONMENT") != "production":
        return
    from urllib.parse import urlparse, parse_qs

    query = parse_qs(urlparse(os.environ["DATABASE_URL"]).query)
    if query.get("sslmode") != ["verify-full"]:
        raise ValueError(
            "Production database connections require sslmode=verify-full and a trusted root certificate"
        )
    if os.environ.get("IDENTITY_URL") and not os.environ["IDENTITY_URL"].startswith(
        "https://"
    ):
        raise ValueError("Production identity calls require HTTPS")
    if os.environ.get("AWS_ENDPOINT_URL"):
        raise ValueError("Production cannot use a local AWS emulator endpoint")
    if "*" in os.environ.get("CORS_ORIGINS", ""):
        raise ValueError("Production requires explicit CORS origins")
