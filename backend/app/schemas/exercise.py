"""Schemas for the exercise library.

`ExerciseCreate` has no public endpoint yet — it exists so the seed script
(`app/db/seed_exercises.py`) and `exercise_service.create_exercise` go through
the same validated shape that a future admin-facing create endpoint would use,
rather than the seed script poking the ORM/repository directly with raw dicts.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Difficulty, ExerciseEquipment, ExerciseType, MuscleGroup


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    muscle_group: MuscleGroup
    equipment: ExerciseEquipment
    difficulty: Difficulty
    instructions: str = Field(min_length=1)
    exercise_type: ExerciseType
    default_sets: int = Field(ge=1, le=20)
    default_reps: str = Field(min_length=1, max_length=20)
    rest_seconds: int = Field(ge=0, le=600)
    calories_per_set: float | None = Field(default=None, ge=0)
    is_compound: bool = False


class ExerciseUpdate(BaseModel):
    """Every field optional — partial update, same pattern as `ProfileUpdate`."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    muscle_group: MuscleGroup | None = None
    equipment: ExerciseEquipment | None = None
    difficulty: Difficulty | None = None
    instructions: str | None = Field(default=None, min_length=1)
    exercise_type: ExerciseType | None = None
    default_sets: int | None = Field(default=None, ge=1, le=20)
    default_reps: str | None = Field(default=None, min_length=1, max_length=20)
    rest_seconds: int | None = Field(default=None, ge=0, le=600)
    calories_per_set: float | None = Field(default=None, ge=0)
    is_compound: bool | None = None


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    muscle_group: MuscleGroup
    equipment: ExerciseEquipment
    difficulty: Difficulty
    instructions: str
    exercise_type: ExerciseType
    default_sets: int
    default_reps: str
    rest_seconds: int
    calories_per_set: float | None
    is_compound: bool
    created_at: datetime
