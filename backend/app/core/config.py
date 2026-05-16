"""Application configuration.

Design decision: SQLite by default (`sqlite:///./athlyt.db`), via a plain
synchronous `DATABASE_URL` — not async SQLAlchemy with asyncpg. For a one-week
solo project, async SQLAlchemy buys nothing: FastAPI already runs sync
dependency functions in a threadpool, so request handling doesn't block, and
we skip an entire category of async-specific setup (async engine config, async
Alembic environments, async session lifecycle edge cases) that has no payoff at
this scale. Switching to Postgres later is a one-line `DATABASE_URL` change
plus `pip install psycopg2-binary` — see `app/db/session.py` for why the rest
of the data layer doesn't need to change.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, type-validated app settings, loaded from environment
    variables (and a local `.env` file in development — see `.env.example`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    APP_NAME: str = "Athlyt API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["local", "test", "production"] = "local"
    DEBUG: bool = False

    # --- API -----------------------------------------------------------------
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    # Hostnames this API will accept requests for, checked against the `Host`
    # header — mitigates Host header injection attacks (cache poisoning,
    # password-reset link poisoning). "*" (any host) is fine in local dev;
    # production should list only the actual API domain(s), e.g.
    # "athlyt-api.onrender.com". Comma-separated, same NoDecode handling as
    # CORS_ORIGINS above.
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])

    # --- Database --------------------------------------------------------------
    # SQLite for local dev; swap to a `postgresql://...` URL for production —
    # the ORM models and queries don't change either way.
    DATABASE_URL: str = "sqlite:///./athlyt.db"

    # --- Auth / JWT --------------------------------------------------------------
    # A single access token, not access+refresh rotation — the right call for a
    # one-week MVP. Refresh-token rotation (revocable sessions, "log out
    # everywhere") is a real feature with real value, but it's additional
    # surface area this scope doesn't need yet; the auth module is small enough
    # to extend with it later without a rewrite if the project grows past the
    # placement-portfolio stage.
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- ML ----------------------------------------------------------------------
    # Path to the trained workout-recommendation model, exported from
    # `ml/notebooks/train_model.ipynb` (see ml/ML_TRAINING.md). Model and
    # preprocessor are saved as two separate .joblib files — see
    # docs/ML_INTEGRATION.md for why they're loaded separately rather than
    # bundled into one artifact.
    ML_MODEL_PATH: str = "../ml/models/model.joblib"
    ML_PREPROCESSOR_PATH: str = "../ml/models/preprocessor.joblib"

    # Which recommendation engine actually serves POST /workouts/recommend:
    #   "ml"   — MLRecommendationService (default, as of the production
    #            rollout) — internally falls back to RuleBasedRecommendationEngine
    #            on any failure or low-confidence prediction, so this is safe
    #            to run as the default: every failure mode still produces a
    #            normal, correct rule-based recommendation, just logged
    #            differently. See docs/ML_INTEGRATION.md for the full
    #            fallback design and the rollout's validation results.
    #   "rule" — RuleBasedRecommendationEngine only, no ML involved at all.
    #            Set this to instantly and completely disable the ML path —
    #            e.g. to roll back a bad deploy — with zero code changes,
    #            just an environment variable change and a restart.
    RECOMMENDATION_ENGINE: Literal["rule", "ml"] = "ml"

    # Below this predict_proba() confidence, MLRecommendationService discards
    # the ML prediction and defers to the rule engine instead — an uncertain
    # ML guess is treated as no better than not having one. 0.6 is a
    # deliberately conservative starting point (well above "just barely more
    # likely than random" for a 5-class problem, where a coin-flip baseline
    # is 0.2) — tune based on real production confidence distributions once
    # there's traffic to observe.
    ML_CONFIDENCE_THRESHOLD: float = 0.6

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — parsed once per process."""
    return Settings()
