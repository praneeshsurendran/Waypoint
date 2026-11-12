from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_contracts.runtime import StatusResult, OkResult
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.plan import LoadFlagIn, TripOut
from app.application.use_cases import loading as use_cases

router = APIRouter(prefix="/loading", tags=["loading"])
_LOADER = require_role("LOADER", "DISPATCHER")
_READ_ROLES = require_role("LOADER", "DISPATCHER", "DRIVER")


@router.get("/trips", response_model=list[TripOut])
def list_loading_trips(
    db: DbDep,
    current_user: CurrentUser,
    *,
    _: Annotated[Actor, _READ_ROLES],
    date: Optional[dt.date] = Query(None),
    depot: Optional[str] = Query(None),
) -> list[TripOut]:
    return TypeAdapter(list[TripOut]).validate_python(
        use_cases.list_loading_trips(
            db=db, current_user=current_user, _=None, date=date, depot=depot
        )
    )


@router.get("/trips/{trip_id}", response_model=TripOut)
def get_loading_trip(
    trip_id: int, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _READ_ROLES]
) -> TripOut:
    return TypeAdapter(TripOut).validate_python(
        use_cases.get_loading_trip(trip_id=trip_id, db=db, current_user=current_user, _=None)
    )


@router.post("/trips/{trip_id}/flags", status_code=status.HTTP_201_CREATED, response_model=OkResult)
def flag_load(
    trip_id: int,
    body: LoadFlagIn,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, _LOADER],
) -> OkResult:
    return TypeAdapter(OkResult).validate_python(
        use_cases.flag_load(trip_id=trip_id, body=body, db=db, current_user=current_user, _=None)
    )


@router.post(
    "/trips/{trip_id}/start",
    status_code=status.HTTP_200_OK,
    response_model=StatusResult,
    response_model_exclude_unset=True,
)
def start_loading_trip(
    trip_id: int, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _LOADER]
) -> StatusResult:
    """Mark that vehicle loading has physically started at the bay (PLANNED -> LOADING)."""
    return TypeAdapter(StatusResult).validate_python(
        use_cases.start_loading_trip(trip_id=trip_id, db=db, current_user=current_user, _=None)
    )


@router.post(
    "/trips/{trip_id}/release",
    status_code=status.HTTP_200_OK,
    response_model=StatusResult,
    response_model_exclude_unset=True,
)
def release_trip(
    trip_id: int, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _LOADER]
) -> StatusResult:
    """Release vehicle after loading is complete (PLANNED/LOADING -> LOADED)."""
    return TypeAdapter(StatusResult).validate_python(
        use_cases.release_trip(trip_id=trip_id, db=db, current_user=current_user, _=None)
    )
