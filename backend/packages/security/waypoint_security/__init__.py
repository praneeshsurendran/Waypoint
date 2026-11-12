from waypoint_observability import correlation_id, traceparent
import os
from typing import Annotated
import httpx
from fastapi import Header, HTTPException
from pydantic import BaseModel
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

"""Verified identity transport; forwarded role headers are never authoritative."""


class Principal(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool = True
    outlet_id: str | None = None
    vehicle_id: str | None = None
    depot_id: str | None = None
    email: str | None = None
    phone: str | None = None


client_factory = httpx.Client


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
) -> Principal:
    return current_principal(
        "Bearer " + credentials.credentials if credentials else None
    )


def validate_runtime():
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
