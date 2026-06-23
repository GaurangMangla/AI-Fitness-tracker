"""Tests for `GET /api/v1/health`."""

from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "healthy"
    assert "version" in body


def test_health_detailed_hides_recommendation_engine_info_when_debug_false(
    client: TestClient, monkeypatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()

    response = client.get("/api/v1/health/detailed")

    assert response.status_code == 200
    body = response.json()
    assert body["recommendation_engine"] == "not available (DEBUG=false)"

    get_settings.cache_clear()


def test_health_detailed_shows_recommendation_engine_info_when_debug_true(
    client: TestClient, monkeypatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()

    response = client.get("/api/v1/health/detailed")

    assert response.status_code == 200
    body = response.json()
    engine_info = body["recommendation_engine"]
    assert isinstance(engine_info, dict)
    assert "configured_engine" in engine_info
    assert "ml_model_loaded" in engine_info
    assert "ml_model_version" in engine_info
    assert "ml_confidence_threshold" in engine_info

    get_settings.cache_clear()


def test_health_detailed_never_exposes_secrets_or_stack_traces(
    client: TestClient, monkeypatch
) -> None:
    """Even in debug mode, the health check must never leak anything
    sensitive — no JWT_SECRET_KEY, no DATABASE_URL with credentials, no raw
    Python tracebacks."""
    from app.core.config import get_settings

    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()

    response = client.get("/api/v1/health/detailed")
    body_text = response.text.lower()

    assert "jwt_secret_key" not in body_text
    assert "traceback" not in body_text
    assert "secret" not in body_text

    get_settings.cache_clear()
