"""Tests for `app.ml.feature_builder` — verifies the feature row matches the
exact schema the trained preprocessor expects, and that missing ML-only
fields raise rather than silently building a nonsense row.
"""

import pytest

from app.ml.feature_builder import _FEATURE_COLUMNS, build_feature_row
from app.models.enums import (
    ActivityLevel,
    DietPreference,
    Equipment,
    FitnessGoal,
    Gender,
    WorkoutExperience,
)
from app.services.recommendation_types import RecommendationInput


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


class TestBuildFeatureRow:
    def test_returns_a_single_row_with_the_exact_trained_columns(self):
        row = build_feature_row(_make_input())
        assert len(row) == 1
        assert list(row.columns) == _FEATURE_COLUMNS

    def test_categorical_fields_use_the_enum_value_not_the_member(self):
        row = build_feature_row(_make_input(fitness_goal=FitnessGoal.weight_loss))
        assert row.iloc[0]["fitness_goal"] == "weight_loss"

    def test_bmi_is_computed_from_height_and_weight(self):
        row = build_feature_row(_make_input(height_cm=180.0, weight_kg=90.0))
        # 90 / 1.8^2 = 27.78
        assert row.iloc[0]["bmi"] == pytest.approx(27.8, abs=0.1)

    def test_bmi_category_matches_the_computed_bmi(self):
        # Deliberately underweight: 50kg at 180cm -> BMI ~15.4
        row = build_feature_row(_make_input(height_cm=180.0, weight_kg=50.0))
        assert row.iloc[0]["bmi_category"] == "underweight"

    def test_equipment_count_matches_the_list_length(self):
        row = build_feature_row(
            _make_input(equipment_available=[Equipment.dumbbells, Equipment.pull_up_bar])
        )
        assert row.iloc[0]["equipment_count"] == 2

    def test_has_gym_access_true_only_with_full_gym(self):
        with_gym = build_feature_row(_make_input(equipment_available=[Equipment.full_gym]))
        without_gym = build_feature_row(_make_input(equipment_available=[Equipment.dumbbells]))
        assert bool(with_gym.iloc[0]["has_gym_access"]) is True
        assert bool(without_gym.iloc[0]["has_gym_access"]) is False

    def test_each_equip_column_reflects_the_equipment_list(self):
        row = build_feature_row(
            _make_input(equipment_available=[Equipment.barbell, Equipment.dumbbells])
        )
        assert bool(row.iloc[0]["equip_barbell"]) is True
        assert bool(row.iloc[0]["equip_dumbbells"]) is True
        assert bool(row.iloc[0]["equip_full_gym"]) is False
        assert bool(row.iloc[0]["equip_none"]) is False

    def test_raises_value_error_when_diet_preference_missing(self):
        # The error message mentions all three required ML-only fields
        # together (see feature_builder.py) rather than pinpointing exactly
        # one, so each of these three tests checks that its specific `None`
        # field triggers the raise, not that the message differs per field.
        with pytest.raises(ValueError, match="diet_preference/height_cm/weight_kg"):
            build_feature_row(_make_input(diet_preference=None))

    def test_raises_value_error_when_height_missing(self):
        with pytest.raises(ValueError, match="diet_preference/height_cm/weight_kg"):
            build_feature_row(_make_input(height_cm=None))

    def test_raises_value_error_when_weight_missing(self):
        with pytest.raises(ValueError, match="diet_preference/height_cm/weight_kg"):
            build_feature_row(_make_input(weight_kg=None))
