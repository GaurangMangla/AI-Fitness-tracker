"""Schemas for the workout-plan hierarchy (`WorkoutPlan` → `WorkoutDay` →
`WorkoutExercise`). No router uses these yet — only the CRUD services and
their tests do, in this milestone. They exist now so the service layer's
function signatures are already shaped the way a future API layer will need
them, rather than being designed twice.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FitnessGoal, WorkoutExperience
from app.schemas.exercise import ExerciseResponse
from app.schemas.recommendation import RecommendationExplanation


# --- WorkoutExercise -----------------------------------------------------------
class WorkoutExerciseCreate(BaseModel):
    exercise_id: str
    sets: int = Field(ge=1, le=20)
    reps: str = Field(min_length=1, max_length=20)
    rest_seconds: int = Field(ge=0, le=600)
    order_index: int = Field(ge=0)


class WorkoutExerciseUpdate(BaseModel):
    sets: int | None = Field(default=None, ge=1, le=20)
    reps: str | None = Field(default=None, min_length=1, max_length=20)
    rest_seconds: int | None = Field(default=None, ge=0, le=600)
    order_index: int | None = Field(default=None, ge=0)


class WorkoutExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workout_day_id: str
    sets: int
    reps: str
    rest_seconds: int
    order_index: int
    exercise: ExerciseResponse


# --- WorkoutDay ------------------------------------------------------------------
class WorkoutDayCreate(BaseModel):
    day_number: int = Field(ge=1, le=7)
    day_name: str = Field(min_length=1, max_length=100)
    focus_area: str = Field(min_length=1, max_length=100)


class WorkoutDayUpdate(BaseModel):
    day_number: int | None = Field(default=None, ge=1, le=7)
    day_name: str | None = Field(default=None, min_length=1, max_length=100)
    focus_area: str | None = Field(default=None, min_length=1, max_length=100)


class WorkoutDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workout_plan_id: str
    day_number: int
    day_name: str
    focus_area: str
    workout_exercises: list[WorkoutExerciseResponse] = []


# --- WorkoutPlan -----------------------------------------------------------------
class WorkoutPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    goal: FitnessGoal
    experience: WorkoutExperience
    workout_days: int = Field(ge=1, le=7)
    active: bool = True


class WorkoutPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    goal: FitnessGoal | None = None
    experience: WorkoutExperience | None = None
    workout_days: int | None = Field(default=None, ge=1, le=7)
    active: bool | None = None


class WorkoutPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    goal: FitnessGoal
    experience: WorkoutExperience
    workout_days: int
    active: bool
    created_at: datetime
    days: list[WorkoutDayResponse] = []


# --- Generate endpoint -----------------------------------------------------------
class GenerateWorkoutRequest(BaseModel):
    """Request body for POST /workouts/generate.

    `workout_days_per_week` is required here for the same reason it's a
    request field on /workouts/recommend: the Profile model has no such
    column (added after the fact would need a migration), so it's taken
    directly from the caller instead of read from the DB.
    """

    workout_days_per_week: int = Field(
        ge=1, le=7, description="How many days per week the user wants to train."
    )


class GeneratedWorkoutPlanResponse(BaseModel):
    """Enriched response for POST /workouts/generate — adds computed fields
    (split_name, difficulty, estimated_duration_minutes) on top of the
    plain WorkoutPlanResponse so the frontend has everything it needs to
    render the plan without a second request."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    goal: FitnessGoal
    experience: WorkoutExperience
    workout_days: int
    active: bool
    created_at: datetime
    days: list[WorkoutDayResponse] = []
    # Computed at generation time, not stored in the DB — returned here
    # so the frontend can display them without deriving them client-side.
    split_name: str
    difficulty: str
    estimated_duration_minutes: int

    # --- Added for the premium AI recommendation UI. Same fields, same
    # meaning, as RecommendationResponse (schemas/recommendation.py) — this
    # is the endpoint the frontend actually calls (POST /workouts/generate),
    # so the same engine/confidence/model-version/explanation metadata is
    # threaded through here too, copied directly from the RecommendationResponse
    # WorkoutPlannerService.generate_and_save() already receives. All
    # additive, all defaulted — existing clients reading only the fields
    # above are unaffected. ---
    engine: str = "rule"
    confidence: float | None = None
    latency_ms: float | None = None
    model_version: str | None = None
    explanation: RecommendationExplanation | None = None
