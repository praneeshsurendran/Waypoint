from pydantic import TypeAdapter
from waypoint_contracts.runtime import NotificationOut, OkResult
from typing import Annotated, TypeVar, NoReturn
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from waypoint_security import Principal, verified_principal
from waypoint_notifications.bootstrap import get_db
from waypoint_notifications.infrastructure.db.notifications import (
    Notification,
    ReadReceipt,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])
CurrentUser = Annotated[Principal, Depends(verified_principal)]


RowT = TypeVar("RowT", bound=tuple[object, ...])


def scoped(query: Select[RowT], user: Principal) -> Select[RowT]:
    if user.role == "STORE_MANAGER":
        if not user.outlet_id:
            raise HTTPException(
                403,
                detail={"code": "FORBIDDEN", "message": "Outlet assignment required."},
            )
        return query.where(Notification.outlet_id == user.outlet_id)
    if user.role == "DRIVER":
        if not user.vehicle_id:
            raise HTTPException(
                403,
                detail={"code": "FORBIDDEN", "message": "Vehicle assignment required."},
            )
        return query.where(Notification.vehicle_id == user.vehicle_id)
    if user.role == "LOADER":
        if not user.depot_id:
            raise HTTPException(
                403,
                detail={"code": "FORBIDDEN", "message": "Depot assignment required."},
            )
        return query.where(Notification.depot_id == user.depot_id)
    if user.role == "DISPATCHER" and user.depot_id:
        return query.where(Notification.depot_id == user.depot_id)
    if user.role not in ("ADMIN", "DISPATCHER"):
        raise HTTPException(
            403, detail={"code": "FORBIDDEN", "message": "Unsupported role."}
        )
    return query


@router.get("", response_model=list[NotificationOut], response_model_exclude_unset=True)
def list_notifications(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[NotificationOut]:
    rows = db.execute(
        scoped(
            select(Notification, ReadReceipt.event_id).outerjoin(
                ReadReceipt,
                and_(
                    ReadReceipt.event_id == Notification.event_id,
                    ReadReceipt.user_id == user.id,
                ),
            ),
            user,
        )
        .order_by(Notification.created_at.desc(), Notification.event_id)
        .offset(offset)
        .limit(limit)
    ).all()
    return TypeAdapter(list[NotificationOut]).validate_python(
        [
            {
                "id": row.event_id,
                "type": row.event_type,
                "data": row.payload,
                "created_at": row.created_at,
                "read": read_event_id is not None,
            }
            for row, read_event_id in rows
        ]
    )


@router.post(
    "/{event_id}/read", response_model=OkResult, response_model_exclude_unset=True
)
def mark_read(
    event_id: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> OkResult:
    row = db.scalar(
        scoped(select(Notification).where(Notification.event_id == event_id), user)
    )
    if row is None:
        raise HTTPException(
            404, detail={"code": "NOT_FOUND", "message": "Notification not found."}
        )
    db.execute(
        insert(ReadReceipt)
        .values(event_id=event_id, user_id=user.id)
        .on_conflict_do_nothing(index_elements=["event_id", "user_id"])
    )
    db.commit()
    return TypeAdapter(OkResult).validate_python({"ok": True})


@router.post("/push-subscriptions", status_code=501, response_model=None)
def register_push(user: CurrentUser) -> NoReturn:
    raise HTTPException(
        501,
        detail={
            "code": "PUSH_NOT_CONFIGURED",
            "message": "Browser push is not configured. In-app notifications remain available.",
        },
    )
