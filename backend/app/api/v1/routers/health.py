"""Health check endpoint — confirms the API is running and the database is
reachable. Used to sanity-check local setup and, later, deployment."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.db.session import check_database_connection
from app.ml import registry

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(database_healthy: Annotated[bool, Depends(check_database_connection)]) -> dict:
    settings = get_settings()
    return {
        "status": "ok" if database_healthy else "degraded",
        "version": settings.APP_VERSION,
        "database": "healthy" if database_healthy else "unhealthy",
    }


@router.get("/health/detailed")
def health_check_detailed(
    database_healthy: Annotated[bool, Depends(check_database_connection)],
) -> dict:
    """Extended health check with environment and dependency info.
    Useful for debugging production issues without SSH access.

    The `recommendation_engine` block (which engine is configured, whether
    the ML model actually loaded, its version) is only included when
    `DEBUG=true` — this is internal diagnostic information about the
    system's configuration and current state, not something every caller
    of a public health endpoint should see by default. The base fields
    above (status, version, database) remain always visible regardless,
    since they carry no comparable internal detail.
    """
    import sys

    settings = get_settings()
    response: dict = {
        "status": "ok" if database_healthy else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "healthy" if database_healthy else "unhealthy",
        "python_version": sys.version.split()[0],
    }

    if settings.DEBUG:
        # get_status() reads whatever's already been loaded (or not) by
        # prior requests — it deliberately never triggers a fresh load
        # attempt itself, so checking health can't itself cause a slow
        # cold-start model load or report a state that doesn't reflect
        # real production traffic. See app/ml/registry.py.
        ml_status = registry.get_status()
        response["recommendation_engine"] = {
            "configured_engine": settings.RECOMMENDATION_ENGINE,
            "ml_model_loaded": ml_status["loaded"],
            "ml_model_version": ml_status["model_version"],
            "ml_load_attempted": ml_status["attempted"],
            "ml_load_error": ml_status["error"],
            "ml_confidence_threshold": settings.ML_CONFIDENCE_THRESHOLD,
        }
    else:
        response["recommendation_engine"] = "not available (DEBUG=false)"

    return response
