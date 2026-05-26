"""`WorkoutPlannerService` — converts a `RecommendationResponse` (which split,
how many days, what difficulty) into a complete persisted weekly plan.

Responsibilities:
1. Map the recommended split to concrete day templates (e.g. Push Pull Legs →
   [Push, Pull, Legs, Rest, Push, Pull, Legs]).
2. For each training day, select appropriate exercises from the DB using the
   user's equipment and experience level.
3. Apply volume adjustments (sets/reps/rest) based on experience.
4. Deactivate any existing active plan, then persist the new one.
5. Return the persisted plan plus computed metadata (split_name, difficulty,
   estimated duration) as a `GeneratedWorkoutPlanResponse`.

Architecture note: this service calls `WorkoutRecommendationService` internally
(via the generate endpoint passing a recommendation in), so the two services
are kept independent — PlannerService depends on the *output* schema of the
recommender, not on the recommender class itself. That lets the ML model swap
into the recommender later without touching this file.
"""

import random
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.enums import (
    Difficulty,
    Equipment,
    FitnessGoal,
    WorkoutExperience,
)
from app.models.exercise import Exercise
from app.repositories import (
    exercise_repository,
    workout_day_repository,
    workout_exercise_repository,
    workout_plan_repository,
)
from app.schemas.exercise import ExerciseResponse
from app.schemas.recommendation import RecommendationResponse
from app.schemas.workout import (
    GeneratedWorkoutPlanResponse,
    WorkoutDayResponse,
    WorkoutExerciseResponse,
)

# ---------------------------------------------------------------------------
# Volume tables — sets/reps/rest adjusted per experience level and goal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VolumeSpec:
    sets: int
    reps: str  # string: supports "8-12", "30 sec", "AMRAP" etc.
    rest_seconds: int
    # Estimated minutes per set including rest — used for duration estimate
    minutes_per_set: float


# (experience, goal) → volume spec for a *strength/compound* exercise
_STRENGTH_VOLUME: dict[tuple[WorkoutExperience, FitnessGoal], VolumeSpec] = {
    (WorkoutExperience.beginner, FitnessGoal.weight_loss): VolumeSpec(3, "12-15", 60, 1.5),
    (WorkoutExperience.beginner, FitnessGoal.muscle_gain): VolumeSpec(3, "10-12", 75, 1.8),
    (WorkoutExperience.beginner, FitnessGoal.maintenance): VolumeSpec(3, "12", 60, 1.5),
    (WorkoutExperience.beginner, FitnessGoal.general_fitness): VolumeSpec(3, "12", 60, 1.5),
    (WorkoutExperience.intermediate, FitnessGoal.weight_loss): VolumeSpec(4, "12-15", 60, 1.5),
    (WorkoutExperience.intermediate, FitnessGoal.muscle_gain): VolumeSpec(4, "8-12", 90, 2.0),
    (WorkoutExperience.intermediate, FitnessGoal.maintenance): VolumeSpec(3, "10-12", 75, 1.8),
    (WorkoutExperience.intermediate, FitnessGoal.general_fitness): VolumeSpec(3, "12", 75, 1.8),
    (WorkoutExperience.advanced, FitnessGoal.weight_loss): VolumeSpec(4, "15", 45, 1.3),
    (WorkoutExperience.advanced, FitnessGoal.muscle_gain): VolumeSpec(5, "6-8", 120, 2.5),
    (WorkoutExperience.advanced, FitnessGoal.maintenance): VolumeSpec(4, "8-10", 90, 2.0),
    (WorkoutExperience.advanced, FitnessGoal.general_fitness): VolumeSpec(4, "10-12", 75, 1.8),
}

# Isolation/accessory exercises always get slightly less volume
_ISOLATION_VOLUME: dict[tuple[WorkoutExperience, FitnessGoal], VolumeSpec] = {
    (WorkoutExperience.beginner, FitnessGoal.weight_loss): VolumeSpec(2, "15", 45, 1.0),
    (WorkoutExperience.beginner, FitnessGoal.muscle_gain): VolumeSpec(3, "12-15", 60, 1.3),
    (WorkoutExperience.beginner, FitnessGoal.maintenance): VolumeSpec(2, "15", 45, 1.0),
    (WorkoutExperience.beginner, FitnessGoal.general_fitness): VolumeSpec(2, "12-15", 45, 1.0),
    (WorkoutExperience.intermediate, FitnessGoal.weight_loss): VolumeSpec(3, "15", 45, 1.0),
    (WorkoutExperience.intermediate, FitnessGoal.muscle_gain): VolumeSpec(3, "10-15", 60, 1.3),
    (WorkoutExperience.intermediate, FitnessGoal.maintenance): VolumeSpec(3, "12", 60, 1.3),
    (WorkoutExperience.intermediate, FitnessGoal.general_fitness): VolumeSpec(3, "12", 60, 1.3),
    (WorkoutExperience.advanced, FitnessGoal.weight_loss): VolumeSpec(3, "15-20", 30, 0.8),
    (WorkoutExperience.advanced, FitnessGoal.muscle_gain): VolumeSpec(4, "10-12", 60, 1.3),
    (WorkoutExperience.advanced, FitnessGoal.maintenance): VolumeSpec(3, "12", 60, 1.3),
    (WorkoutExperience.advanced, FitnessGoal.general_fitness): VolumeSpec(3, "12-15", 60, 1.3),
}

# Number of exercises per day by experience
_EXERCISES_PER_DAY: dict[WorkoutExperience, int] = {
    WorkoutExperience.beginner: 4,
    WorkoutExperience.intermediate: 5,
    WorkoutExperience.advanced: 6,
}

# ---------------------------------------------------------------------------
# Day templates per split
# Each entry: (day_name, focus_area, [muscle_groups_in_priority_order])
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DayTemplate:
    day_name: str
    focus_area: str
    muscle_groups: list[str]  # MuscleGroup values, priority order
    is_compound_first: bool = True  # compound exercises selected before isolation


_SPLIT_TEMPLATES: dict[str, list[DayTemplate]] = {
    "Push Pull Legs": [
        DayTemplate("Day 1 — Push", "Chest, Shoulders & Triceps", ["chest", "shoulders", "arms"]),
        DayTemplate("Day 2 — Pull", "Back & Biceps", ["back", "arms"]),
        DayTemplate("Day 3 — Legs", "Legs & Core", ["legs", "core"]),
        DayTemplate("Day 4 — Push", "Chest, Shoulders & Triceps", ["chest", "shoulders", "arms"]),
        DayTemplate("Day 5 — Pull", "Back & Biceps", ["back", "arms"]),
        DayTemplate("Day 6 — Legs", "Legs & Core", ["legs", "core"]),
    ],
    "Upper Lower": [
        DayTemplate("Day 1 — Upper", "Chest, Back & Arms", ["chest", "back", "shoulders", "arms"]),
        DayTemplate("Day 2 — Lower", "Legs & Core", ["legs", "core"]),
        DayTemplate("Day 3 — Upper", "Chest, Back & Arms", ["chest", "back", "shoulders", "arms"]),
        DayTemplate("Day 4 — Lower", "Legs & Core", ["legs", "core"]),
        DayTemplate("Day 5 — Upper", "Chest, Back & Arms", ["chest", "back", "shoulders", "arms"]),
    ],
    "Full Body": [
        DayTemplate(
            "Day 1 — Full Body", "Full Body", ["chest", "back", "legs", "shoulders", "arms", "core"]
        ),
        DayTemplate(
            "Day 2 — Full Body", "Full Body", ["legs", "back", "chest", "core", "shoulders", "arms"]
        ),
        DayTemplate(
            "Day 3 — Full Body", "Full Body", ["back", "chest", "legs", "arms", "core", "shoulders"]
        ),
        DayTemplate(
            "Day 4 — Full Body", "Full Body", ["chest", "back", "legs", "shoulders", "arms", "core"]
        ),
        DayTemplate(
            "Day 5 — Full Body", "Full Body", ["legs", "back", "chest", "core", "shoulders", "arms"]
        ),
    ],
    "Bro Split": [
        DayTemplate("Day 1 — Chest", "Chest", ["chest"]),
        DayTemplate("Day 2 — Back", "Back", ["back"]),
        DayTemplate("Day 3 — Shoulders", "Shoulders", ["shoulders"]),
        DayTemplate("Day 4 — Arms", "Biceps & Triceps", ["arms"]),
        DayTemplate("Day 5 — Legs", "Legs & Core", ["legs", "core"]),
        DayTemplate("Day 6 — Chest", "Chest", ["chest"]),
    ],
    "Upper Lower Strength": [
        DayTemplate(
            "Day 1 — Upper Strength", "Chest, Back & Shoulders", ["chest", "back", "shoulders"]
        ),
        DayTemplate("Day 2 — Lower Strength", "Legs & Core", ["legs", "core"]),
        DayTemplate(
            "Day 3 — Upper Strength", "Chest, Back & Shoulders", ["back", "chest", "shoulders"]
        ),
        DayTemplate("Day 4 — Lower Strength", "Legs & Core", ["legs", "core"]),
    ],
    "Home Bodyweight Split": [
        DayTemplate(
            "Day 1 — Upper Body", "Chest, Shoulders & Arms", ["chest", "shoulders", "arms"]
        ),
        DayTemplate("Day 2 — Lower Body", "Legs & Core", ["legs", "core"]),
        DayTemplate("Day 3 — Full Body", "Full Body Circuit", ["chest", "back", "legs", "core"]),
        DayTemplate("Day 4 — Core & Back", "Back & Core", ["back", "core"]),
        # Days 5-7 cycle back through the same 4-day rotation — this is the
        # only split whose `max_days` (in workout_splits.py) is 7, so it's
        # the only one that must support that many templates. Every other
        # split's template list length already exactly matches its own
        # `max_days` (Push Pull Legs: 6/6, Bro Split: 6/6, etc.) — this
        # split previously had only 4 templates while claiming max_days=7,
        # so requesting a 7-day plan silently produced a 4-day plan with a
        # `workout_days: 7` label on it. Fixed by extending the cycle,
        # matching the same "repeat the rotation" convention Push Pull Legs
        # and Bro Split already use for their own repeat days.
        DayTemplate(
            "Day 5 — Upper Body", "Chest, Shoulders & Arms", ["chest", "shoulders", "arms"]
        ),
        DayTemplate("Day 6 — Lower Body", "Legs & Core", ["legs", "core"]),
        DayTemplate("Day 7 — Full Body", "Full Body Circuit", ["chest", "back", "legs", "core"]),
    ],
}

# ---------------------------------------------------------------------------
# Equipment bridge: map user Equipment enum → allowed ExerciseEquipment values
# ---------------------------------------------------------------------------

_EQUIPMENT_BRIDGE: dict[Equipment, set[str]] = {
    Equipment.none: {"bodyweight"},
    Equipment.resistance_bands: {"bodyweight", "resistance_bands"},
    Equipment.pull_up_bar: {"bodyweight", "pull_up_bar"},
    Equipment.dumbbells: {"bodyweight", "dumbbells"},
    Equipment.barbell: {"bodyweight", "dumbbells", "barbell", "bench"},
    Equipment.full_gym: {
        "bodyweight",
        "dumbbells",
        "barbell",
        "kettlebell",
        "resistance_bands",
        "machine",
        "cable",
        "bench",
        "pull_up_bar",
    },
}


def _allowed_equipment(user_equipment: list[str]) -> set[str]:
    """Union of all ExerciseEquipment values allowed by the user's gear."""
    allowed: set[str] = set()
    for item in user_equipment:
        try:
            allowed |= _EQUIPMENT_BRIDGE.get(Equipment(item), {"bodyweight"})
        except ValueError:
            allowed.add("bodyweight")
    # Always include bodyweight — no equipment can ever block it
    allowed.add("bodyweight")
    return allowed


# ---------------------------------------------------------------------------
# Exercise selector
# ---------------------------------------------------------------------------


def _select_exercises(
    db: Session,
    muscle_groups: list[str],
    allowed_eq: set[str],
    experience: WorkoutExperience,
    n: int,
    already_used: set[str],
) -> list[Exercise]:
    """Pick up to `n` exercises from `muscle_groups` (tried in order), filtered
    by allowed equipment and experience-appropriate difficulty.

    Selection logic:
    - Difficulty filter: beginners get beginner + intermediate; advanced get all.
    - Within a muscle group, compound exercises are preferred first.
    - Already-used exercise IDs are excluded to avoid consecutive-day duplicates.
    - Falls back to used exercises if not enough fresh ones exist (edge case on
      small equipment sets / bodyweight-only plans).
    """
    # Allowed difficulties
    if experience == WorkoutExperience.beginner:
        ok_difficulty = {Difficulty.beginner.value, Difficulty.intermediate.value}
    elif experience == WorkoutExperience.intermediate:
        ok_difficulty = {
            Difficulty.beginner.value,
            Difficulty.intermediate.value,
            Difficulty.advanced.value,
        }
    else:
        ok_difficulty = {
            Difficulty.beginner.value,
            Difficulty.intermediate.value,
            Difficulty.advanced.value,
        }

    selected: list[Exercise] = []
    used_groups: list[str] = []  # track which groups we've pulled from

    for group in muscle_groups:
        if len(selected) >= n:
            break
        # Fetch all eligible exercises for this group
        candidates = exercise_repository.list_exercises(db, muscle_group=group)  # type: ignore[arg-type]
        candidates = [
            e for e in candidates if e.equipment in allowed_eq and e.difficulty in ok_difficulty
        ]
        # Sort: compounds first, then by name for determinism
        candidates.sort(key=lambda e: (not e.is_compound, e.name))

        # Prefer not-yet-used
        fresh = [e for e in candidates if e.id not in already_used]
        pool = fresh if fresh else candidates

        # How many to take from this group — distribute slots across groups
        remaining_slots = n - len(selected)
        remaining_groups = len(muscle_groups) - len(used_groups)
        take = max(1, remaining_slots // max(remaining_groups, 1))
        take = min(take, len(pool))

        # Shuffle isolation exercises slightly for variety; keep compounds anchored
        compounds = [e for e in pool if e.is_compound]
        isolations = [e for e in pool if not e.is_compound]
        random.shuffle(isolations)
        ordered = compounds + isolations

        selected.extend(ordered[:take])
        used_groups.append(group)

    # If we still need more (e.g. a single-muscle-group bro-split day), pull more
    # from the first group
    if len(selected) < n and muscle_groups:
        shortfall = n - len(selected)
        extra = exercise_repository.list_exercises(db, muscle_group=muscle_groups[0])  # type: ignore[arg-type]
        extra = [
            e
            for e in extra
            if e.equipment in allowed_eq
            and e.difficulty in ok_difficulty
            and e.id not in {x.id for x in selected}
        ]
        selected.extend(extra[:shortfall])

    return selected[:n]


# ---------------------------------------------------------------------------
# Volume resolver
# ---------------------------------------------------------------------------


def _resolve_volume(
    exercise: Exercise,
    experience: WorkoutExperience,
    goal: FitnessGoal,
) -> VolumeSpec:
    """Return the sets/reps/rest appropriate for this exercise placement."""
    table = _STRENGTH_VOLUME if exercise.is_compound else _ISOLATION_VOLUME
    key = (experience, goal)
    # Fallback: intermediate + general_fitness if the key somehow isn't there
    return table.get(
        key,
        table.get(
            (WorkoutExperience.intermediate, FitnessGoal.general_fitness),
            VolumeSpec(3, "12", 60, 1.5),
        ),
    )


# ---------------------------------------------------------------------------
# Duration estimator
# ---------------------------------------------------------------------------


def _estimate_duration(days: list[dict], experience: WorkoutExperience, goal: FitnessGoal) -> int:
    """Estimate total session duration in minutes for a single day (we return
    the average across all days, rounded to the nearest 5 minutes)."""
    if not days:
        return 45
    total_minutes_per_day: list[float] = []
    warmup = 5.0
    cooldown = 5.0
    for day in days:
        day_minutes = warmup + cooldown
        for ex_entry in day.get("exercises", []):
            exercise = ex_entry["exercise"]
            spec = _resolve_volume(exercise, experience, goal)
            day_minutes += spec.sets * spec.minutes_per_set
        total_minutes_per_day.append(day_minutes)

    avg = sum(total_minutes_per_day) / len(total_minutes_per_day)
    # Round to nearest 5
    return int(round(avg / 5) * 5)


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class WorkoutPlannerService:
    """Converts a `RecommendationResponse` into a persisted `WorkoutPlan`.

    Designed to be instantiated once (no mutable state after __init__) and
    called per-request — same pattern as `WorkoutRecommendationService`.
    """

    def generate_and_save(
        self,
        db: Session,
        user_id: str,
        user_equipment: list[str],
        recommendation: RecommendationResponse,
        fitness_goal: FitnessGoal,
    ) -> GeneratedWorkoutPlanResponse:
        """Full pipeline: select exercises → build day structure → deactivate
        old plan → persist new plan → return enriched response."""

        experience = WorkoutExperience(recommendation.difficulty.lower())
        split_name = recommendation.split_name
        n_days = recommendation.workout_days
        allowed_eq = _allowed_equipment(user_equipment)
        n_exercises = _EXERCISES_PER_DAY[experience]

        # Get day templates for this split, trimmed to the requested day count
        templates = _SPLIT_TEMPLATES.get(split_name, _SPLIT_TEMPLATES["Full Body"])
        templates = templates[:n_days]

        # Build the day/exercise structure in memory first (no DB writes yet)
        # so we can compute duration before committing anything
        day_plans: list[dict] = []
        used_exercise_ids: set[str] = set()

        for tmpl in templates:
            exercises = _select_exercises(
                db=db,
                muscle_groups=tmpl.muscle_groups,
                allowed_eq=allowed_eq,
                experience=experience,
                n=n_exercises,
                already_used=used_exercise_ids,
            )
            # Track used IDs for the next day (anti-duplicate)
            used_exercise_ids = {e.id for e in exercises}

            day_plans.append(
                {
                    "template": tmpl,
                    "exercises": [{"exercise": e} for e in exercises],
                }
            )

        estimated_duration = _estimate_duration(day_plans, experience, fitness_goal)

        # --- Persistence ---
        # 1. Deactivate any currently active plan (preserve history)
        workout_plan_repository.deactivate_all(db, user_id)

        # 2. Create the plan row
        plan = workout_plan_repository.create(
            db,
            user_id=user_id,
            fields={
                "title": recommendation.title,
                "goal": fitness_goal,
                "experience": experience,
                "workout_days": n_days,
                "active": True,
            },
        )

        # 3. Create days + exercises
        all_day_responses: list[WorkoutDayResponse] = []
        for day_number, day_data in enumerate(day_plans, start=1):
            tmpl = day_data["template"]
            day = workout_day_repository.create(
                db,
                workout_plan_id=plan.id,
                fields={
                    "day_number": day_number,
                    "day_name": tmpl.day_name,
                    "focus_area": tmpl.focus_area,
                },
            )

            ex_responses: list[WorkoutExerciseResponse] = []
            for order_idx, ex_entry in enumerate(day_data["exercises"]):
                exercise: Exercise = ex_entry["exercise"]
                spec = _resolve_volume(exercise, experience, fitness_goal)

                we = workout_exercise_repository.create(
                    db,
                    workout_day_id=day.id,
                    fields={
                        "exercise_id": exercise.id,
                        "sets": spec.sets,
                        "reps": spec.reps,
                        "rest_seconds": spec.rest_seconds,
                        "order_index": order_idx,
                    },
                )

                ex_responses.append(
                    WorkoutExerciseResponse(
                        id=we.id,
                        workout_day_id=we.workout_day_id,
                        sets=we.sets,
                        reps=we.reps,
                        rest_seconds=we.rest_seconds,
                        order_index=we.order_index,
                        exercise=ExerciseResponse.model_validate(exercise),
                    )
                )

            all_day_responses.append(
                WorkoutDayResponse(
                    id=day.id,
                    workout_plan_id=day.workout_plan_id,
                    day_number=day.day_number,
                    day_name=day.day_name,
                    focus_area=day.focus_area,
                    workout_exercises=ex_responses,
                )
            )

        return GeneratedWorkoutPlanResponse(
            id=plan.id,
            user_id=plan.user_id,
            title=plan.title,
            goal=plan.goal,
            experience=plan.experience,
            workout_days=plan.workout_days,
            active=plan.active,
            created_at=plan.created_at,
            days=all_day_responses,
            split_name=split_name,
            difficulty=recommendation.difficulty,
            estimated_duration_minutes=estimated_duration,
            # Carried straight through from the RecommendationResponse this
            # method already receives — see workout_recommendation_service.py
            # for where these actually get computed (engine/confidence/
            # latency_ms/model_version/explanation).
            engine=recommendation.engine,
            confidence=recommendation.confidence,
            latency_ms=recommendation.latency_ms,
            model_version=recommendation.model_version,
            explanation=recommendation.explanation,
        )
