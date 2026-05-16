"""Global exception handlers.

Design decision: errors return `{"detail": "<message>"}` — the same shape
FastAPI's own `HTTPException` already uses — rather than a custom nested
envelope (`{"error": {"code": ..., "message": ...}}`). For a small frontend
that controls both ends of the API, the extra structure isn't pulling its
weight yet; this is the simplest thing that works, and it's a five-minute
change later if the API grows enough consumers to need machine-readable error
codes.

Important: registering a custom handler for the bare `Exception` class
replaces Starlette's default `ServerErrorMiddleware`, which is what normally
logs the traceback for unhandled exceptions. Without `logger.exception(...)`
below, every unhandled 500 in production would be completely silent — no
traceback, no indication anything went wrong, anywhere in the logs. This was
fixed as part of production-readiness hardening (Phase 1.4).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle every expected, typed domain exception (see `app/core/exceptions.py`).

    Logged at INFO, not ERROR — these are expected outcomes (a 404, a 409
    conflict, a validation failure), not bugs. Useful for traffic visibility
    without polluting error-level alerting.
    """
    logger.info(
        "%s: %s [%s %s]",
        exc.__class__.__name__,
        exc.message,
        request.method,
        request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for anything unexpected — i.e. a bug.

    `logger.exception(...)` captures the full traceback at ERROR level.
    Never leaks internals (stack traces, file paths) into the HTTP response
    itself — the client only ever sees the generic message below.
    """
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
