"""Security response headers middleware.

Mirrors the headers already set on the frontend (see `frontend/next.config.ts`)
so API responses get the same baseline protection, since the API is a
separate origin some clients may hit directly (e.g. Swagger UI, curl,
mobile apps added later) rather than only through the Next.js frontend.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Not HSTS'd unconditionally here — that's a hosting-platform concern
        # (Render/Railway/Vercel all terminate TLS in front of the app and
        # typically add Strict-Transport-Security themselves). Adding it here
        # too is harmless but redundant; left out to avoid conflicting values.
        return response
