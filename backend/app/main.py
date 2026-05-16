"""Application factory.

Database schema management strategy:
- PRODUCTION / STAGING: Alembic is the sole source of truth for the schema.
  `alembic upgrade head` must be run as a pre-deploy step before starting the
  server. The application itself never calls `create_all()` in production.
- LOCAL DEVELOPMENT (SQLite): `create_all()` still runs at startup for
  convenience, so developers can `uvicorn app.main:app --reload` without
  running a migration command first. Controlled by ENVIRONMENT=local.
- TESTS: `conftest.py` calls `create_all()` directly against an in-memory
  SQLite database — tests must never depend on Alembic.

Middleware order (registered outer-to-inner, so requests pass through in
this order, responses in reverse):
  1. TrustedHostMiddleware  — rejects requests with an unrecognised Host
     header before any other processing happens.
  2. SecurityHeadersMiddleware — adds baseline security headers to every
     response.
  3. CORSMiddleware — handles preflight and cross-origin headers.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import models  # noqa: F401 — side-effect: registers every model on Base.metadata
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging_config import configure_logging, get_logger
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.base import Base
from app.db.seed_exercises import seed_exercises
from app.db.session import SessionLocal, engine

logger = get_logger(__name__)


def _run_local_dev_schema() -> None:
    """In local development and tests only, create any missing tables via
    create_all(). Convenience shortcut so `uvicorn app.main:app --reload`
    works without running `alembic upgrade head` first. NEVER called in
    production — Alembic handles production schema.
    """
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    if settings.ENVIRONMENT in ("local", "test"):
        _run_local_dev_schema()

    with SessionLocal() as db:
        seed_exercises(db)

    logger.info(
        "Athlyt API started — environment=%s, version=%s",
        settings.ENVIRONMENT,
        settings.APP_VERSION,
    )

    yield

    logger.info("Athlyt API shutting down")


def create_app() -> FastAPI:
    # Logging must be configured before anything else logs — including the
    # lifespan startup message above and every request the app handles.
    configure_logging()

    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
