from sqlalchemy.orm import Session
from fastapi import UploadFile
from waypoint_security import Actor
from waypoint_contracts.runtime import UploadResult
import hashlib
import uuid
from fastapi import HTTPException
from app.core.config import get_settings
from app.infrastructure.messaging.models import ProofObject
from app.bootstrap import proof_storage as storage
from app.application.use_cases.delivery import authorize_trip
from app.infrastructure.db.models.plan import Trip, Stop

TYPES = {
    "image/jpeg": (".jpg", lambda b: b.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda b: b.startswith(b"RIFF") and b[8:12] == b"WEBP"),
}


def upload(db: Session, user: Actor, file: UploadFile, stop_id: str | None) -> UploadResult:
    if file.content_type not in TYPES:
        raise HTTPException(
            415,
            detail={"code": "INVALID_CONTENT_TYPE", "message": "Use JPEG, PNG or WebP evidence."},
        )
    stop = None
    if stop_id is not None:
        try:
            stop = db.get(Stop, int(stop_id))
        except ValueError:
            raise HTTPException(
                422, detail={"code": "INVALID_STOP", "message": "Invalid stop ID."}
            ) from None
        if not stop:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Stop not found."})
        authorize_trip(db, db.get(Trip, stop.trip_id), user)
    elif user.role == "DRIVER":
        trip = (
            db.query(Trip)
            .filter(Trip.vehicle_id == user.vehicle_id, Trip.status.in_(["LOADED", "IN_TRANSIT"]))
            .first()
            if user.vehicle_id
            else None
        )
        if not trip:
            raise HTTPException(
                403, detail={"code": "FORBIDDEN", "message": "An assigned active trip is required."}
            )
    elif user.role == "LOADER" and not user.depot_id:
        raise HTTPException(
            403, detail={"code": "FORBIDDEN", "message": "A depot assignment is required."}
        )
    content = file.file.read(get_settings().max_upload_bytes + 1)
    if not content or len(content) > get_settings().max_upload_bytes:
        raise HTTPException(
            413,
            detail={
                "code": "INVALID_UPLOAD_SIZE",
                "message": "Evidence exceeds the upload limit or is empty.",
            },
        )
    extension, valid = TYPES[file.content_type]
    if not valid(content):
        raise HTTPException(
            415,
            detail={
                "code": "INVALID_IMAGE",
                "message": "File contents do not match the image type.",
            },
        )
    key = str(uuid.uuid4()) + extension
    storage().put(key, content, file.content_type)
    db.add(
        ProofObject(
            key=key,
            owner_id=user.id,
            stop_id=stop.id if stop else None,
            content_type=file.content_type,
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
    )
    db.commit()
    return UploadResult(path="/uploads/" + key)


def authorize_proof(db: Session, proof: ProofObject, user: Actor) -> None:
    if proof.owner_id == user.id or user.role in ("DISPATCHER", "ADMIN"):
        return
    if proof.stop_id is not None:
        stop = db.get(Stop, proof.stop_id)
        if stop is None:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Delivery not found."})
        if user.role == "STORE_MANAGER" and user.outlet_id == stop.outlet_id:
            return
        if user.role in ("DRIVER", "LOADER"):
            authorize_trip(db, db.get(Trip, stop.trip_id), user)
            return
    raise HTTPException(
        403, detail={"code": "FORBIDDEN", "message": "Evidence belongs to another delivery."}
    )
