"""The recommendation rule pipeline.

Five independent functions, each with the same shape —
`(RecommendationInput, list[ScoredSplit]) -> list[ScoredSplit]` — chained
together by `recommendation_engine.RuleBasedRecommendationEngine`. None of
them know about each other; each only reads `RecommendationInput` and
mutates the candidates it's given. That uniform shape is the actual seam for
"easy to replace with an ML model later": a future engine implementation can
keep some of these rules (e.g. `equipment_rule`'s hard disqualification is a
real constraint, not a preference, and would still apply to ML output) while
replacing the scoring rules with a model's predictions — without changing
this function signature, every existing rule keeps working unmodified.
"""

from app.models.enums import ActivityLevel, Equipment, FitnessGoal, WorkoutExperience
from app.services.recommendation_types import RecommendationInput, ScoredSplit

# --- Equipment ---------------------------------------------------------------
_REAL_EQUIPMENT = (Equipment.dumbbells, Equipment.barbell, Equipment.full_gym)
_HOME_BODYWEIGHT_BONUS_WHEN_NO_REAL_EQUIPMENT = 12


def equipment_rule(
    recommendation_input: RecommendationInput, candidates: list[ScoredSplit]
) -> list[ScoredSplit]:
    """Hard-disqualifies any split whose equipment requirement isn't met, and
    gives the Home Bodyweight split a decisive scoring bonus specifically
    when the user has no real resistance equipment — without that bonus,
    Full Body can out-score it on goal/experience fit alone even when the
    user has nothing to train with, which isn't the right answer."""
    has_real_equipment = any(
        equipment in recommendation_input.equipment_available for equipment in _REAL_EQUIPMENT
    )

    for candidate in candidates:
        requirement = candidate.definition.requires_equipment
        if requirement is not None and not any(
            equipment in recommendation_input.equipment_available for equipment in requirement
        ):
            candidate.eligible = False
            continue

        if candidate.definition.key == "home_bodyweight" and not has_real_equipment:
            candidate.score += _HOME_BODYWEIGHT_BONUS_WHEN_NO_REAL_EQUIPMENT
            candidate.reasons.append("no gym equipment available")

    return candidates


# --- Workout days -------------------------------------------------------------
def workout_days_rule(
    recommendation_input: RecommendationInput, candidates: list[ScoredSplit]
) -> list[ScoredSplit]:
    """Disqualifies splits whose day-count range doesn't fit how many days
    the user wants to train, and scores the rest by closeness to that
    split's ideal day count(s)."""
    days = recommendation_input.workout_days_per_week

    for candidate in candidates:
        definition = candidate.definition
        if not (definition.min_days <= days <= definition.max_days):
            candidate.eligible = False
            continue

        if days in definition.ideal_days:
            candidate.score += 10
            candidate.reasons.append(f"fits a {days}-day schedule well")
        else:
            closest_gap = min(abs(days - ideal) for ideal in definition.ideal_days)
            candidate.score += max(0, 6 - closest_gap * 2)

    return candidates


# --- Goal ----------------------------------------------------------------------
# Score contribution per (goal, split) pair. Missing entries default to 0 via
# `.get(..., 0)` below, e.g. a split with no opinion for a given goal.
_GOAL_SCORES: dict[FitnessGoal, dict[str, float]] = {
    FitnessGoal.muscle_gain: {
        "push_pull_legs": 10,
        "bro_split": 9,
        "upper_lower": 7,
        "upper_lower_strength": 6,
        "full_body": 3,
        "home_bodyweight": 2,
    },
    FitnessGoal.weight_loss: {
        "full_body": 10,
        "home_bodyweight": 8,
        "upper_lower": 6,
        "upper_lower_strength": 3,
        "push_pull_legs": 3,
        "bro_split": 2,
    },
    FitnessGoal.maintenance: {
        "upper_lower": 9,
        "full_body": 8,
        "home_bodyweight": 5,
        "push_pull_legs": 5,
        "upper_lower_strength": 5,
        "bro_split": 3,
    },
    FitnessGoal.general_fitness: {
        "full_body": 10,
        "upper_lower": 7,
        "home_bodyweight": 7,
        "push_pull_legs": 4,
        "upper_lower_strength": 4,
        "bro_split": 2,
    },
}


def goal_rule(
    recommendation_input: RecommendationInput, candidates: list[ScoredSplit]
) -> list[ScoredSplit]:
    scores = _GOAL_SCORES.get(recommendation_input.fitness_goal, {})
    for candidate in candidates:
        candidate.score += scores.get(candidate.definition.key, 0)
    return candidates


# --- Experience ----------------------------------------------------------------
_EXPERIENCE_SCORES: dict[WorkoutExperience, dict[str, float]] = {
    WorkoutExperience.beginner: {
        "full_body": 10,
        "home_bodyweight": 8,
        "upper_lower": 7,
        "upper_lower_strength": 2,
        "push_pull_legs": 2,
        "bro_split": 0,
    },
    WorkoutExperience.intermediate: {
        "push_pull_legs": 10,
        "upper_lower": 9,
        "upper_lower_strength": 7,
        "bro_split": 6,
        "full_body": 5,
        "home_bodyweight": 5,
    },
    WorkoutExperience.advanced: {
        # bro_split and upper_lower_strength were both 10 here originally —
        # a +1 edge over push_pull_legs (9) that turned out to never be
        # enough: push_pull_legs's goal score is 1-2 points higher than
        # bro_split's in every single FitnessGoal (see _GOAL_SCORES above),
        # and push_pull_legs matches bro_split's day-fit score at bro_split's
        # only ideal day count (5). The result was that bro_split could
        # never mathematically outscore push_pull_legs under any input —
        # verified exhaustively while building the ML training dataset (see
        # ml/ML_TRAINING.md §2.4, which documents the bug this fixes).
        #
        # Raised to 12 (a +3 edge, not +1) specifically so bro_split wins at
        # its classic real-world niche — an advanced lifter training 5 days
        # a week with full gym access — across every fitness goal, while
        # changing nothing else: push_pull_legs still correctly wins at 6
        # days (where 2x through a 3-day PPL cycle is the more natural fit
        # than a bodybuilding split), and every beginner/intermediate score
        # is untouched.
        "bro_split": 12,
        "upper_lower_strength": 10,
        "push_pull_legs": 9,
        "upper_lower": 6,
        "full_body": 3,
        "home_bodyweight": 3,
    },
}


def experience_rule(
    recommendation_input: RecommendationInput, candidates: list[ScoredSplit]
) -> list[ScoredSplit]:
    scores = _EXPERIENCE_SCORES.get(recommendation_input.workout_experience, {})
    for candidate in candidates:
        candidate.score += scores.get(candidate.definition.key, 0)
    return candidates


# --- Recovery capacity (age + activity level) -----------------------------------
_HIGH_FREQUENCY_SPLITS = {"bro_split", "push_pull_legs"}
_REDUCED_RECOVERY_ACTIVITY_LEVELS = (ActivityLevel.very_active, ActivityLevel.extra_active)
_REDUCED_RECOVERY_AGE_THRESHOLD = 50


def recovery_rule(
    recommendation_input: RecommendationInput, candidates: list[ScoredSplit]
) -> list[ScoredSplit]:
    """Age and activity level are real, well-established proxies for
    recovery capacity in exercise programming: older trainees and those with
    high non-training physical demands generally need more recovery time
    between sessions. This is deliberately a small adjustment — a
    tie-breaker on top of goal/experience/equipment, not a factor that
    overrides them.

    `gender` is part of `RecommendationInput` (the spec calls for it as an
    input) but no rule, including this one, uses it: there's no legitimate
    exercise-science basis for sex to determine workout *split structure* —
    unlike, say, calorie targets, which legitimately differ by sex for
    body-composition reasons (see `metrics_service`). It's threaded through
    the input contract so a future ML-based engine has it available if it
    finds a real population-level signal, without this rule-based version
    inventing one that doesn't reflect real training science.
    """
    reduced_recovery = (
        recommendation_input.age >= _REDUCED_RECOVERY_AGE_THRESHOLD
        or recommendation_input.activity_level in _REDUCED_RECOVERY_ACTIVITY_LEVELS
    )

    for candidate in candidates:
        if candidate.definition.key not in _HIGH_FREQUENCY_SPLITS:
            continue
        if reduced_recovery:
            candidate.score -= 3
        else:
            candidate.score += 1

    return candidates


# Order matters only in that later rules see scores/eligibility set by
# earlier ones — every rule is still independent and order-stable for the
# decision itself, since disqualification (`eligible = False`) and additive
# scoring don't depend on which rule ran first.
RULE_PIPELINE = (goal_rule, equipment_rule, experience_rule, workout_days_rule, recovery_rule)
