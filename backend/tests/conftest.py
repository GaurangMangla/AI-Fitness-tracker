"""Shared test fixtures.

Sets test environment variables before any `app.*` module is imported, since
`Settings` validates `JWT_SECRET_KEY` the moment it's instantiated. Uses an
in-memory SQLite database for tests, isolated from the real `athlyt.db` file.
"""

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models  # noqa: F401  ensures every model is registered on Base.metadata
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import create_app


@pytest.fixture
def app() -> FastAPI:
    get_settings.cache_clear()
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db() -> Session:
    """A raw DB session for repository/service-level unit tests that don't
    need a full HTTP client. `create_all` is called here too (not just via
    the `app` fixture's lifespan) so tests using only this fixture work
    regardless of whether a `client`-fixture test has already run in this
    session — both calls are idempotent, so doing it twice is harmless.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
