# ── Stage 1: Builder ───────────────────────────────────────────────────────
# Install all Python dependencies into an isolated prefix so the runtime
# image doesn't need build tools (gcc, pip, etc.).
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies for packages that compile C extensions
# (psycopg2-binary ships its own libpq, so no libpq-dev needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only the dependency manifest first — Docker layer-caches this step
# until pyproject.toml changes, so a code-only change doesn't re-install deps.
COPY pyproject.toml README.md ./
# Minimal stub so hatchling can build the editable install
RUN mkdir -p app && touch app/__init__.py

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .


# ── Stage 2: Runtime ───────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN useradd --create-home --shell /bin/bash athlyt

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (all layers below this are code-change sensitive)
COPY --chown=athlyt:athlyt . .

USER athlyt

# Expose the API port
EXPOSE 8000

# Health check — polls the liveness endpoint every 30s
# Start period gives time for `alembic upgrade head` to complete before
# Docker starts counting failures.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" \
    || exit 1

# Entrypoint: run migrations then start the server.
# `alembic upgrade head` is idempotent — safe to run on every container start.
# If the migration fails the container exits before uvicorn starts,
# making the issue immediately visible in logs.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]

