"""FastAPI dependencies: DB session, current user, role guards."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models.user import User

bearer = HTTPBearer(auto_error=False)

DbDep = Annotated[Session, Depends(get_db)]


def _get_current_user(
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required."},
        )
    from app.core.config import get_settings

    if get_settings().identity_url:
        from waypoint_security import current_principal

        principal = current_principal("Bearer " + credentials.credentials)
        # Maintain an owned projection for existing local FK/response contracts.
        user = db.get(User, principal.id)
        if user is None:
            user = User(id=principal.id, password_hash="!external-identity")
            db.add(user)
        for key, value in principal.model_dump().items():
            if hasattr(User, key):
                setattr(user, key, value)
        db.flush()
        return user
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: int = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
        )
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found or deactivated."},
        )
    return user


CurrentUser = Annotated[User, Depends(_get_current_user)]


def require_role(*roles: str):
    """Return a dependency that enforces the user has one of the given roles."""

    def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles and not (
            current_user.role == "ADMIN" and "DISPATCHER" in roles
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"This endpoint requires role: {', '.join(roles)}.",
                },
            )
        return current_user

    return Depends(_check)
