"""`WorkoutTrackingService` — turns a `WorkoutPlan`/`WorkoutDay` (Milestone
2.3) into something a user can actually *do*: start today's workout, mark
exercises complete or skipped, pause/resume, finish, and look back at
history.

Architecture note: this service depends on `workout_plan_repository` and
`workout_day_repository` (read-only) the same way `WorkoutPlannerService`
does — it doesn't duplicate plan-generation logic, only consumes its output.
The "what is today's workout day" calculation is intentionally re-derived
here rather than imported from `app/api/v1/routers/workouts.py`, since that
logic currently lives inline in a route handler, not an importable function —
extracting it would mean editing an existing, already-tested file for a
~10-line gain, which the project's "do not rewrite existing functionality"
rule argues against. The duplication is small and self-contained; see
`_get_todays_day` below.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.enums import WorkoutSessionStatus
from app.models.exercise_completion import ExerciseCompletion
from app.models.profile import Profile
from app.models.workout_day import WorkoutDay
from app.models.workout_plan import WorkoutPlan
from app.models.workout_session import WorkoutSession
from app.repositories import (
    exercise_completion_repository,
    workout_exercise_repository,
    workout_plan_repository,
    workout_session_repository,
)
from app.schemas.workout_session import ExerciseCompletionRequest, FinishWorkoutResponse

# A moderate resistance-training MET (Metabolic Equivalent of Task) value —
# a standard, citable estimate ("Compendium of Physical Activities") rather
# than a number invented for this project. calories = MET * weight_kg *
# duration_hours is the conventional formula behind most fitness trackers'
# "calories burned" estimates; it's an estimate, not a measurement, which is
# exactly what the field name (`calories_burned_estimate`) says.
_RESISTANCE_TRAINING_MET = 5.0

_ALREADY_COMPLETED_MESSAGE = "A completed workout cannot be modified."


def _get_todays_day(db: Session, plan: WorkoutPlan) -> WorkoutDay | None:
    """Same day-of-week mapping as `GET /workouts/today` (see that router for
    the canonical explanation): ISO weekday (1=Mon…7=Sun) mapped by position
    onto the plan's ordered training days. Returns `None` on a rest day."""
    today_iso = datetime.now().isoweekday()
    day_index = (today_iso - 1) % plan.workout_days

    if not plan.days:
        return None
    sorted_days = sorted(plan.days, key=lambda d: d.day_number)
    if day_index >= len(sorted_days):
        return None
    return sorted_days[day_index]


def _elapsed_seconds_since(start: datetime) -> int:
    now = datetime.now(UTC)
    # SQLite returns naive datetimes; treat them as UTC (everything in this
    # app is written/read as UTC — see `TimestampMixin`) so subtraction never
    # raises on naive-vs-aware mismatch.
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return max(0, int((now - start).total_seconds()))


def _require_owned_session(db: Session, user_id: str, session_id: str) -> WorkoutSession:
    """Fetches a session and verifies it belongs to the requesting user.
    Returns the same 404 for "doesn't exist" and "belongs to someone else" —
    same enumeration-avoidance pattern `auth_service` already uses for
    login."""
    session = workout_session_repository.get_by_id(db, session_id)
    if session is None or session.user_id != user_id:
        raise NotFoundError("Workout session not found.")
    return session


def _get_or_create_completion(
    db: Session, *, session_id: str, workout_exercise_id: str
) -> ExerciseCompletion:
    existing = exercise_completion_repository.get_by_session_and_exercise(
        db, session_id=session_id, workout_exercise_id=workout_exercise_id
    )
    if existing is not None:
        return existing
    return exercise_completion_repository.create(
        db,
        fields={
            "workout_session_id": session_id,
            "workout_exercise_id": workout_exercise_id,
            "completed_sets": 0,
            "completed": False,
            "skipped": False,
        },
    )


class WorkoutTrackingService:
    """Stateless — same pattern as `WorkoutPlannerService`/
    `WorkoutRecommendationService`: no instance state, safe to share a single
    instance across requests."""

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    def start_session(self, db: Session, user_id: str) -> WorkoutSession:
        plan = workout_plan_repository.get_active_by_user(db, user_id)
        if plan is None:
            raise NotFoundError(
                "No active workout plan found. Generate one at POST /workouts/generate."
            )

        today_day = _get_todays_day(db, plan)
        if today_day is None:
            raise ValidationError("Today is a rest day. Enjoy the recovery!")

        existing = workout_session_repository.get_active_or_paused_for_user(db, user_id)
        if existing is not None:
            raise ConflictError(
                "You already have an active workout session. "
                "Finish it before starting a new one."
            )

        return workout_session_repository.create(
            db,
            user_id=user_id,
            fields={
                "workout_plan_id": plan.id,
                "workout_day_id": today_day.id,
                "status": WorkoutSessionStatus.active,
            },
        )

    # ------------------------------------------------------------------
    # Pause / resume
    # ------------------------------------------------------------------
    # Not in the milestone's literal API list, but explicitly required by its
    # feature list ("Pause and resume workouts") — there's no way to expose
    # that capability without endpoints, so two were added:
    # POST /workouts/{session_id}/pause and .../resume. Both follow the same
    # auth/ownership/status-guard shape as every other tracking endpoint.

    def pause_session(self, db: Session, user_id: str, session_id: str) -> WorkoutSession:
        session = _require_owned_session(db, user_id, session_id)
        if session.status == WorkoutSessionStatus.completed:
            raise ConflictError(_ALREADY_COMPLETED_MESSAGE)
        if session.status == WorkoutSessionStatus.paused:
            raise ConflictError("This workout session is already paused.")

        elapsed = _elapsed_seconds_since(session.last_resumed_at)
        return workout_session_repository.update(
            db,
            session=session,
            fields={
                "accumulated_active_seconds": session.accumulated_active_seconds + elapsed,
                "status": WorkoutSessionStatus.paused,
            },
        )

    def resume_session(self, db: Session, user_id: str, session_id: str) -> WorkoutSession:
        session = _require_owned_session(db, user_id, session_id)
        if session.status == WorkoutSessionStatus.completed:
            raise ConflictError(_ALREADY_COMPLETED_MESSAGE)
        if session.status == WorkoutSessionStatus.active:
            raise ConflictError("This workout session is already active.")

        return workout_session_repository.update(
            db,
            session=session,
            fields={
                "status": WorkoutSessionStatus.active,
                "last_resumed_at": datetime.now(UTC),
            },
        )

    # ------------------------------------------------------------------
    # Complete / skip an exercise
    # ------------------------------------------------------------------

    def complete_exercise(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        workout_exercise_id: str,
        data: ExerciseCompletionRequest,
    ) -> ExerciseCompletion:
        session = _require_owned_session(db, user_id, session_id)
        if session.status == WorkoutSessionStatus.completed:
            raise ConflictError(_ALREADY_COMPLETED_MESSAGE)

        workout_exercise = self._require_exercise_in_session(db, session, workout_exercise_id)

        completion = _get_or_create_completion(
            db, session_id=session_id, workout_exercise_id=workout_exercise_id
        )
        return exercise_completion_repository.update(
            db,
            completion=completion,
            fields={
                "completed": True,
                "skipped": False,
                "completed_sets": (
                    data.completed_sets
                    if data.completed_sets is not None
                    else workout_exercise.sets
                ),
                "completed_reps": data.completed_reps or workout_exercise.reps,
                "notes": data.notes,
            },
        )

    def skip_exercise(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        workout_exercise_id: str,
        data: ExerciseCompletionRequest,
    ) -> ExerciseCompletion:
        session = _require_owned_session(db, user_id, session_id)
        if session.status == WorkoutSessionStatus.completed:
            raise ConflictError(_ALREADY_COMPLETED_MESSAGE)

        self._require_exercise_in_session(db, session, workout_exercise_id)

        completion = _get_or_create_completion(
            db, session_id=session_id, workout_exercise_id=workout_exercise_id
        )
        return exercise_completion_repository.update(
            db,
            completion=completion,
            fields={
                "completed": False,
                "skipped": True,
                "notes": data.notes,
            },
        )

    def _require_exercise_in_session(
        self, db: Session, session: WorkoutSession, workout_exercise_id: str
    ):
        """Guards against marking an exercise complete/skipped that doesn't
        actually belong to this session's workout day — prevents a session
        from one day being polluted with another day's exercise IDs."""
        workout_exercise = workout_exercise_repository.get_by_id(db, workout_exercise_id)
        if workout_exercise is None or workout_exercise.workout_day_id != session.workout_day_id:
            raise NotFoundError("This exercise is not part of this workout session.")
        return workout_exercise

    # ------------------------------------------------------------------
    # Finish
    # ------------------------------------------------------------------

    def finish_session(
        self, db: Session, user_id: str, session_id: str, profile: Profile
    ) -> FinishWorkoutResponse:
        session = _require_owned_session(db, user_id, session_id)
        if session.status == WorkoutSessionStatus.completed:
            raise ConflictError(_ALREADY_COMPLETED_MESSAGE)

        total_seconds = session.accumulated_active_seconds
        if session.status == WorkoutSessionStatus.active:
            total_seconds += _elapsed_seconds_since(session.last_resumed_at)
        # If paused, the gap since the pause was already excluded by
        # `pause_session` — nothing further to add.

        total_minutes = round(total_seconds / 60)
        calories = round(_RESISTANCE_TRAINING_MET * profile.weight_kg * (total_seconds / 3600), 1)

        updated = workout_session_repository.update(
            db,
            session=session,
            fields={
                "status": WorkoutSessionStatus.completed,
                "completed_at": datetime.now(UTC),
                "total_duration_minutes": total_minutes,
                "calories_burned_estimate": calories,
                "accumulated_active_seconds": total_seconds,
            },
        )

        completions = exercise_completion_repository.list_by_session(db, session_id)
        exercises_completed = sum(1 for c in completions if c.completed)
        exercises_skipped = sum(1 for c in completions if c.skipped)

        return FinishWorkoutResponse(
            session=updated,
            total_duration_minutes=total_minutes,
            exercises_completed=exercises_completed,
            exercises_skipped=exercises_skipped,
            calories_burned_estimate=calories,
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, db: Session, user_id: str) -> list[WorkoutSession]:
        return workout_session_repository.list_history_for_user(db, user_id)

    def get_session_detail(self, db: Session, user_id: str, session_id: str) -> WorkoutSession:
        return _require_owned_session(db, user_id, session_id)
