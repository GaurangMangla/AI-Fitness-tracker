"""Application logging configuration.

Design decision: Python's standard `logging` module, configured once at
startup via `dictConfig`, not a third-party library (structlog, loguru).
For a project this size, stdlib logging covers everything needed — JSON-ish
structured fields via a custom formatter, correct log levels per environment,
and every platform (Render, Railway, Fly.io, Docker) captures stdout/stderr
automatically, so there's no log-shipping infrastructure to configure here.

Log level policy:
  - `local` / `test`: DEBUG — verbose, since you're staring at the terminal.
  - `production`: INFO — request-level events and errors, not every SQL
    query (`echo=settings.DEBUG` in `db/session.py` already keys SQL logging
    off DEBUG specifically, independent of this).

Nothing sensitive is ever logged: no passwords, no JWTs, no full request
bodies. Exception log entries include the exception message and traceback
(needed to debug production issues) but never re-log request payloads.
"""

import logging
import logging.config
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Call once, at application startup (see `app/main.py`)."""
    settings = get_settings()
    level = "DEBUG" if settings.ENVIRONMENT in ("local", "test") else "INFO"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": sys.stdout,
                },
            },
            "root": {
                "level": level,
                "handlers": ["console"],
            },
            "loggers": {
                # Uvicorn's own loggers ship with `propagate=False` and their
                # own handlers by default — override both so they use our
                # formatting/level instead of uvicorn's defaults, without
                # double-logging through root.
                "uvicorn": {"level": level, "handlers": ["console"], "propagate": False},
                "uvicorn.error": {"level": level, "handlers": ["console"], "propagate": False},
                "uvicorn.access": {"level": level, "handlers": ["console"], "propagate": False},
                # SQLAlchemy's engine logger is controlled separately by
                # `echo=settings.DEBUG` in db/session.py — leave it at
                # WARNING here so it doesn't double-log when DEBUG is off.
                "sqlalchemy.engine": {"level": "WARNING", "propagate": False},
                # Deliberately NOT listing "app" here: every `app.*` logger
                # (get_logger(__name__) in any module under app/) has no
                # handlers of its own, so it propagates straight up to root
                # — which already has the "console" handler at the right
                # level. This is what lets pytest's `caplog` fixture (which
                # attaches to root) actually see records from app code in
                # tests, and it avoids a second, easy-to-miss duplicate-log
                # bug that setting handlers at both "app" and root would
                # otherwise cause.
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — `get_logger(__name__)` in any module."""
    return logging.getLogger(name)
