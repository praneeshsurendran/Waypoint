from __future__ import annotations

import datetime as dt
from typing import Any

import bcrypt
import jwt

from waypoint_identity.core.settings import get_settings


def hash_password(password: str) -> str:
    if not 8 <= len(password.encode()) <= 72:
        raise ValueError("Password must be between 8 and 72 bytes")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    if len(password.encode()) > 72:
        return False
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": dt.datetime.now(dt.timezone.utc),
        "exp": dt.datetime.now(dt.timezone.utc)
        + dt.timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.InvalidSignatureError:
        if not settings.jwt_previous_secret:
            raise
        return jwt.decode(
            token,
            settings.jwt_previous_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
