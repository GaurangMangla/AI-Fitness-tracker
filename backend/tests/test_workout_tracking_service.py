"""Unit tests for `WorkoutTrackingService`.

Exercises the service directly against a raw `db` session (the `db` fixture
from `conftest.py`), the same level `test_workout_planner_service.py` already
operates at — no HTTP layer, no auth, just the service + real repositories +
an in-memory SQLite DB.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.seed_exercises import seed_exercises
from app.models.enums import (
    ActivityLevel,
    DietPreference,
    Equipment,
    FitnessGoal,
    Gender,
    WorkoutExperience,
    WorkoutSessionStatus,
)
from app.models.profile import Profile
from app.models.user import User
from app.repositories import workout_session_repository
from app.schemas.recommendation import RecommendationResponse
from app.schemas.workout_session import ExerciseCompletionRequest
from app.services.workout_planner_service import WorkoutPlannerService
from app.services.workout_tracking_service import WorkoutTrackingService
from tests.factories import unique_email

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> WorkoutTrackingService:
    return WorkoutTrackingService()


@pytest.fixture
def user_with_plan(db: Session):
    """A user, their profile, and an active 7-day plan (7 days = always a
    training day, never a rest day — keeps the fixture deterministic
    regardless of what day the test actually runs on).

    Seeds the exercise library explicitly rather than relying on another
    test file's `client` fixture having already triggered it earlier in the
    run (it's idempotent — see `test_seed_exercises.py` — so calling it here
    too is harmless even when it's already populated)."""
    seed_exercises(db)

    user = User(email=unique_email("track"), password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        name="Tracker Test",
        age=30,
        gender=Gender.male,
        height_cm=180.0,
        weight_kg=80.0,
        fitness_goal=FitnessGoal.muscle_gain,
        activity_level=ActivityLevel.moderately_active,
        workout_experience=WorkoutExperience.intermediate,
        equipment_available=[Equipment.full_gym.value],
        diet_preference=DietPreference.non_vegetarian,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    recommendation = RecommendationResponse(
        title="Test Plan",
        # "Home Bodyweight Split" is the only split whose max_days (in
        # workout_splits.py) is actually 7 — it was previously hardcoded
        # here as "Push Pull Legs" (max_days=6), an impossible combination
        # the real /workouts/recommend endpoint could never produce, since
        # push_pull_legs would be disqualified outright for a 7-day
        # request. That mismatch caused the planner to silently generate
        # only 6 real days while this fixture's plan.workout_days still
        # claimed 7, so `_get_todays_day` could compute a day_index (0-6)
        # that pointed past the end of the 6-day list on certain weekdays
        # — the same class of bug fixed in workout_planner_service.py's
        # `_SPLIT_TEMPLATES`, but reintroduced here via a fixture that
        # bypassed the real recommendation step entirely.
        split_name="Home Bodyweight Split",
        workout_days=7,
        difficulty="Intermediate",
        reason="Test fixture.",
    )
    plan = WorkoutPlannerService().generate_and_save(
        db=db,
        user_id=user.id,
        user_equipment=profile.equipment_available,
        recommendation=recommendation,
        fitness_goal=profile.fitness_goal,
    )
    return user, profile, plan


# ---------------------------------------------------------------------------
# start_session
# ---------------------------------------------------------------------------


class TestStartSession:
    def test_creates_an_active_session_for_todays_day(self, db, service, user_with_plan):
        user, _, plan = user_with_plan
        session = service.start_session(db, user.id)

        assert session.status == WorkoutSessionStatus.active
        assert session.workout_plan_id == plan.id
        assert session.user_id == user.id
        assert session.completed_at is None

    def test_raises_not_found_without_a_plan(self, db, service):
        user = User(email=unique_email("noplan"), password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        with pytest.raises(NotFoundError):
            service.start_session(db, user.id)

    def test_raises_conflict_if_a_session_is_already_active(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        service.start_session(db, user.id)

        with pytest.raises(ConflictError):
            service.start_session(db, user.id)

    def test_raises_conflict_if_a_session_is_paused(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        session = service.start_session(db, user.id)
        service.pause_session(db, user.id, session.id)

        with pytest.raises(ConflictError):
            service.start_session(db, user.id)


# ---------------------------------------------------------------------------
# pause / resume
# ---------------------------------------------------------------------------


class TestPauseResume:
    def test_pause_sets_status_and_accumulates_time(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        session = service.start_session(db, user.id)
        # Backdate last_resumed_at so there's a measurable elapsed interval.
        session.last_resumed_at = datetime.now(UTC) - timedelta(seconds=30)
        db.commit()

        paused = service.pause_session(db, user.id, session.id)
        assert paused.status == WorkoutSessionStatus.paused
        assert paused.accumulated_active_seconds >= 30

    def test_resume_sets_status_back_to_active(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        session = service.start_session(db, user.id)
        service.pause_session(db, user.id, session.id)

        resumed = service.resume_session(db, user.id, session.id)
        assert resumed.status == WorkoutSessionStatus.active

    def test_cannot_pause_an_already_paused_session(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        session = service.start_session(db, user.id)
        service.pause_session(db, user.id, session.id)

        with pytest.raises(ConflictError):
            service.pause_session(db, user.id, session.id)

    def test_cannot_resume_an_already_active_session(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        session = service.start_session(db, user.id)

        with pytest.raises(ConflictError):
            service.resume_session(db, user.id, session.id)

    def test_pausing_excludes_subsequent_idle_time_from_duration(self, db, service, user_with_plan):
        """The core correctness property: time spent paused must not count
        toward the final duration."""
        user, profile, _ = user_with_plan
        session = service.start_session(db, user.id)
        session.last_resumed_at = datetime.now(UTC) - timedelta(seconds=10)
        db.commit()

        service.pause_session(db, user.id, session.id)
        # Simulate a long idle gap while paused — must not be counted.
        session = workout_session_repository.get_by_id(db, session.id)
        session.last_resumed_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()

        result = service.finish_session(db, user.id, session.id, profile)
        # Only the ~10 active seconds before the pause should count, not the
        # 1-hour gap — well under a minute either way.
        assert result.total_duration_minutes == 0


# ---------------------------------------------------------------------------
# complete_exercise / skip_exercise
# ---------------------------------------------------------------------------


class TestCompleteAndSkipExercise:
    def _first_exercise_id(self, db, session, plan) -> str:
        """The first exercise of whichever day the session actually points
        to — *not* `plan.days[0]`. Which day is "today" depends on the real
        calendar date `_get_todays_day` reads at test-run time, so a fixed
        index would silently break on whichever weekdays don't happen to
        map to index 0."""
        day = next(d for d in plan.days if d.id == session.workout_day_id)
        return day.workout_exercises[0].id

    def test_complete_marks_exercise_completed(self, db, service, user_with_plan):
        user, _, plan = user_with_plan
        session = service.start_session(db, user.id)
        we_id = self._first_exercise_id(db, session, plan)

        completion = service.complete_exercise(
            db, user.id, session.id, we_id, ExerciseCompletionRequest()
        )
        assert completion.completed is True
        assert completion.skipped is False
        assert completion.completed_sets > 0  # defaults to the prescribed sets

    def test_complete_respects_explicit_values(self, db, service, user_with_plan):
        user, _, plan = user_with_plan
        session = service.start_session(db, user.id)
        we_id = self._first_exercise_id(db, session, plan)

        completion = service.complete_exercise(
            db,
            user.id,
            session.id,
            we_id,
            ExerciseCompletionRequest(completed_sets=2, completed_reps="8", notes="Felt heavy"),
        )
        assert completion.completed_sets == 2
        assert completion.completed_reps == "8"
        assert completion.notes == "Felt heavy"

    def test_skip_marks_exercise_skipped(self, db, service, user_with_plan):
        user, _, plan = user_with_plan
        session = service.start_session(db, user.id)
        we_id = self._first_exercise_id(db, session, plan)

        completion = service.skip_exercise(
            db, user.id, session.id, we_id, ExerciseCompletionRequest()
        )
        assert completion.skipped is True
        assert completion.completed is False

    def test_completing_twice_updates_the_same_row_not_a_new_one(self, db, service, user_with_plan):
        user, _, plan = user_with_plan
        session = service.start_session(db, user.id)
        we_id = self._first_exercise_id(db, session, plan)

        first = service.complete_exercise(
            db, user.id, session.id, we_id, ExerciseCompletionRequest()
        )
        second = service.complete_exercise(
            db, user.id, session.id, we_id, ExerciseCompletionRequest(completed_sets=1)
        )
        assert first.id == second.id

    def test_rejects_exercise_not_in_this_session(self, db, service, user_with_plan):
        user, _, plan = user_with_plan
        session = service.start_session(db, user.id)

        with pytest.raises(NotFoundError):
            service.complete_exercise(
                db, user.id, session.id, "not-a-real-id", ExerciseCompletionRequest()
            )

    def test_cannot_complete_in_a_finished_session(self, db, service, user_with_plan):
        user, profile, plan = user_with_plan
        session = service.start_session(db, user.id)
        we_id = self._first_exercise_id(db, session, plan)
        service.finish_session(db, user.id, session.id, profile)

        with pytest.raises(ConflictError):
            service.complete_exercise(db, user.id, session.id, we_id, ExerciseCompletionRequest())


# ---------------------------------------------------------------------------
# finish_session
# ---------------------------------------------------------------------------


class TestFinishSession:
    def test_finish_sets_status_completed(self, db, service, user_with_plan):
        user, profile, _ = user_with_plan
        session = service.start_session(db, user.id)

        result = service.finish_session(db, user.id, session.id, profile)
        assert result.session.status == WorkoutSessionStatus.completed
        assert result.session.completed_at is not None

    def test_finish_computes_positive_duration_for_a_real_elapsed_session(
        self, db, service, user_with_plan
    ):
        user, profile, _ = user_with_plan
        session = service.start_session(db, user.id)
        session.last_resumed_at = datetime.now(UTC) - timedelta(minutes=20)
        db.commit()

        result = service.finish_session(db, user.id, session.id, profile)
        assert result.total_duration_minutes >= 19  # ~20 minutes, allow for test runtime

    def test_finish_estimates_positive_calories_for_a_real_elapsed_session(
        self, db, service, user_with_plan
    ):
        user, profile, _ = user_with_plan
        session = service.start_session(db, user.id)
        session.last_resumed_at = datetime.now(UTC) - timedelta(minutes=20)
        db.commit()

        result = service.finish_session(db, user.id, session.id, profile)
        assert result.calories_burned_estimate > 0

    def test_finish_counts_completed_and_skipped_exercises(self, db, service, user_with_plan):
        user, profile, plan = user_with_plan
        session = service.start_session(db, user.id)
        today_day = next(d for d in plan.days if d.id == session.workout_day_id)
        exercises = today_day.workout_exercises

        service.complete_exercise(
            db, user.id, session.id, exercises[0].id, ExerciseCompletionRequest()
        )
        service.skip_exercise(db, user.id, session.id, exercises[1].id, ExerciseCompletionRequest())

        result = service.finish_session(db, user.id, session.id, profile)
        assert result.exercises_completed == 1
        assert result.exercises_skipped == 1

    def test_cannot_finish_an_already_completed_session(self, db, service, user_with_plan):
        user, profile, _ = user_with_plan
        session = service.start_session(db, user.id)
        service.finish_session(db, user.id, session.id, profile)

        with pytest.raises(ConflictError):
            service.finish_session(db, user.id, session.id, profile)

    def test_finish_while_paused_excludes_only_the_pre_pause_active_time(
        self, db, service, user_with_plan
    ):
        user, profile, _ = user_with_plan
        session = service.start_session(db, user.id)
        session.last_resumed_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
        service.pause_session(db, user.id, session.id)

        result = service.finish_session(db, user.id, session.id, profile)
        assert result.total_duration_minutes >= 4


# ---------------------------------------------------------------------------
# History / ownership
# ---------------------------------------------------------------------------


class TestHistoryAndOwnership:
    def test_history_is_empty_before_any_finished_session(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        assert service.get_history(db, user.id) == []

    def test_history_includes_finished_sessions_only(self, db, service, user_with_plan):
        user, profile, _ = user_with_plan
        session = service.start_session(db, user.id)
        service.finish_session(db, user.id, session.id, profile)

        history = service.get_history(db, user.id)
        assert len(history) == 1
        assert history[0].id == session.id
        assert history[0].status == WorkoutSessionStatus.completed

    def test_active_session_does_not_appear_in_history(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        service.start_session(db, user.id)

        assert service.get_history(db, user.id) == []

    def test_get_session_detail_returns_the_session(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        session = service.start_session(db, user.id)

        detail = service.get_session_detail(db, user.id, session.id)
        assert detail.id == session.id

    def test_a_user_cannot_access_another_users_session(self, db, service, user_with_plan):
        user, _, _ = user_with_plan
        session = service.start_session(db, user.id)

        other_user = User(email=unique_email("other"), password_hash="x")
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        with pytest.raises(NotFoundError):
            service.get_session_detail(db, other_user.id, session.id)
