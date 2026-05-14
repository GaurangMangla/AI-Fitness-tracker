"""Database engine and session management.

Supports both SQLite (local dev / tests) and PostgreSQL (production) from
the same codebase — the DATABASE_URL environment variable selects the backend.

SQLite-specific behaviour:
  - `check_same_thread=False` is required because FastAPI's threadpool can
    serve a request on a different OS thread than the one that opened the
    connection. This arg is silently ignored by all non-SQLite drivers.
  - StaticPool forces in-memory SQLite to share one connection across all
    threads, so tables created at startup are visible to request handlers.
    Only activated for `sqlite:///:memory:` URLs (i.e. tests).

PostgreSQL-specific behaviour:
  - Pool size and overflow are tuned for a typical small production deployment.
    Adjust `SQLALCHEMY_POOL_SIZE` / `SQLALCHEMY_MAX_OVERFLOW` env vars if
    running under high concurrency or with a PgBouncer in front.
  - `pool_pre_ping=True` silently drops and re-establishes stale connections,
    which prevents "server closed the connection unexpectedly" errors after
    the database has been idle for a while (common on Render/Railway free tiers
    that idle the database after 5 minutes).
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_is_in_memory = _is_sqlite and ":memory:" in settings.DATABASE_URL

_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_pool_kwargs: dict = {"poolclass": StaticPool} if _is_in_memory else {}

# PostgreSQL connection pool tuning — only applied for non-SQLite URLs.
# pool_pre_ping reconnects after idle periods, preventing stale connection
# errors common on free-tier databases (Render, Railway, Supabase, etc.).
if not _is_sqlite:
    _pool_kwargs.update(
        {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
            "pool_recycle": 300,  # recycle connections every 5 min
        }
    )

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=settings.DEBUG,
    **_pool_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session scoped to one request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Used by the health check endpoint."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
