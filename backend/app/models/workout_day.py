"""The `WorkoutDay` model — one training day within a `WorkoutPlan`
(e.g. "Day 1 — Push"). Holds an ordered list of `WorkoutExercise` rows.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.workout_exercise import WorkoutExercise
    from app.models.workout_plan import WorkoutPlan


class WorkoutDay(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workout_days"

    workout_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    day_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Free text ("Push", "Upper Body", "Chest & Triceps"), not a `MuscleGroup`
    # enum — a single day commonly spans more than one muscle group, which an
    # enum column couldn't represent without becoming a list, and the exact
    # wording here is presentational rather than something the app filters or
    # branches logic on.
    focus_area: Mapped[str] = mapped_column(String(100), nullable=False)

    workout_plan: Mapped["WorkoutPlan"] = relationship(back_populates="days")
    workout_exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout_day",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )
