from __future__ import annotations
from pydantic import TypeAdapter

from fastapi import APIRouter
from waypoint_identity.api.dependencies import CurrentUser, DbDep
from waypoint_contracts.admin import ContactUpdate
from waypoint_contracts.auth import (
    LoginRequest,
    TokenResponse,
    UserProfile,
    AccountChangeRequest,
)
from waypoint_contracts.runtime import OkResult
from waypoint_identity.application.use_cases import auth as use_cases

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbDep) -> TokenResponse:
    return TypeAdapter(TokenResponse).validate_python(use_cases.login(body=body, db=db))


@router.get("/me", response_model=UserProfile)
def me(current_user: CurrentUser) -> UserProfile:
    return TypeAdapter(UserProfile).validate_python(
        use_cases.me(current_user=current_user)
    )


@router.patch("/me", response_model=UserProfile)
def update_me(body: ContactUpdate, current_user: CurrentUser, db: DbDep) -> UserProfile:
    """A person changes their own name, email and phone. Role and assignments need an administrator."""
    return TypeAdapter(UserProfile).validate_python(
        use_cases.update_me(body=body, current_user=current_user, db=db)
    )


@router.post("/account-change-requests", response_model=OkResult, status_code=201)
def request_account_change(
    body: AccountChangeRequest, current_user: CurrentUser, db: DbDep
) -> OkResult:
    use_cases.request_account_change(body.detail, current_user, db)
    return OkResult(ok=True)
