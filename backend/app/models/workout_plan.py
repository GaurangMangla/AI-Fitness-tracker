"""The `WorkoutPlan` model — a user's generated workout program.

Belongs to a `User` via `user_id`, but the relationship is declared
one-directionally (no `back_populates` on `User`, and `app/models/user.py`
is not touched by this migration) — this milestone's instructions are
explicit about not modifying existing functionality unless required, and a
one-directional FK relationship is all that's actually required to model
"a plan belongs to a user." `User.workout_plans` can be added later if/when
something needs to navigate user → plans directly.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FitnessGoal, WorkoutExperience

if TYPE_CHECKING:
    from app.models.workout_day import WorkoutDay


class WorkoutPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workout_plans"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    # Reuses the same enums as `Profile.fitness_goal`/`Profile.workout_experience`
    # — a plan's goal/experience level is the same vocabulary as the user's,
    # just possibly captured at plan-creation time rather than read live off
    # the profile (a user's profile can change after a plan was generated).
    goal: Mapped[FitnessGoal] = mapped_column(Enum(FitnessGoal, native_enum=False), nullable=False)
    experience: Mapped[WorkoutExperience] = mapped_column(
        Enum(WorkoutExperience, native_enum=False), nullable=False
    )
    workout_days: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    days: Mapped[list["WorkoutDay"]] = relationship(
        back_populates="workout_plan",
        cascade="all, delete-orphan",
        order_by="WorkoutDay.day_number",
    )
