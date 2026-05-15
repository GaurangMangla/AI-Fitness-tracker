"""The `Exercise` model — the shared exercise library.

Not user-owned (no `user_id`): every user reads from the same library.
`WorkoutExercise` (a different model, despite the similar name) is what
attaches a specific exercise to a specific user's workout plan with
plan-specific overrides (sets/reps/rest for that placement) — see its
docstring for why those aren't just duplicated from here automatically.
"""

from sqlalchemy import Boolean, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Difficulty, ExerciseEquipment, ExerciseType, MuscleGroup


class Exercise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exercises"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    muscle_group: Mapped[MuscleGroup] = mapped_column(
        Enum(MuscleGroup, native_enum=False), nullable=False, index=True
    )
    equipment: Mapped[ExerciseEquipment] = mapped_column(
        Enum(ExerciseEquipment, native_enum=False), nullable=False, index=True
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, native_enum=False), nullable=False, index=True
    )
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    exercise_type: Mapped[ExerciseType] = mapped_column(
        Enum(ExerciseType, native_enum=False), nullable=False
    )
    default_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    # A string, not an int: reps are sometimes a range ("8-12") or a duration
    # ("30 sec") rather than a single number, especially for the cardio/core
    # exercises in this library — a plain int couldn't represent either.
    default_reps: Mapped[str] = mapped_column(String(20), nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_per_set: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_compound: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # `created_at` was the only timestamp the spec named for this model, but
    # `TimestampMixin` is used uniformly across every model in this codebase
    # (see e.g. `Profile`) rather than carving out a one-off exception here —
    # `updated_at` comes along for free and costs nothing to have.
