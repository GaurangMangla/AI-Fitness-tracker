"""Catalog of supported workout splits.

This is reference data the rule engine (`recommendation_rules.py`,
`recommendation_engine.py`) scores against. Adding a 7th split later means
adding one entry here — no rule function needs to change for that.

`ideal_days` are the day-counts this split is classically built around (used
to *score* candidates); `min_days`/`max_days` are the hard bounds outside of
which the split is disqualified entirely (used to *filter* candidates) — see
`recommendation_rules.workout_days_rule`.
"""

from dataclasses import dataclass

from app.models.enums import Difficulty, Equipment


@dataclass(frozen=True)
class WorkoutSplitDefinition:
    key: str
    split_name: str
    difficulty: Difficulty
    ideal_days: tuple[int, ...]
    min_days: int
    max_days: int
    # Any one of these satisfies the requirement. `None` means no hard
    # equipment requirement at all (the split works with whatever — or
    # nothing — the user has).
    requires_equipment: tuple[Equipment, ...] | None


WORKOUT_SPLITS: tuple[WorkoutSplitDefinition, ...] = (
    WorkoutSplitDefinition(
        key="push_pull_legs",
        split_name="Push Pull Legs",
        difficulty=Difficulty.intermediate,
        ideal_days=(3, 5, 6),
        min_days=3,
        max_days=6,
        requires_equipment=(Equipment.dumbbells, Equipment.barbell, Equipment.full_gym),
    ),
    WorkoutSplitDefinition(
        key="upper_lower",
        split_name="Upper Lower",
        difficulty=Difficulty.beginner,
        ideal_days=(4,),
        min_days=3,
        max_days=5,
        requires_equipment=(Equipment.dumbbells, Equipment.barbell, Equipment.full_gym),
    ),
    WorkoutSplitDefinition(
        key="full_body",
        split_name="Full Body",
        difficulty=Difficulty.beginner,
        ideal_days=(2, 3),
        min_days=1,
        max_days=5,
        requires_equipment=None,
    ),
    WorkoutSplitDefinition(
        key="bro_split",
        split_name="Bro Split",
        difficulty=Difficulty.advanced,
        ideal_days=(5,),
        min_days=5,
        max_days=6,
        requires_equipment=(Equipment.full_gym,),
    ),
    WorkoutSplitDefinition(
        key="upper_lower_strength",
        split_name="Upper Lower Strength",
        difficulty=Difficulty.advanced,
        ideal_days=(4,),
        min_days=3,
        max_days=4,
        requires_equipment=(Equipment.barbell, Equipment.full_gym),
    ),
    WorkoutSplitDefinition(
        key="home_bodyweight",
        split_name="Home Bodyweight Split",
        difficulty=Difficulty.beginner,
        ideal_days=(3, 4),
        min_days=1,
        max_days=7,
        # No hard requirement, and (see `recommendation_rules.equipment_rule`)
        # it's the one split that gets an explicit *scoring bonus* when the
        # user has no real equipment — making it the engine's guaranteed,
        # always-eligible fallback no matter how sparse the input is.
        requires_equipment=None,
    ),
)

SPLIT_BY_KEY: dict[str, WorkoutSplitDefinition] = {split.key: split for split in WORKOUT_SPLITS}
