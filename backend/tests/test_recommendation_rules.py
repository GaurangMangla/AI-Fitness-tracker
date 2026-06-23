"""Unit tests for the individual rule functions, each tested in isolation —
this is the actual payoff of "modular rule engine, not one big if-else":
each rule's logic is verifiable on its own, independent of the others or of
final split selection.
"""

from app.models.enums import ActivityLevel, Equipment, FitnessGoal, Gender, WorkoutExperience
from app.services.recommendation_rules import (
    equipment_rule,
    experience_rule,
    goal_rule,
    recovery_rule,
    workout_days_rule,
)
from app.services.recommendation_types import RecommendationInput, ScoredSplit
from app.services.workout_splits import WORKOUT_SPLITS


def _fresh_candidates() -> list[ScoredSplit]:
    return [ScoredSplit(definition=definition) for definition in WORKOUT_SPLITS]


def _make_input(**overrides: object) -> RecommendationInput:
    defaults: dict[str, object] = dict(
        fitness_goal=FitnessGoal.muscle_gain,
        workout_experience=WorkoutExperience.intermediate,
        activity_level=ActivityLevel.moderately_active,
        equipment_available=[Equipment.full_gym],
        workout_days_per_week=4,
        age=30,
        gender=Gender.male,
    )
    defaults.update(overrides)
    return RecommendationInput(**defaults)


def test_equipment_rule_disqualifies_splits_needing_unavailable_equipment() -> None:
    recommendation_input = _make_input(equipment_available=[Equipment.dumbbells])

    candidates = equipment_rule(recommendation_input, _fresh_candidates())
    by_key = {c.definition.key: c for c in candidates}

    assert by_key["bro_split"].eligible is False  # needs full_gym specifically
    assert by_key["upper_lower_strength"].eligible is False  # needs barbell/full_gym
    assert by_key["push_pull_legs"].eligible is True  # dumbbells satisfy it


def test_equipment_rule_gives_home_bodyweight_a_bonus_with_no_real_equipment() -> None:
    recommendation_input = _make_input(equipment_available=[Equipment.none])

    candidates = equipment_rule(recommendation_input, _fresh_candidates())
    by_key = {c.definition.key: c for c in candidates}

    assert by_key["home_bodyweight"].score > 0
    assert by_key["full_body"].score == 0  # no equivalent bonus for full_body


def test_equipment_rule_gives_no_bonus_when_real_equipment_exists() -> None:
    recommendation_input = _make_input(equipment_available=[Equipment.full_gym])

    candidates = equipment_rule(recommendation_input, _fresh_candidates())
    by_key = {c.definition.key: c for c in candidates}

    assert by_key["home_bodyweight"].score == 0


def test_workout_days_rule_disqualifies_out_of_range_splits() -> None:
    recommendation_input = _make_input(workout_days_per_week=1)

    candidates = workout_days_rule(recommendation_input, _fresh_candidates())
    by_key = {c.definition.key: c for c in candidates}

    assert by_key["bro_split"].eligible is False  # needs at least 5 days
    assert by_key["home_bodyweight"].eligible is True  # 1-7 day range


def test_workout_days_rule_scores_an_exact_match_higher_than_a_near_miss() -> None:
    exact_match = _make_input(workout_days_per_week=4)  # upper_lower's ideal
    near_miss = _make_input(workout_days_per_week=5)

    exact_scores = {
        c.definition.key: c.score for c in workout_days_rule(exact_match, _fresh_candidates())
    }
    near_scores = {
        c.definition.key: c.score for c in workout_days_rule(near_miss, _fresh_candidates())
    }

    assert exact_scores["upper_lower"] > near_scores["upper_lower"]


def test_goal_rule_favors_full_body_for_weight_loss() -> None:
    recommendation_input = _make_input(fitness_goal=FitnessGoal.weight_loss)

    candidates = goal_rule(recommendation_input, _fresh_candidates())
    by_key = {c.definition.key: c.score for c in candidates}

    assert by_key["full_body"] > by_key["bro_split"]


def test_experience_rule_favors_full_body_for_beginners() -> None:
    recommendation_input = _make_input(workout_experience=WorkoutExperience.beginner)

    candidates = experience_rule(recommendation_input, _fresh_candidates())
    by_key = {c.definition.key: c.score for c in candidates}

    assert by_key["full_body"] > by_key["bro_split"]


def test_experience_rule_favors_advanced_splits_for_advanced_users() -> None:
    recommendation_input = _make_input(workout_experience=WorkoutExperience.advanced)

    candidates = experience_rule(recommendation_input, _fresh_candidates())
    by_key = {c.definition.key: c.score for c in candidates}

    assert by_key["bro_split"] > by_key["full_body"]


def test_recovery_rule_penalizes_high_frequency_splits_for_older_users() -> None:
    younger = _make_input(age=25)
    older = _make_input(age=60)

    younger_scores = {
        c.definition.key: c.score for c in recovery_rule(younger, _fresh_candidates())
    }
    older_scores = {c.definition.key: c.score for c in recovery_rule(older, _fresh_candidates())}

    assert older_scores["bro_split"] < younger_scores["bro_split"]


def test_recovery_rule_penalizes_high_frequency_splits_for_very_active_lifestyles() -> None:
    sedentary = _make_input(activity_level=ActivityLevel.sedentary)
    very_active = _make_input(activity_level=ActivityLevel.very_active)

    sedentary_scores = {
        c.definition.key: c.score for c in recovery_rule(sedentary, _fresh_candidates())
    }
    active_scores = {
        c.definition.key: c.score for c in recovery_rule(very_active, _fresh_candidates())
    }

    assert active_scores["push_pull_legs"] < sedentary_scores["push_pull_legs"]


def test_recovery_rule_does_not_affect_low_frequency_splits() -> None:
    younger = _make_input(age=25)
    older = _make_input(age=60)

    younger_scores = {
        c.definition.key: c.score for c in recovery_rule(younger, _fresh_candidates())
    }
    older_scores = {c.definition.key: c.score for c in recovery_rule(older, _fresh_candidates())}

    assert younger_scores["full_body"] == older_scores["full_body"] == 0


def test_gender_has_no_effect_on_any_rules_output() -> None:
    """Documents the deliberate no-op: changing only `gender` must not
    change any candidate's score or eligibility through any rule."""
    male_input = _make_input(gender=Gender.male)
    female_input = _make_input(gender=Gender.female)

    candidates_male = _fresh_candidates()
    candidates_female = _fresh_candidates()
    for rule in (goal_rule, equipment_rule, experience_rule, workout_days_rule, recovery_rule):
        candidates_male = rule(male_input, candidates_male)
        candidates_female = rule(female_input, candidates_female)

    male_scores = {c.definition.key: (c.score, c.eligible) for c in candidates_male}
    female_scores = {c.definition.key: (c.score, c.eligible) for c in candidates_female}
    assert male_scores == female_scores
