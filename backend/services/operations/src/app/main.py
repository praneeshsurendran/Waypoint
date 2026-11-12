"""Waypoint API — app factory."""

from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from waypoint_observability import install

from app.core.config import get_settings
from app.api.routers import (
    auth,
    orders,
    plans,
    deferrals,
    loading,
    driver,
    reference,
    health,
    admin,
    analytics,
    people,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("waypoint")


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app):
        if settings.seed_on_start:
            from seed.run import main as seed_main

            await asyncio.to_thread(seed_main)
        try:
            yield
        finally:
            from app.bootstrap import shutdown

            shutdown()

    app = FastAPI(
        lifespan=lifespan,
        title="Waypoint API",
        description="Delivery planning system for a Sri Lankan retail group.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    install(app)

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID"],
    )

    # --- Standard error handler ---
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
            },
        )

    # --- Routers ---
    prefix = "/api/v1"
    app.include_router(health.router)  # /health (no prefix)
    if settings.service_mode == "legacy":
        app.include_router(auth.router, prefix=prefix)  # /api/v1/auth/...
    if settings.service_mode == "legacy":
        app.include_router(reference.router, prefix=prefix)  # /api/v1/reference/...
    app.include_router(orders.router, prefix=prefix)  # /api/v1/orders/...
    app.include_router(plans.router, prefix=prefix)  # /api/v1/plans/...
    app.include_router(deferrals.router, prefix=prefix)  # /api/v1/deferrals/...
    app.include_router(loading.router, prefix=prefix)  # /api/v1/loading/...
    app.include_router(driver.router, prefix=prefix)  # /api/v1/driver/...
    app.include_router(admin.router, prefix=prefix)  # /api/v1/admin/...
    if settings.service_mode == "legacy":
        app.include_router(people.router, prefix=prefix)
    else:
        from fastapi import APIRouter

        audit_router = APIRouter()
        for route in people.router.routes:
            if route.path == "/admin/audit":
                audit_router.routes.append(route)
        app.include_router(audit_router, prefix=prefix)
    # app.include_router(people.router, prefix=prefix)            # /api/v1/admin/users, outlets, vehicles, audit
    app.include_router(analytics.router, prefix=prefix)  # /api/v1/analytics/...

    from app.api.routers import jobs, proofs

    app.include_router(jobs.router, prefix=prefix)
    app.include_router(proofs.router)
    return app


app = create_app()
