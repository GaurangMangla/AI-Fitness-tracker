"""The `WorkoutSession` model — one user's attempt at completing a specific
`WorkoutDay`, on a specific occasion.

Belongs to a `User` via `user_id` and a `WorkoutDay` via `workout_day_id`,
both declared one-directionally (no `back_populates` on `User` or
`WorkoutDay`) — same convention `WorkoutPlan` already established for its
`User` relationship, kept consistent here rather than introduced freshly.
`workout_plan_id` is denormalized onto the session (rather than derived by
joining through `workout_day.workout_plan_id` every time) because workout
history needs to remain readable even if the plan itself is later deleted —
unlikely today (plans are only ever deactivated, never deleted), but cheap
insurance for a row that's meant to be permanent, append-only history.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WorkoutSessionStatus

if TYPE_CHECKING:
    from app.models.exercise_completion import ExerciseCompletion


class WorkoutSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workout_sessions"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[WorkoutSessionStatus] = mapped_column(
        Enum(WorkoutSessionStatus, native_enum=False),
        nullable=False,
        default=WorkoutSessionStatus.active,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Active *training* minutes only — a paused gap is excluded by the
    # service (see `WorkoutTrackingService`), so this is never a naive
    # `completed_at - started_at` calculation. Nullable until the session
    # finishes; null/None means "still in progress."
    total_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories_burned_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Accumulated active-time clock, in seconds, carried across pause/resume
    # cycles. Not part of the public API response — an internal bookkeeping
    # field the service reads/writes so `total_duration_minutes` excludes
    # paused time without needing a separate pause-log table for this scope.
    accumulated_active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Timestamp of the most recent active→active or resume tick; used to
    # compute the next slice of active time to add to
    # `accumulated_active_seconds` when the session is paused or finished.
    last_resumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    exercise_completions: Mapped[list["ExerciseCompletion"]] = relationship(
        back_populates="workout_session",
        cascade="all, delete-orphan",
    )
