"""Enums shared by `app.models` (as SQLAlchemy column types) and `app.schemas`
(as Pydantic field types) — defined once here so the two never drift out of
sync with each other.
"""

from enum import Enum


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class FitnessGoal(str, Enum):
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"
    general_fitness = "general_fitness"


class ActivityLevel(str, Enum):
    """Standard activity-level bands used for TDEE estimation — see
    `app/services/metrics_service.py` for the multiplier each one maps to."""

    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    extra_active = "extra_active"


class WorkoutExperience(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class WorkoutSessionStatus(str, Enum):
    """Lifecycle of a single `WorkoutSession` — one user's attempt at a
    specific `WorkoutDay` on a specific occasion. `paused` exists so a user
    can leave mid-workout and resume later without losing progress or the
    accumulated active-time clock (see `WorkoutTrackingService`)."""

    active = "active"
    paused = "paused"
    completed = "completed"


class DietPreference(str, Enum):
    vegetarian = "vegetarian"
    non_vegetarian = "non_vegetarian"
    vegan = "vegan"


class Equipment(str, Enum):
    """What gear a *user* has access to (profile onboarding). Deliberately a
    separate enum from `ExerciseEquipment` below — that one describes what a
    specific *exercise* requires, which needs finer granularity (e.g.
    "machine", "cable", "bench") than "what's in my gym bag" does. Forcing
    both concepts through one shared enum would be the wrong kind of reuse.
    """

    none = "none"
    dumbbells = "dumbbells"
    barbell = "barbell"
    resistance_bands = "resistance_bands"
    pull_up_bar = "pull_up_bar"
    full_gym = "full_gym"


class MuscleGroup(str, Enum):
    """The exercise library's organizing categories. "cardio" isn't literally
    a muscle group, but it's grouped here rather than in `ExerciseType`
    because it's how the library is browsed/filtered (alongside chest, back,
    etc.), matching how the exercise library was specified."""

    chest = "chest"
    back = "back"
    shoulders = "shoulders"
    legs = "legs"
    arms = "arms"
    core = "core"
    cardio = "cardio"


class ExerciseType(str, Enum):
    """Cross-cutting classification independent of muscle group — e.g. a
    "core" exercise could be `strength` (a weighted plank) or `mobility` (a
    stretch). Exists for filtering the library by training modality, not just
    body part."""

    strength = "strength"
    cardio = "cardio"
    mobility = "mobility"
    balance = "balance"


class ExerciseEquipment(str, Enum):
    """What a specific exercise requires — finer-grained than the profile's
    `Equipment` enum on purpose (see its docstring)."""

    bodyweight = "bodyweight"
    dumbbells = "dumbbells"
    barbell = "barbell"
    kettlebell = "kettlebell"
    resistance_bands = "resistance_bands"
    machine = "machine"
    cable = "cable"
    bench = "bench"
    pull_up_bar = "pull_up_bar"


class Difficulty(str, Enum):
    """An exercise's difficulty. The same three values as `WorkoutExperience`,
    kept as a distinct enum rather than reused — "this exercise is
    `beginner`-difficulty" and "this user is a `beginner`" are different
    concepts that happen to share a vocabulary, and a future change to one
    (e.g. adding an `elite` exercise difficulty) shouldn't be forced onto the
    other."""

    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
