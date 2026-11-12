"""Request correlation without logging credentials or request payloads."""

from fastapi import FastAPI, Request
from starlette.responses import Response
from starlette.middleware.base import RequestResponseEndpoint

import json
import logging
import re
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

traceparent: ContextVar[str | None] = ContextVar("traceparent", default=None)
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="background")


def install(app: FastAPI) -> None:
    from waypoint_runtime import install as protect

    protect(app)
    logger = logging.getLogger("waypoint.http")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    @app.middleware("http")
    async def correlate(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        candidate = request.headers.get("x-correlation-id", "")
        value = (
            candidate
            if re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", candidate)
            else str(uuid4())
        )
        token = correlation_id.set(value)
        incoming = request.headers.get("traceparent", "")
        parent = (
            incoming
            if re.fullmatch(r"00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}", incoming)
            else f"00-{uuid4().hex}-{uuid4().hex[:16]}-01"
        )
        trace_token = traceparent.set(parent)
        started = time.monotonic()
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = value
            response.headers["traceparent"] = parent
            logging.getLogger("waypoint.http").info(
                json.dumps(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "correlation_id": value,
                        "traceparent": parent,
                        "method": request.method,
                        "status": response.status_code,
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    }
                )
            )
            return response
        finally:
            correlation_id.reset(token)
            traceparent.reset(trace_token)
