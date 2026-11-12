from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.api.deps import DbDep

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
def health():
    return {"status": "ok", "service": "waypoint-operations"}


@router.get("/health/db")
@router.get("/health/ready")
def ready(db: DbDep):
    try:
        db.execute(text("SELECT 1"))
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if int(revision.split("_")[0]) < 6:
            raise RuntimeError("Migrations are incomplete")
        return {"status": "ready", "db": "connected"}
    except Exception:
        raise HTTPException(
            503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database unavailable."}
        ) from None
