import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from waypoint_observability import install
from waypoint_notifications.bootstrap import SessionLocal
from waypoint_notifications.api.v1.routers import notifications


def create_app():
    from contextlib import asynccontextmanager
    from waypoint_notifications.bootstrap import engine

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Waypoint notifications", version="0.2.0", lifespan=lifespan)
    origins = [
        v.strip()
        for v in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if v.strip()
    ]
    if "*" in origins:
        raise ValueError("Explicit CORS origins are required")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID"],
    )
    install(app)
    app.include_router(notifications.router, prefix="/api/v1")

    @app.get("/health/live")
    def live():
        return {"status": "ok", "service": "notifications"}

    @app.get("/health/ready")
    def ready():
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
                revision = db.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                if int(revision.split("_")[0]) < 1:
                    raise RuntimeError("Migrations are incomplete")
            return {"status": "ready"}
        except Exception:
            raise HTTPException(
                503,
                detail={
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Database unavailable.",
                },
            ) from None

    return app


app = create_app()
