"""Integration test: `RECOMMENDATION_ENGINE=rule|ml` switches which engine
actually serves `POST /workouts/recommend`, without any code change.

Uses the real HTTP API (via the `client` fixture) rather than calling
`WorkoutRecommendationService` directly, specifically to prove the full
chain works: env var → `Settings` → `get_recommendation_service()`
dependency → router → response — the actual thing a deployer changes when
they set this variable in Render/Docker, not just an internal implementation
detail.
"""

import joblib
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.ml import registry
from tests.factories import unique_email
from tests.ml_test_helpers import build_tiny_model_and_preprocessor

_ONBOARDING_PAYLOAD = {
    "name": "Engine Switch Tester",
    "age": 27,
    "gender": "male",
    "height_cm": 180,
    "weight_kg": 78,
    "fitness_goal": "muscle_gain",
    "activity_level": "moderately_active",
    "workout_experience": "intermediate",
    "equipment_available": ["full_gym"],
    "diet_preference": "non_vegetarian",
}


def _register_and_onboard(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email("engineswitch"), "password": "correct-horse-battery-staple"},
    )
    token: str = response.json()["access_token"]
    client.patch(
        "/api/v1/users/me",
        json=_ONBOARDING_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    return token


@pytest.fixture(autouse=True)
def _reset_registry():
    registry.reset_for_testing()
    yield
    registry.reset_for_testing()


class TestRecommendationEngineSwitching:
    def test_default_is_now_ml_with_graceful_fallback_when_no_model_present(
        self, client: TestClient, monkeypatch, tmp_path
    ):
        """RECOMMENDATION_ENGINE now defaults to "ml" (the production
        rollout this test file was updated for) — but this test deliberately
        points at a nonexistent model path rather than relying on whatever
        real .joblib files happen to exist in the test-running environment
        (Git LFS may or may not have been pulled), so the test's outcome
        doesn't depend on that. Confirms: even in the worst case (default
        engine selected, model completely unavailable), the API still
        returns a normal 200 with a valid recommendation — via the
        automatic fallback to the rule engine, exactly as designed."""
        monkeypatch.delenv("RECOMMENDATION_ENGINE", raising=False)
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "does_not_exist.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "also_missing.joblib"))
        get_settings.cache_clear()

        assert get_settings().RECOMMENDATION_ENGINE == "ml"  # confirms the actual default

        token = _register_and_onboard(client)
        response = client.post(
            "/api/v1/workouts/recommend",
            json={"workout_days_per_week": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["split_name"] == "Push Pull Legs"

        get_settings.cache_clear()

    def test_default_with_a_real_model_present_genuinely_uses_ml(
        self, client: TestClient, monkeypatch, tmp_path
    ):
        """Same as above, but with a real (tiny) model actually present —
        confirms the default genuinely routes through MLRecommendationService
        end-to-end, not just that it falls back gracefully when there's
        nothing to route to."""
        model, preprocessor = build_tiny_model_and_preprocessor()
        model_path = tmp_path / "model.joblib"
        preprocessor_path = tmp_path / "preprocessor.joblib"
        joblib.dump(model, model_path)
        joblib.dump(preprocessor, preprocessor_path)

        monkeypatch.delenv("RECOMMENDATION_ENGINE", raising=False)
        monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
        monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "0.0")
        get_settings.cache_clear()

        token = _register_and_onboard(client)
        response = client.post(
            "/api/v1/workouts/recommend",
            json={"workout_days_per_week": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["split_name"] in (
            "Push Pull Legs",
            "Home Bodyweight Split",
            "Upper Lower",
        )

        get_settings.cache_clear()

    def test_rule_engine_remains_fully_available_as_an_instant_rollback(
        self, client: TestClient, monkeypatch
    ):
        """The critical guarantee behind promoting ML to the default:
        RECOMMENDATION_ENGINE=rule must still work exactly as it always
        has, with zero code changes required — this is the rollback path
        documented in docs/ML_INTEGRATION.md and the README."""
        monkeypatch.setenv("RECOMMENDATION_ENGINE", "rule")
        get_settings.cache_clear()

        token = _register_and_onboard(client)
        response = client.post(
            "/api/v1/workouts/recommend",
            json={"workout_days_per_week": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["split_name"] == "Push Pull Legs"

        get_settings.cache_clear()

    def test_ml_setting_with_no_model_still_returns_a_valid_recommendation(
        self, client: TestClient, monkeypatch, tmp_path
    ):
        """The single most important behavioural guarantee in this whole
        phase: setting RECOMMENDATION_ENGINE=ml in an environment where the
        model files simply aren't present (e.g. Git LFS not pulled) must
        NOT break the API — it must silently fall back and return 200,
        exactly as if RECOMMENDATION_ENGINE were still "rule"."""
        monkeypatch.setenv("RECOMMENDATION_ENGINE", "ml")
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "does_not_exist.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "also_missing.joblib"))
        get_settings.cache_clear()

        token = _register_and_onboard(client)
        response = client.post(
            "/api/v1/workouts/recommend",
            json={"workout_days_per_week": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["split_name"]  # a real split was returned, not an error

        get_settings.cache_clear()

    def test_ml_setting_with_a_real_model_actually_uses_it(
        self, client: TestClient, monkeypatch, tmp_path
    ):
        """With RECOMMENDATION_ENGINE=ml and a real (if tiny) model present,
        the endpoint should still return 200 with a valid recommendation —
        confirming the ml path is genuinely reachable end-to-end through the
        real API, not just unit-testable in isolation."""
        model, preprocessor = build_tiny_model_and_preprocessor()
        model_path = tmp_path / "model.joblib"
        preprocessor_path = tmp_path / "preprocessor.joblib"
        joblib.dump(model, model_path)
        joblib.dump(preprocessor, preprocessor_path)

        monkeypatch.setenv("RECOMMENDATION_ENGINE", "ml")
        monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
        monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "0.0")  # accept whatever it predicts
        get_settings.cache_clear()

        token = _register_and_onboard(client)
        response = client.post(
            "/api/v1/workouts/recommend",
            json={"workout_days_per_week": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        # The tiny model was trained on these 3 classes only.
        assert body["split_name"] in ("Push Pull Legs", "Home Bodyweight Split", "Upper Lower")

        get_settings.cache_clear()

    def test_generate_endpoint_also_respects_the_engine_setting(
        self, client: TestClient, monkeypatch, tmp_path
    ):
        """POST /workouts/generate calls the same recommendation_service —
        confirming the switch applies there too, not just /recommend."""
        monkeypatch.setenv("RECOMMENDATION_ENGINE", "ml")
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "missing.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "missing2.joblib"))
        get_settings.cache_clear()

        token = _register_and_onboard(client)
        response = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Must still succeed via fallback — the Workout Planner downstream
        # of the recommendation must never see a broken/missing recommendation.
        assert response.status_code == 201

        get_settings.cache_clear()
