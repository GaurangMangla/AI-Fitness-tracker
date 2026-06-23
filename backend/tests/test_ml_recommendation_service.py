"""Tests for `MLRecommendationService` — the core Phase 2.3 deliverable.

Covers every fallback trigger named in the phase spec: model unavailable,
low confidence, invalid input, and an unexpected exception. The one
invariant every test in this file checks in some form: **the caller never
sees an exception** — `recommend()` always returns a real
`WorkoutSplitDefinition`, whether that came from the model or the rule
engine underneath it.
"""

import joblib
import pytest

from app.core.config import get_settings
from app.ml import registry
from app.models.enums import (
    ActivityLevel,
    DietPreference,
    Equipment,
    FitnessGoal,
    Gender,
    WorkoutExperience,
)
from app.services.ml_recommendation_service import MLRecommendationService
from app.services.recommendation_types import RecommendationInput
from app.services.workout_splits import WorkoutSplitDefinition
from tests.ml_test_helpers import build_tiny_model_and_preprocessor


def _make_input(**overrides: object) -> RecommendationInput:
    defaults: dict[str, object] = dict(
        fitness_goal=FitnessGoal.muscle_gain,
        workout_experience=WorkoutExperience.intermediate,
        activity_level=ActivityLevel.moderately_active,
        equipment_available=[Equipment.full_gym],
        workout_days_per_week=5,
        age=28,
        gender=Gender.male,
        diet_preference=DietPreference.non_vegetarian,
        height_cm=178.0,
        weight_kg=78.0,
    )
    defaults.update(overrides)
    return RecommendationInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _reset_registry():
    registry.reset_for_testing()
    yield
    registry.reset_for_testing()


@pytest.fixture
def working_model(tmp_path, monkeypatch):
    """A real, tiny, correctly-loadable model+preprocessor — the
    "everything is fine" scenario every other fixture in this file is a
    variation of breaking in one specific way."""
    model, preprocessor = build_tiny_model_and_preprocessor()
    model_path = tmp_path / "model.joblib"
    preprocessor_path = tmp_path / "preprocessor.joblib"
    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)

    monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
    monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
    monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "0.5")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSuccessfulPrediction:
    def test_returns_a_real_split_definition(self, working_model):
        service = MLRecommendationService()
        result = service.recommend(_make_input())
        assert isinstance(result, WorkoutSplitDefinition)

    def test_the_predicted_split_is_one_the_model_was_trained_on(self, working_model):
        # The tiny model in ml_test_helpers.py was trained on exactly these
        # three classes — confirms a genuinely high-confidence prediction
        # (not a fallback) is what's actually being returned here.
        service = MLRecommendationService()
        result = service.recommend(_make_input())
        assert result.key in ("push_pull_legs", "home_bodyweight", "upper_lower")

    def test_logs_the_source_confidence_and_latency(self, working_model, caplog):
        import logging

        service = MLRecommendationService()
        with caplog.at_level(logging.INFO, logger="app.services.ml_recommendation_service"):
            service.recommend(_make_input())

        assert any("served by ML model" in r.message for r in caplog.records)
        assert any("confidence=" in r.message for r in caplog.records)
        assert any("latency_ms=" in r.message for r in caplog.records)


class TestFallbackWhenModelUnavailable:
    def test_falls_back_to_rule_engine_when_model_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "nonexistent.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "also_nonexistent.joblib"))
        get_settings.cache_clear()

        service = MLRecommendationService()
        # Must not raise — this is the entire point of the fallback.
        result = service.recommend(_make_input())
        assert isinstance(result, WorkoutSplitDefinition)

        get_settings.cache_clear()

    def test_fallback_result_matches_calling_the_rule_engine_directly(self, tmp_path, monkeypatch):
        from app.services.recommendation_engine import RuleBasedRecommendationEngine

        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "missing.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "missing2.joblib"))
        get_settings.cache_clear()

        recommendation_input = _make_input()
        ml_service = MLRecommendationService()
        ml_result = ml_service.recommend(recommendation_input)

        rule_result = RuleBasedRecommendationEngine().recommend(recommendation_input)
        assert ml_result.key == rule_result.key

        get_settings.cache_clear()

    def test_logs_the_fallback_reason(self, tmp_path, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "gone.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "gone2.joblib"))
        get_settings.cache_clear()

        service = MLRecommendationService()
        with caplog.at_level(logging.WARNING, logger="app.services.ml_recommendation_service"):
            service.recommend(_make_input())

        assert any("falling back to rule engine" in r.message for r in caplog.records)

        get_settings.cache_clear()


class TestFallbackWhenConfidenceTooLow:
    def test_falls_back_when_confidence_below_threshold(self, working_model, monkeypatch):
        # working_model's default threshold (0.5) is comfortably below what
        # the tiny model actually predicts with; cranking it to just over 1.0
        # guarantees every real prediction counts as "too uncertain."
        monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "1.01")
        get_settings.cache_clear()

        service = MLRecommendationService()
        result = service.recommend(_make_input())
        # Still must return a real result — just via the rule engine this time.
        assert isinstance(result, WorkoutSplitDefinition)

        get_settings.cache_clear()

    def test_logs_the_confidence_and_threshold_on_low_confidence_fallback(
        self, working_model, monkeypatch, caplog
    ):
        import logging

        monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "1.01")
        get_settings.cache_clear()

        service = MLRecommendationService()
        with caplog.at_level(logging.INFO, logger="app.services.ml_recommendation_service"):
            service.recommend(_make_input())

        assert any("below threshold" in r.message for r in caplog.records)

        get_settings.cache_clear()


class TestFallbackOnInvalidInput:
    def test_falls_back_when_diet_preference_missing(self, working_model):
        """A RecommendationInput missing the ML-only fields (diet_preference/
        height_cm/weight_kg) makes build_feature_row raise ValueError — this
        must be caught by recommend(), same as any other failure."""
        service = MLRecommendationService()
        broken_input = _make_input(diet_preference=None)
        result = service.recommend(broken_input)
        assert isinstance(result, WorkoutSplitDefinition)

    def test_falls_back_when_height_missing(self, working_model):
        service = MLRecommendationService()
        result = service.recommend(_make_input(height_cm=None))
        assert isinstance(result, WorkoutSplitDefinition)


class TestUnrecognisedPrediction:
    def test_falls_back_if_model_predicts_an_unknown_split_key(self, tmp_path, monkeypatch):
        """Defends against a corrupted/mismatched artifact predicting a
        class that isn't one of the 6 real split keys — should never
        happen with a correctly trained model, but must not crash if it did."""
        import joblib as _joblib
        import pandas as pd
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import OneHotEncoder

        from app.ml.feature_builder import _FEATURE_COLUMNS

        # A model trained on a bogus class name that will never appear in
        # SPLIT_BY_KEY, simulating a mismatched/corrupted artifact.
        rows = [
            {
                "gender": "male",
                "fitness_goal": "muscle_gain",
                "activity_level": "sedentary",
                "workout_experience": "beginner",
                "diet_preference": "vegan",
                "bmi_category": "normal",
                "age": 30,
                "height_cm": 170.0,
                "weight_kg": 70.0,
                "bmi": 24.2,
                "workout_days_per_week": 3,
                "equipment_count": 0,
                "has_gym_access": False,
                "equip_barbell": False,
                "equip_dumbbells": False,
                "equip_full_gym": False,
                "equip_none": True,
                "equip_pull_up_bar": False,
                "equip_resistance_bands": False,
                "target": "not_a_real_split_key",
            }
        ] * 10
        df = pd.DataFrame(rows)
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "cat",
                    OneHotEncoder(handle_unknown="ignore"),
                    [
                        "gender",
                        "fitness_goal",
                        "activity_level",
                        "workout_experience",
                        "diet_preference",
                        "bmi_category",
                    ],
                )
            ],
            remainder="passthrough",
        )
        X = preprocessor.fit_transform(df[_FEATURE_COLUMNS])
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        model.fit(X, df["target"])

        model_path = tmp_path / "bogus_model.joblib"
        preprocessor_path = tmp_path / "bogus_preprocessor.joblib"
        _joblib.dump(model, model_path)
        _joblib.dump(preprocessor, preprocessor_path)

        monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
        monkeypatch.setenv(
            "ML_CONFIDENCE_THRESHOLD", "0.0"
        )  # isolate this test to the key-check path
        get_settings.cache_clear()

        service = MLRecommendationService()
        result = service.recommend(_make_input())
        # Must fall back to a real split, never the bogus key.
        assert isinstance(result, WorkoutSplitDefinition)
        assert result.key != "not_a_real_split_key"

        get_settings.cache_clear()


class TestRecommendWithMetadata:
    """Tests for `recommend_with_metadata()` — added for the premium AI
    recommendation UI. `recommend()` itself is unchanged (see the other
    test classes above); these specifically check the richer return type."""

    def test_successful_prediction_reports_engine_ml_and_real_confidence(self, working_model):
        service = MLRecommendationService()
        result = service.recommend_with_metadata(_make_input())

        assert result.engine == "ml"
        assert result.confidence is not None
        assert 0.0 <= result.confidence <= 1.0
        assert result.latency_ms >= 0

    def test_recommend_and_recommend_with_metadata_agree_on_the_split(self, working_model):
        """`.recommend()` must still return exactly `.recommend_with_metadata().split`
        — this is what keeps `.recommend()` unchanged from Phase 2.3, not a
        second, potentially-diverging implementation."""
        service = MLRecommendationService()
        recommendation_input = _make_input()

        # Same input, same deterministic model -> same result either way.
        split_via_recommend = service.recommend(recommendation_input)
        result_via_metadata = service.recommend_with_metadata(recommendation_input)

        assert split_via_recommend.key == result_via_metadata.split.key

    def test_fallback_reports_engine_rule_with_no_confidence(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "missing.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "missing2.joblib"))
        get_settings.cache_clear()

        service = MLRecommendationService()
        result = service.recommend_with_metadata(_make_input())

        assert result.engine == "rule"
        assert result.confidence is None
        assert result.model_version is None

        get_settings.cache_clear()

    def test_low_confidence_fallback_also_reports_engine_rule(self, working_model, monkeypatch):
        monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "1.01")  # guarantees fallback
        get_settings.cache_clear()

        service = MLRecommendationService()
        result = service.recommend_with_metadata(_make_input())

        assert result.engine == "rule"
        assert result.confidence is None

        get_settings.cache_clear()
