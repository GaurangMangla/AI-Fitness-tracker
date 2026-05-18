"""Schemas for Progress and Nutrition modules."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DietPreference, MealType

# ── Progress ────────────────────────────────────────────────────────────────


class ProgressLogRequest(BaseModel):
    log_date: str | None = Field(default=None, description="ISO date YYYY-MM-DD; defaults to today")
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    body_fat_pct: float | None = Field(default=None, ge=1, le=70)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    notes: str | None = Field(default=None, max_length=500)


class ProgressLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    log_date: str
    weight_kg: float | None
    body_fat_pct: float | None
    sleep_hours: float | None
    notes: str | None
    created_at: datetime


class BodyMeasurementRequest(BaseModel):
    log_date: str | None = Field(default=None)
    chest_cm: float | None = Field(default=None, ge=40, le=200)
    waist_cm: float | None = Field(default=None, ge=40, le=200)
    hips_cm: float | None = Field(default=None, ge=40, le=200)
    left_arm_cm: float | None = Field(default=None, ge=10, le=100)
    right_arm_cm: float | None = Field(default=None, ge=10, le=100)
    left_thigh_cm: float | None = Field(default=None, ge=20, le=150)
    right_thigh_cm: float | None = Field(default=None, ge=20, le=150)


class BodyMeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    log_date: str
    chest_cm: float | None
    waist_cm: float | None
    hips_cm: float | None
    left_arm_cm: float | None
    right_arm_cm: float | None
    left_thigh_cm: float | None
    right_thigh_cm: float | None
    created_at: datetime


class ProgressSummaryResponse(BaseModel):
    current_weight_kg: float | None
    current_body_fat_pct: float | None
    last_sleep_hours: float | None
    weight_change_30d_kg: float | None
    total_logs: int
    weight_entries: int


# ── Nutrition ───────────────────────────────────────────────────────────────


class MealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    meal_type: MealType
    name: str
    description: str | None
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


class NutritionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    diet_type: DietPreference
    active: bool
    target_calories: int
    target_protein_g: float
    target_carbs_g: float
    target_fat_g: float
    target_water_ml: int
    meals: list[MealResponse] = []
    created_at: datetime


class NutritionLogRequest(BaseModel):
    log_date: str | None = Field(default=None)
    calories_consumed: int = Field(ge=0, le=10000)
    protein_g: float = Field(ge=0, le=500)
    carbs_g: float = Field(ge=0, le=1000)
    fat_g: float = Field(ge=0, le=500)
    water_ml: int = Field(default=0, ge=0, le=10000)
    notes: str | None = Field(default=None, max_length=500)


class NutritionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    log_date: str
    calories_consumed: int
    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: int
    notes: str | None
    created_at: datetime


class NutritionWeeklySummary(BaseModel):
    avg_calories: int
    avg_protein_g: float
    avg_carbs_g: float
    avg_fat_g: float
    days_logged: int


class WorkoutStatsResponse(BaseModel):
    total_sessions: int
    total_minutes: int
    total_calories_burned: float
    total_exercises_completed: int
    current_streak_days: int
    longest_streak_days: int
    sessions_last_7_days: int
    sessions_last_30_days: int
    avg_session_minutes: float
    avg_calories_per_session: float
