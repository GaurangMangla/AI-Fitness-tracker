"""Unit tests for `WorkoutRecommendationService`.

Covers the four scenarios the spec names explicitly (muscle gain, weight
loss, strength, home workout), plus the two error scenarios (invalid
profile, missing onboarding). No database involved — `Profile` instances are
constructed directly in memory, since the service never touches a session.
"""

import pytest

from app.core.exceptions import ValidationError
from app.models.enums import (
    ActivityLevel,
    DietPreference,
    FitnessGoal,
    Gender,
    WorkoutExperience,
)
from app.models.profile import Profile
from app.services.workout_recommendation_service import WorkoutRecommendationService
from app.services.workout_splits import SPLIT_BY_KEY


def _make_profile(**overrides: object) -> Profile:
    defaults: dict[str, object] = dict(
        name="Test User",
        age=28,
        gender=Gender.male,
        height_cm=178,
        weight_kg=75,
        fitness_goal=FitnessGoal.muscle_gain,
        activity_level=ActivityLevel.moderately_active,
        workout_experience=WorkoutExperience.intermediate,
        equipment_available=["full_gym"],
        diet_preference=DietPreference.non_vegetarian,
    )
    defaults.update(overrides)
    return Profile(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def service() -> WorkoutRecommendationService:
    return WorkoutRecommendationService()


def test_muscle_gain_recommends_push_pull_legs(service: WorkoutRecommendationService) -> None:
    profile = _make_profile(
        fitness_goal=FitnessGoal.muscle_gain,
        workout_experience=WorkoutExperience.intermediate,
        equipment_available=["full_gym"],
    )

    result = service.recommend(profile, workout_days_per_week=5)

    assert result.split_name == "Push Pull Legs"
    assert result.title == "Muscle Gain Plan"
    assert result.workout_days == 5
    assert result.difficulty == "Intermediate"
    assert result.reason == (
        "Recommended because the user selected Muscle Gain, Intermediate experience, "
        "Gym equipment and 5 workout days."
    )


def test_weight_loss_recommends_full_body(service: WorkoutRecommendationService) -> None:
    profile = _make_profile(
        fitness_goal=FitnessGoal.weight_loss,
        workout_experience=WorkoutExperience.beginner,
        equipment_available=["dumbbells"],
    )

    result = service.recommend(profile, workout_days_per_week=3)

    assert result.split_name == "Full Body"
    assert result.title == "Weight Loss Plan"
    assert result.difficulty == "Beginner"


def test_strength_recommends_upper_lower_strength(service: WorkoutRecommendationService) -> None:
    profile = _make_profile(
        fitness_goal=FitnessGoal.muscle_gain,
        workout_experience=WorkoutExperience.advanced,
        equipment_available=["barbell"],
    )

    result = service.recommend(profile, workout_days_per_week=4)

    assert result.split_name == "Upper Lower Strength"
    assert result.title == "Strength Plan"
    assert result.difficulty == "Advanced"


def test_home_workout_recommends_home_bodyweight_split(
    service: WorkoutRecommendationService,
) -> None:
    profile = _make_profile(
        fitness_goal=FitnessGoal.general_fitness,
        workout_experience=WorkoutExperience.beginner,
        equipment_available=["none"],
    )

    result = service.recommend(profile, workout_days_per_week=3)

    assert result.split_name == "Home Bodyweight Split"
    assert result.title == "Home Workout Plan"
    assert "No equipment" in result.reason


def test_missing_onboarding_raises_validation_error(
    service: WorkoutRecommendationService,
) -> None:
    """profile=None — a registered user who hasn't completed onboarding."""
    with pytest.raises(ValidationError):
        service.recommend(None, workout_days_per_week=4)


def test_invalid_profile_with_no_equipment_selected_raises_validation_error(
    service: WorkoutRecommendationService,
) -> None:
    """A profile with an empty equipment list — not producible through the
    real onboarding flow (Milestone 1 requires at least one item), but
    `_validate_profile_for_recommendation` defends against it directly
    rather than assuming that upstream invariant always holds."""
    profile = _make_profile(equipment_available=[])

    with pytest.raises(ValidationError):
        service.recommend(profile, workout_days_per_week=4)


def test_recommendation_response_has_exactly_the_spec_shape(
    service: WorkoutRecommendationService,
) -> None:
    profile = _make_profile()
    result = service.recommend(profile, workout_days_per_week=5)
    assert set(result.model_dump().keys()) == {
        "title",
        "split_name",
        "workout_days",
        "difficulty",
        "reason",
        # Added for the premium AI recommendation UI — all additive,
        # all defaulted (see schemas/recommendation.py), so this is an
        # intentional widening of the contract, not a break: every field
        # from the original spec above is still present, unchanged.
        "engine",
        "confidence",
        "latency_ms",
        "model_version",
        "explanation",
    }


def test_a_substituted_engine_changes_the_outcome(service: WorkoutRecommendationService) -> None:
    """Proves the ML-swap seam actually works: a fake engine implementing
    the same `recommend(...)` shape changes the result, with no other code
    needing to change."""

    class _AlwaysBroSplitEngine:
        def recommend(self, recommendation_input: object) -> object:
            return SPLIT_BY_KEY["bro_split"]

    custom_service = WorkoutRecommendationService(engine=_AlwaysBroSplitEngine())  # type: ignore[arg-type]
    profile = _make_profile(
        fitness_goal=FitnessGoal.weight_loss,
        workout_experience=WorkoutExperience.beginner,
        equipment_available=["none"],
    )

    result = custom_service.recommend(profile, workout_days_per_week=3)

    assert result.split_name == "Bro Split"


def test_bro_split_is_genuinely_reachable_for_advanced_users_at_5_days(
    service: WorkoutRecommendationService,
) -> None:
    """Regression test for a real bug found while building the ML training
    dataset (see ml/ML_TRAINING.md §2.4): `bro_split` could never be
    recommended under ANY input, because push_pull_legs scored equal-or-
    higher on every dimension the rule engine evaluated, and ties always
    resolved to push_pull_legs (defined first in WORKOUT_SPLITS). Fixed in
    recommendation_rules.py by raising bro_split's advanced-experience score
    from 10 to 12 — this test locks in that bro_split is now reachable at
    its classic real-world niche (advanced lifter, 5 days/week, full gym),
    across every fitness goal, so this can't silently regress back to
    unreachable."""
    for goal in (
        FitnessGoal.muscle_gain,
        FitnessGoal.weight_loss,
        FitnessGoal.maintenance,
        FitnessGoal.general_fitness,
    ):
        profile = _make_profile(
            fitness_goal=goal,
            workout_experience=WorkoutExperience.advanced,
            equipment_available=["full_gym"],
        )
        result = service.recommend(profile, workout_days_per_week=5)
        assert result.split_name == "Bro Split", f"Expected Bro Split for goal={goal}"


def test_push_pull_legs_still_wins_at_6_days_even_for_advanced_users(
    service: WorkoutRecommendationService,
) -> None:
    """The bro_split fix (above) must not flip the correct outcome at 6
    days, where cycling a 3-day push/pull/legs rotation twice is the more
    natural fit than a single-muscle-per-day bodybuilding split."""
    profile = _make_profile(
        fitness_goal=FitnessGoal.muscle_gain,
        workout_experience=WorkoutExperience.advanced,
        equipment_available=["full_gym"],
    )
    result = service.recommend(profile, workout_days_per_week=6)
    assert result.split_name == "Push Pull Legs"


def test_bro_split_still_loses_to_push_pull_legs_for_intermediate_users(
    service: WorkoutRecommendationService,
) -> None:
    """The fix only raised bro_split's *advanced*-experience score —
    intermediate users should be completely unaffected."""
    profile = _make_profile(
        fitness_goal=FitnessGoal.muscle_gain,
        workout_experience=WorkoutExperience.intermediate,
        equipment_available=["full_gym"],
    )
    result = service.recommend(profile, workout_days_per_week=5)
    assert result.split_name == "Push Pull Legs"


def test_explanation_reflects_the_actual_profile(service: WorkoutRecommendationService) -> None:
    """The new explanation object (added for the premium AI recommendation
    UI) must describe the *actual* profile passed in, using the same
    human-readable labels _build_reason() already uses in its prose."""
    profile = _make_profile(
        fitness_goal=FitnessGoal.weight_loss,
        workout_experience=WorkoutExperience.beginner,
        equipment_available=["none"],
        age=35,
        gender=Gender.female,
    )
    result = service.recommend(profile, workout_days_per_week=3)

    assert result.explanation is not None
    assert result.explanation.goal == "Weight Loss"
    assert result.explanation.experience == "Beginner"
    assert result.explanation.days_per_week == 3
    assert result.explanation.equipment == "No equipment"
    assert result.explanation.gender == "Female"
    assert result.explanation.age == 35


def test_rule_engine_default_reports_engine_rule_with_no_confidence_or_model_version(
    service: WorkoutRecommendationService,
) -> None:
    """The default WorkoutRecommendationService() (no engine passed in)
    uses RuleBasedRecommendationEngine — its metadata should say so, and
    have no confidence/model_version, since neither concept applies to a
    rule-based decision."""
    profile = _make_profile()
    result = service.recommend(profile, workout_days_per_week=5)

    assert result.engine == "rule"
    assert result.confidence is None
    assert result.model_version is None
    assert result.latency_ms is not None  # timing is still measured either way


def test_a_substituted_engine_without_metadata_support_still_gets_a_valid_response(
    service: WorkoutRecommendationService,
) -> None:
    """An engine implementing only the original RecommendationEngine
    protocol (recommend() -> WorkoutSplitDefinition, no
    recommend_with_metadata()) must still produce a complete, valid
    RecommendationResponse — the metadata just gets synthesized as a
    generic "rule" result rather than raising or crashing."""
    from app.services.workout_splits import SPLIT_BY_KEY as _SPLITS

    class _MinimalEngine:
        """Deliberately implements only the base protocol method."""

        def recommend(self, recommendation_input: object) -> object:
            return _SPLITS["full_body"]

    custom_service = WorkoutRecommendationService(engine=_MinimalEngine())  # type: ignore[arg-type]
    profile = _make_profile()

    result = custom_service.recommend(profile, workout_days_per_week=3)

    assert result.split_name == "Full Body"
    assert result.engine == "rule"
    assert result.confidence is None
    assert result.model_version is None
    assert result.explanation is not None
