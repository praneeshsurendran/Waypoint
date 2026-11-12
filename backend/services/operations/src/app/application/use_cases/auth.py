"""Auth router: login and /me."""

from __future__ import annotations

from pydantic import TypeAdapter
from waypoint_contracts.admin import ContactUpdate
from waypoint_contracts.auth import LoginRequest, TokenResponse, UserProfile

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbDep
from waypoint_security import Actor as CurrentUser
from app.core.security import create_access_token, verify_password
from app.infrastructure.db.models.user import User


def login(body: LoginRequest, db: DbDep) -> TokenResponse:
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "BAD_CREDENTIALS", "message": "Invalid username or password."},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INACTIVE_USER", "message": "This account is deactivated."},
        )
    token = create_access_token(str(user.id))
    return TypeAdapter(TokenResponse).validate_python(
        TokenResponse(access_token=token, user=UserProfile.model_validate(user))
    )


def me(current_user: CurrentUser) -> UserProfile:
    return TypeAdapter(UserProfile).validate_python(UserProfile.model_validate(current_user))


def update_me(body: ContactUpdate, current_user: CurrentUser, db: DbDep) -> UserProfile:
    """A person changes their own name, email and phone. Role and assignments need an administrator."""
    changes = body.model_dump(exclude_unset=True)
    for field, column in (("email", User.email), ("phone", User.phone)):
        value = (changes.get(field) or "").strip() or None
        if field in changes:
            changes[field] = value.lower() if value and field == "email" else value
            if (
                value
                and db.query(User)
                .filter(column == changes[field], User.id != current_user.id)
                .first()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "DUPLICATE", "message": f"That {field} is already in use."},
                )
    if "full_name" in changes and (not (changes["full_name"] or "").strip()):
        changes.pop("full_name")
    for field, value in changes.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return TypeAdapter(UserProfile).validate_python(UserProfile.model_validate(current_user))
