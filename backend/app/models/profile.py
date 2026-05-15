"""The `Profile` model — onboarding and fitness data, one-to-one with `User`.

Design decisions:
- `equipment_available` is stored as a JSON column (a list of `Equipment`
  values), not a separate join table. A user has at most a handful of
  equipment items, it's never queried/filtered on independently in this
  milestone, and a join table would be real relational modeling for a
  problem this small — JSON is the right amount of structure here.
- The single-value fields (`gender`, `fitness_goal`, `activity_level`,
  `workout_experience`, `diet_preference`) use SQLAlchemy's `Enum` column
  type, which both validates at the database layer (a CHECK constraint on
  SQLite, a native enum type on Postgres) and stores the same way on either
  backend — consistent with this project's "stay Postgres-portable" rule.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    ActivityLevel,
    DietPreference,
    FitnessGoal,
    Gender,
    WorkoutExperience,
)

if TYPE_CHECKING:
    from app.models.user import User


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender, native_enum=False), nullable=False)
    height_cm: Mapped[float] = mapped_column(nullable=False)
    weight_kg: Mapped[float] = mapped_column(nullable=False)
    fitness_goal: Mapped[FitnessGoal] = mapped_column(
        Enum(FitnessGoal, native_enum=False), nullable=False
    )
    activity_level: Mapped[ActivityLevel] = mapped_column(
        Enum(ActivityLevel, native_enum=False), nullable=False
    )
    workout_experience: Mapped[WorkoutExperience] = mapped_column(
        Enum(WorkoutExperience, native_enum=False), nullable=False
    )
    equipment_available: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diet_preference: Mapped[DietPreference] = mapped_column(
        Enum(DietPreference, native_enum=False), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="profile")
