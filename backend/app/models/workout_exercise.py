"""The `WorkoutExercise` model — join table between `WorkoutDay` and
`Exercise`, with its own `sets`/`reps`/`rest_seconds`.

These aren't just copied from `Exercise.default_sets`/`default_reps`/
`rest_seconds` and left alone: a plan generator (later milestone) adjusts
them per user — e.g. a beginner might get fewer sets than the exercise's
default. `Exercise` holds sensible *defaults*; `WorkoutExercise` holds what
was actually prescribed for this placement, in this plan, for this user.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.exercise import Exercise
    from app.models.workout_day import WorkoutDay


class WorkoutExercise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workout_exercises"

    workout_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # No `ondelete="CASCADE"` here on purpose: `Exercise` rows are shared
    # library data, not owned by any one plan. Deleting an exercise from the
    # library is not a path this milestone builds (no delete-exercise
    # endpoint), so the default FK behavior is never actually exercised —
    # but declaring it without cascade is the correct intent for when it is.
    exercise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exercises.id"), nullable=False, index=True
    )
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[str] = mapped_column(String(20), nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    workout_day: Mapped["WorkoutDay"] = relationship(back_populates="workout_exercises")
    exercise: Mapped["Exercise"] = relationship()
