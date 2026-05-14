"""Alembic environment configuration for Athlyt.

Supports both synchronous SQLite (dev/test) and PostgreSQL (production)
through the DATABASE_URL environment variable — same as the application.

Key design decisions:
- Imports `app.models` (the package) to register every ORM model on
  `Base.metadata` before autogenerate runs, so Alembic sees all tables.
- Reads DATABASE_URL from the application's Settings (pydantic-settings)
  rather than from alembic.ini, so there is exactly one place where the
  database URL lives.
- `render_as_batch=True` enables ALTER TABLE support under SQLite (SQLite
  does not support ADD COLUMN / DROP COLUMN natively; batch mode rewrites
  the table). This is a no-op under PostgreSQL — safe to leave on always.
- `compare_type=True` makes autogenerate detect column type changes, not
  just add/drop columns. Useful when an enum gains a value.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Bootstrap — must happen BEFORE any app.* import so pydantic-settings reads
# the correct environment variables.  In production the real env vars are
# set in the deployment environment; here we just ensure the test sentinel
# is present when someone runs `alembic` locally without a .env file.
# ---------------------------------------------------------------------------
os.environ.setdefault("JWT_SECRET_KEY", "alembic-dev-placeholder-32-chars-min-xx")

# ---------------------------------------------------------------------------
# Import app modules — ORDER MATTERS
# 1. settings (reads DATABASE_URL)
# 2. models package (registers every model on Base.metadata)
# 3. Base (provides target_metadata)
# ---------------------------------------------------------------------------
from app import models as _models_import  # noqa: F401,E402 — side-effect import
from app.core.config import get_settings
from app.db.base import Base

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to alembic.ini values.
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the sqlalchemy.url in alembic.ini with the value from Settings,
# so there is a single source of truth for the database URL.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# All models must be reflected in target_metadata for autogenerate to work.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Helper: is the current URL pointing at SQLite?
# ---------------------------------------------------------------------------
def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


# ---------------------------------------------------------------------------
# Offline mode — generates SQL without a live DB connection.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Useful for generating a SQL script to review before applying,
    or for environments without direct DB access.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite(url),
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — runs migrations against a live database connection.
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode (the normal path for `alembic upgrade`)."""
    url = config.get_main_option("sqlalchemy.url")

    # For in-memory SQLite (used in tests), use StaticPool so all connections
    # share the same in-memory database — same reasoning as session.py.
    is_memory = url == "sqlite:///:memory:"
    connect_args = {"check_same_thread": False} if _is_sqlite(url) else {}

    extra_kwargs: dict = {}
    if is_memory:
        from sqlalchemy.pool import StaticPool

        extra_kwargs["poolclass"] = StaticPool
        extra_kwargs["connect_args"] = connect_args
    elif _is_sqlite(url):
        extra_kwargs["connect_args"] = connect_args

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        **extra_kwargs,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_is_sqlite(url),
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
