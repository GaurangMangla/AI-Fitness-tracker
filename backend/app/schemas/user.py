"""Schemas for `/users/me` (GET and PATCH) and the profile data nested inside it."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ActivityLevel,
    DietPreference,
    Equipment,
    FitnessGoal,
    Gender,
    WorkoutExperience,
)


class ProfileUpdate(BaseModel):
    """Request body for `PATCH /users/me`.

    Every field is optional — true PATCH semantics, so a later "edit my
    weight" call from a settings page can send just `{"weight_kg": 72.5}`.
    The onboarding form happens to send every field at once on a user's first
    submission, but the schema doesn't assume that; `user_service.update_profile`
    is what enforces that a *first* submission must be complete (see there for
    why that check belongs in the service layer, not here).
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=13, le=100)
    gender: Gender | None = None
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=30, le=300)
    fitness_goal: FitnessGoal | None = None
    activity_level: ActivityLevel | None = None
    workout_experience: WorkoutExperience | None = None
    equipment_available: list[Equipment] | None = Field(default=None, min_length=1)
    diet_preference: DietPreference | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    age: int
    gender: Gender
    height_cm: float
    weight_kg: float
    fitness_goal: FitnessGoal
    activity_level: ActivityLevel
    workout_experience: WorkoutExperience
    equipment_available: list[Equipment]
    diet_preference: DietPreference


class ProfileMetrics(BaseModel):
    """Derived, not stored — recomputed from the profile on every request so
    it's never at risk of going stale relative to the latest height/weight."""

    bmi: float
    bmi_category: str
    daily_calories: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime
    profile: ProfileResponse | None = None
    metrics: ProfileMetrics | None = None
