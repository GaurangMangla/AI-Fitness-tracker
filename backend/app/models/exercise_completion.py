"""The `ExerciseCompletion` model — tracks one `WorkoutExercise`'s progress
within a single `WorkoutSession`.

One row is created lazily, the first time an exercise within a session is
either completed or skipped — not eagerly for every exercise on session
start. This keeps "the user hasn't touched this exercise yet" representable
as "no row exists" rather than needing a third boolean to distinguish
"not started" from "completed: false, skipped: false."
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.workout_session import WorkoutSession


class ExerciseCompletion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exercise_completions"

    workout_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # No `ondelete="CASCADE"` — same reasoning as `WorkoutExercise.exercise_id`:
    # a `WorkoutExercise` placement is plan data, not owned by any one
    # session's completion record.
    workout_exercise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_exercises.id"), nullable=False, index=True
    )
    completed_sets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_reps: Mapped[str | None] = mapped_column(String(20), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    workout_session: Mapped["WorkoutSession"] = relationship(back_populates="exercise_completions")
