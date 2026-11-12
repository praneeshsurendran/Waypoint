from pydantic import TypeAdapter
from waypoint_contracts.runtime import LiveHealth, ReadyHealth
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.api.deps import DbDep

router = APIRouter(tags=["health"])


@router.get("/health", response_model=LiveHealth)
@router.get("/health/live", response_model=LiveHealth)
def health() -> LiveHealth:
    return TypeAdapter(LiveHealth).validate_python(
        {"status": "ok", "service": "waypoint-operations"}
    )


@router.get("/health/db", response_model=ReadyHealth)
@router.get("/health/ready", response_model=ReadyHealth)
def ready(db: DbDep) -> ReadyHealth:
    try:
        db.execute(text("SELECT 1"))
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if int(revision.split("_")[0]) < 6:
            raise RuntimeError("Migrations are incomplete")
        return TypeAdapter(ReadyHealth).validate_python({"status": "ready", "db": "connected"})
    except Exception:
        raise HTTPException(
            503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database unavailable."}
        ) from None
