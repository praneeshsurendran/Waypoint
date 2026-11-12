from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from waypoint_security import Principal, verified_principal
from waypoint_notifications.bootstrap import get_db
from waypoint_notifications.infrastructure.db.notifications import (
    Notification,
    ReadReceipt,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])
CurrentUser = Annotated[Principal, Depends(verified_principal)]


def scoped(query, user):
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
    return query


@router.get("")
def list_notifications(
    user: CurrentUser,
    db=Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    rows = db.scalars(
        scoped(select(Notification), user)
        .order_by(Notification.created_at.desc(), Notification.event_id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": row.event_id,
            "type": row.event_type,
            "data": row.payload,
            "created_at": row.created_at,
            "read": db.get(ReadReceipt, (row.event_id, user.id)) is not None,
        }
        for row in rows
    ]


@router.post("/{event_id}/read")
def mark_read(event_id: str, user: CurrentUser, db=Depends(get_db)):
    row = db.scalar(
        scoped(select(Notification).where(Notification.event_id == event_id), user)
    )
    if row is None:
        raise HTTPException(
            404, detail={"code": "NOT_FOUND", "message": "Notification not found."}
        )
    if db.get(ReadReceipt, (event_id, user.id)) is None:
        db.add(ReadReceipt(event_id=event_id, user_id=user.id))
    db.commit()
    return {"ok": True}


@router.post("/push-subscriptions", status_code=501)
def register_push(user: CurrentUser):
    raise HTTPException(
        501,
        detail={
            "code": "PUSH_NOT_CONFIGURED",
            "message": "Browser push is not configured. In-app notifications remain available.",
        },
    )
