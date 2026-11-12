from __future__ import annotations
from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter

from waypoint_contracts.runtime import (
    CreatedResult,
    DeviceResult,
    DriverHistoryEvent,
    OkResult,
    StatusResult,
    UploadResult,
)
from typing import Optional
from fastapi import APIRouter, Form, UploadFile, status, Query
from waypoint_contracts.plan import SyncHistoryPage
from waypoint_contracts.position import PositionIn, PositionOut
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.plan import DeliveryEventIn, DeliveryEventResult, SyncBatch, TripOut
from app.application.use_cases import driver as use_cases

router = APIRouter(prefix="/driver", tags=["driver"])
_DRIVER = require_role("DRIVER", "DISPATCHER")
_UPLOAD_ROLES = require_role("DRIVER", "DISPATCHER", "LOADER")


@router.get("/trips/current", response_model=Optional[TripOut])
def current_trip(
    db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DRIVER]
) -> Optional[TripOut]:
    """Return the driver's active trip (LOADING, LOADED, or IN_TRANSIT)."""
    return TypeAdapter(Optional[TripOut]).validate_python(
        use_cases.current_trip(db=db, current_user=current_user, _=None)
    )


@router.post(
    "/trips/start",
    status_code=status.HTTP_200_OK,
    response_model=StatusResult,
    response_model_exclude_unset=True,
)
def start_driver_trip(
    db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DRIVER]
) -> StatusResult:
    """Mark the driver's current trip as IN_TRANSIT (LOADED -> IN_TRANSIT)."""
    return TypeAdapter(StatusResult).validate_python(
        use_cases.start_driver_trip(db=db, current_user=current_user, _=None)
    )


@router.post(
    "/stops/{stop_id}/events",
    status_code=201,
    response_model=DeviceResult,
    response_model_exclude_unset=True,
)
def record_stop_event(
    stop_id: int,
    body: DeliveryEventIn,
    db: DbDep,
    current_user: CurrentUser,
    _: Annotated[Actor, _DRIVER],
) -> DeviceResult:
    return TypeAdapter(DeviceResult).validate_python(
        use_cases.record_stop_event(
            stop_id=stop_id, body=body, db=db, current_user=current_user, _=None
        )
    )


@router.post("/sync", response_model=list[DeliveryEventResult])
def sync_events(
    body: SyncBatch, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DRIVER]
) -> list[DeliveryEventResult]:
    return TypeAdapter(list[DeliveryEventResult]).validate_python(
        use_cases.sync_events(body=body, db=db, current_user=current_user, _=None)
    )


@router.post("/uploads", response_model=UploadResult, response_model_exclude_unset=True)
def upload_pod(
    file: UploadFile,
    db: DbDep,
    current_user: CurrentUser,
    stop_id: Optional[str] = Form(None),
    *,
    _: Annotated[Actor, _UPLOAD_ROLES],
) -> UploadResult:
    return TypeAdapter(UploadResult).validate_python(
        use_cases.upload_pod(file=file, db=db, current_user=current_user, stop_id=stop_id, _=None)
    )


@router.post(
    "/positions",
    status_code=status.HTTP_201_CREATED,
    response_model=OkResult,
    response_model_exclude_unset=True,
)
def record_position(
    body: PositionIn, db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DRIVER]
) -> OkResult:
    """Store one GPS fix from the driver's device for the vehicle they are assigned to."""
    return TypeAdapter(OkResult).validate_python(
        use_cases.record_position(body=body, db=db, current_user=current_user, _=None)
    )


@router.get("/positions/latest", response_model=list[PositionOut])
def latest_positions(
    db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DRIVER]
) -> list[PositionOut]:
    """The most recent fix for each vehicle that has reported one."""
    return TypeAdapter(list[PositionOut]).validate_python(
        use_cases.latest_positions(db=db, current_user=current_user, _=None)
    )


@router.post(
    "/check-delivery-windows", response_model=CreatedResult, response_model_exclude_unset=True
)
def check_delivery_windows(
    db: DbDep, current_user: CurrentUser, _: Annotated[Actor, _DRIVER]
) -> CreatedResult:
    from app.application.use_cases.delivery_windows import check

    return TypeAdapter(CreatedResult).validate_python(check(db, current_user))


@router.get("/sync", response_model=SyncHistoryPage)
def sync_history(
    db: DbDep,
    current_user: CurrentUser,
    device_id: str = Query(min_length=1, max_length=100),
    after: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    *,
    _: Annotated[Actor, _DRIVER],
) -> SyncHistoryPage:
    from app.application.use_cases.sync_history import read_history

    return TypeAdapter(SyncHistoryPage).validate_python(
        read_history(db, current_user, device_id, after, limit)
    )


@router.get("/history", response_model=list[DriverHistoryEvent], response_model_exclude_unset=True)
def route_history(
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    *,
    _: Annotated[Actor, _DRIVER],
) -> list[DriverHistoryEvent]:
    from app.application.use_cases.driver_history import read_history

    return TypeAdapter(list[DriverHistoryEvent]).validate_python(
        read_history(db, current_user, limit, offset)
    )
