"""Shared, typed FastAPI dependencies. Routers depend on `DbSession`/`CurrentUser`
rather than writing `Depends(...)` inline everywhere.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories import user_repository
from app.services.ml_recommendation_service import MLRecommendationService
from app.services.workout_recommendation_service import WorkoutRecommendationService

DbSession = Annotated[Session, Depends(get_db)]

# `auto_error=False` is deliberate: FastAPI's HTTPBearer otherwise raises a
# 403 when no credentials are supplied, which is the wrong status code for
# "you're not logged in" — `get_current_user` below raises our own
# `UnauthorizedError` (401) for that case instead, so missing and invalid
# tokens both produce the same, correct status code.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated.")

    user_id = decode_access_token(credentials.credentials)
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError("User not found.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_recommendation_service() -> WorkoutRecommendationService:
    """Constructs `WorkoutRecommendationService` with whichever engine
    `RECOMMENDATION_ENGINE` currently selects ("rule" or "ml").

    Resolved per-request via `Depends()` rather than as a module-level
    singleton (Phase 2.3) — this is what makes the environment variable
    switch actually take effect without any code change, and what makes it
    testable: each test builds its own `app` via the `app` fixture (which
    calls `get_settings.cache_clear()` first), so a test that sets
    `RECOMMENDATION_ENGINE=ml` before creating its client gets a real
    `MLRecommendationService`, and one that doesn't gets the original rule
    engine — no module reload or process restart required either way.

    Constructing either service here is cheap regardless of which engine is
    selected: `MLRecommendationService.__init__` doesn't load the model
    itself (that's deferred to `app.ml.registry`, cached at module level and
    loaded at most once per process) — it just builds a lightweight wrapper
    object, same as `WorkoutRecommendationService()` already was.
    """
    settings = get_settings()
    if settings.RECOMMENDATION_ENGINE == "ml":
        return WorkoutRecommendationService(engine=MLRecommendationService())
    return WorkoutRecommendationService()


RecommendationService = Annotated[WorkoutRecommendationService, Depends(get_recommendation_service)]
