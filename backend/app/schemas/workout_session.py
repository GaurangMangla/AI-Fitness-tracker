"""Schemas for Milestone 2.5 — workout session tracking.

Follows the same `model_config = ConfigDict(from_attributes=True)` convention
as `app/schemas/workout.py` for every response model, so they serialize
directly from the ORM objects the service/repositories return.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WorkoutSessionStatus


# --- ExerciseCompletion -----------------------------------------------------------
class ExerciseCompletionRequest(BaseModel):
    """Body for both the complete and skip endpoints. All fields optional —
    a quick tap of "Skip" needs none of them; a careful "Complete" can record
    exactly what was done."""

    completed_sets: int | None = Field(default=None, ge=0, le=20)
    completed_reps: str | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)


class ExerciseCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workout_session_id: str
    workout_exercise_id: str
    completed_sets: int
    completed_reps: str | None
    completed: bool
    skipped: bool
    notes: str | None


# --- WorkoutSession ----------------------------------------------------------------
class WorkoutSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    workout_plan_id: str
    workout_day_id: str
    status: WorkoutSessionStatus
    started_at: datetime
    completed_at: datetime | None
    total_duration_minutes: int | None
    calories_burned_estimate: float | None
    exercise_completions: list[ExerciseCompletionResponse] = []
    # Exposed so the frontend live-timer can compute elapsed active seconds
    # correctly across pause/resume cycles without a separate polling endpoint.
    accumulated_active_seconds: int
    last_resumed_at: datetime


class FinishWorkoutResponse(BaseModel):
    """Summary returned by POST /workouts/{session_id}/finish — exactly the
    three figures the milestone spec asks for, plus the full session for
    anything else the frontend needs (e.g. listing which exercises were
    skipped)."""

    session: WorkoutSessionResponse
    total_duration_minutes: int
    exercises_completed: int
    exercises_skipped: int
    calories_burned_estimate: float
