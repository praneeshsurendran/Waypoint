from __future__ import annotations
from fastapi import APIRouter
from app.api.deps import CurrentUser, DbDep
from waypoint_contracts.admin import ContactUpdate
from waypoint_contracts.auth import LoginRequest, TokenResponse, UserProfile
from app.application.use_cases import auth as use_cases

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbDep):
    return use_cases.login(body=body, db=db)


@router.get("/me", response_model=UserProfile)
def me(current_user: CurrentUser):
    return use_cases.me(current_user=current_user)


@router.patch("/me", response_model=UserProfile)
def update_me(body: ContactUpdate, current_user: CurrentUser, db: DbDep):
    """A person changes their own name, email and phone. Role and assignments need an administrator."""
    return use_cases.update_me(body=body, current_user=current_user, db=db)
