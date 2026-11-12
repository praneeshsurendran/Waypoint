"""Shared request protections and lifecycle wiring; no business state or ORM entities."""

from fastapi import FastAPI, Request
from starlette.responses import Response
from starlette.middleware.base import RequestResponseEndpoint

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    TimeoutError as DatabaseTimeout,
)
from starlette.concurrency import run_in_threadpool
from .rate_limit import Category, category_for, client_address, enforce
from .redis_client import close_redis
from .settings import settings

logger = logging.getLogger("waypoint.runtime")


def install(app: FastAPI) -> None:
    from waypoint_contracts.common import HttpErrorResponse

    app.router.responses.update(
        {
            code: {"model": HttpErrorResponse}
            for code in (400, 401, 403, 404, 409, 413, 415, 422, 429, 503)
        }
    )
    settings()  # Fail invalid production configuration at startup, not on a first request.
    previous = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(instance: FastAPI) -> AsyncIterator[None]:
        try:
            async with previous(instance):
                yield
        finally:
            close_redis()
            from waypoint_security import close_identity_client

            close_identity_client()

    app.router.lifespan_context = lifespan

    @app.middleware("http")
    async def protect(request: Request, call_next: RequestResponseEndpoint) -> Response:
        response: Response
        if (
            request.method != "OPTIONS"
            and not request.url.path.startswith("/health")
            and request.url.path not in ("/openapi.json", "/docs", "/redoc")
        ):
            category: Category = (
                "login" if category_for(request) == "login" else "client"
            )
            try:
                await run_in_threadpool(
                    enforce, request, "ip:" + client_address(request), category
                )
            except HTTPException as error:
                response = JSONResponse(
                    status_code=error.status_code,
                    content={"detail": error.detail},
                    headers=error.headers,
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith(("/api/", "/uploads/")):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        # Preserve FastAPI's existing detail-array contract without echoing passwords or private input.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
                    for item in error.errors()
                ]
            },
        )

    @app.exception_handler(IntegrityError)
    async def conflict(request: Request, error: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "code": "DATA_CONFLICT",
                    "message": "The requested change conflicts with existing data.",
                }
            },
        )

    async def unavailable(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "1"},
            content={
                "detail": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Database temporarily unavailable.",
                }
            },
        )

    app.add_exception_handler(OperationalError, unavailable)
    app.add_exception_handler(DatabaseTimeout, unavailable)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception) -> JSONResponse:
        # SQL/AWS exceptions can contain parameters; log type and correlation separately, never repr(error).
        logger.error("Unhandled request error (%s)", type(error).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                }
            },
        )
