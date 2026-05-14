"""SQLAlchemy declarative base and shared mixins.

No business models live here yet — that starts with the `User` model in
Feature 1. `Base` and the mixins below exist now so every future model gets a
consistent, Postgres-portable primary key and timestamp strategy for free.

Design decision: primary keys are UUIDs stored as `String(36)`, not SQLAlchemy's
native UUID type or an auto-incrementing integer. SQLite has no native UUID
column type, so using one would mean the schema *looks* portable but actually
isn't — `String(36)` works identically on SQLite and Postgres, which is what
"keep the database layer compatible with PostgreSQL" actually requires in
practice. IDs are generated in Python (`uuid.uuid4()`), not by the database, so
the same code works unchanged on either backend.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model."""


class UUIDPrimaryKeyMixin:
    """Gives a model a UUID-as-string primary key column named `id`."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


class TimestampMixin:
    """Gives a model `created_at`/`updated_at` columns, set by the database
    itself rather than application code."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
