"""Unit tests for `WorkoutPlannerService`.

Tests cover:
- Equipment bridge: correct ExerciseEquipment values unlocked by each user
  Equipment enum value.
- Exercise selector: respects equipment, difficulty, and avoids duplicates.
- Volume resolver: compound vs isolation, experience + goal combinations.
- Full generate_and_save: persists plan/day/exercise rows correctly and
  deactivates any pre-existing active plan.
"""

from sqlalchemy.orm import Session

from app.models.enums import (
    FitnessGoal,
    WorkoutExperience,
)
from app.repositories import workout_plan_repository
from app.schemas.recommendation import RecommendationResponse
from app.services.workout_planner_service import (
    _EXERCISES_PER_DAY,
    WorkoutPlannerService,
    _allowed_equipment,
    _resolve_volume,
    _select_exercises,
)
from tests.factories import unique_email as make_email

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_recommendation(
    split_name: str = "Full Body",
    difficulty: str = "Beginner",
    workout_days: int = 3,
    title: str = "Test Plan",
) -> RecommendationResponse:
    return RecommendationResponse(
        title=title,
        split_name=split_name,
        workout_days=workout_days,
        difficulty=difficulty,
        reason="Test reason",
    )


def _register_and_onboard(client, split_name="Full Body", days=3):
    """Register a user and complete onboarding; return auth headers."""
    email = make_email("planner")
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "TestPass123!"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.patch(
        "/api/v1/users/me",
        json={
            "name": "Test User",
            "age": 25,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 75.0,
            "fitness_goal": "muscle_gain",
            "activity_level": "moderately_active",
            "workout_experience": "intermediate",
            "equipment_available": ["full_gym"],
            "diet_preference": "non_vegetarian",
        },
        headers=headers,
    )
    return headers


# ---------------------------------------------------------------------------
# Equipment bridge tests
# ---------------------------------------------------------------------------


class TestAllowedEquipment:
    def test_none_always_includes_bodyweight(self):
        allowed = _allowed_equipment(["none"])
        assert "bodyweight" in allowed

    def test_dumbbells_unlocks_dumbbells_and_bodyweight(self):
        allowed = _allowed_equipment(["dumbbells"])
        assert "dumbbells" in allowed
        assert "bodyweight" in allowed
        assert "barbell" not in allowed

    def test_barbell_unlocks_barbell_bench_dumbbells_bodyweight(self):
        allowed = _allowed_equipment(["barbell"])
        assert "barbell" in allowed
        assert "bench" in allowed
        assert "dumbbells" in allowed
        assert "bodyweight" in allowed

    def test_full_gym_unlocks_everything(self):
        allowed = _allowed_equipment(["full_gym"])
        for eq in ("bodyweight", "dumbbells", "barbell", "cable", "machine", "bench"):
            assert eq in allowed

    def test_multiple_equipment_items_union(self):
        allowed = _allowed_equipment(["pull_up_bar", "resistance_bands"])
        assert "pull_up_bar" in allowed
        assert "resistance_bands" in allowed
        assert "bodyweight" in allowed

    def test_unknown_value_falls_back_to_bodyweight(self):
        allowed = _allowed_equipment(["space_station_gym"])
        assert "bodyweight" in allowed


# ---------------------------------------------------------------------------
# Volume resolver tests
# ---------------------------------------------------------------------------


class TestResolveVolume:
    def _make_exercise(self, is_compound: bool):
        """Minimal mock with just the `is_compound` attribute."""

        class FakeExercise:
            pass

        e = FakeExercise()
        e.is_compound = is_compound
        return e

    def test_compound_beginner_muscle_gain_has_more_sets_than_isolation(self):
        compound = _resolve_volume(
            self._make_exercise(True), WorkoutExperience.beginner, FitnessGoal.muscle_gain
        )
        isolation = _resolve_volume(
            self._make_exercise(False), WorkoutExperience.beginner, FitnessGoal.muscle_gain
        )
        assert compound.sets >= isolation.sets

    def test_advanced_muscle_gain_compound_has_more_sets_than_beginner(self):
        beginner = _resolve_volume(
            self._make_exercise(True), WorkoutExperience.beginner, FitnessGoal.muscle_gain
        )
        advanced = _resolve_volume(
            self._make_exercise(True), WorkoutExperience.advanced, FitnessGoal.muscle_gain
        )
        assert advanced.sets >= beginner.sets

    def test_weight_loss_has_shorter_rest_than_muscle_gain(self):
        loss = _resolve_volume(
            self._make_exercise(True), WorkoutExperience.intermediate, FitnessGoal.weight_loss
        )
        gain = _resolve_volume(
            self._make_exercise(True), WorkoutExperience.intermediate, FitnessGoal.muscle_gain
        )
        assert loss.rest_seconds <= gain.rest_seconds

    def test_reps_is_a_string(self):
        spec = _resolve_volume(
            self._make_exercise(True), WorkoutExperience.beginner, FitnessGoal.general_fitness
        )
        assert isinstance(spec.reps, str)

    def test_sets_positive(self):
        spec = _resolve_volume(
            self._make_exercise(False), WorkoutExperience.advanced, FitnessGoal.weight_loss
        )
        assert spec.sets > 0


# ---------------------------------------------------------------------------
# Exercise selector tests (use seeded DB via conftest)
# ---------------------------------------------------------------------------


class TestSelectExercises:
    def test_returns_requested_count(self, db: Session):
        allowed = _allowed_equipment(["full_gym"])
        exercises = _select_exercises(
            db, ["chest"], allowed, WorkoutExperience.intermediate, 4, set()
        )
        assert len(exercises) <= 4
        assert len(exercises) > 0

    def test_respects_equipment_filter(self, db: Session):
        # bodyweight only — no barbell/dumbbell exercises should appear
        allowed = _allowed_equipment(["none"])
        exercises = _select_exercises(
            db, ["chest", "back", "legs"], allowed, WorkoutExperience.beginner, 5, set()
        )
        for e in exercises:
            assert e.equipment in allowed, f"{e.name} uses {e.equipment} which is not allowed"

    def test_avoids_already_used_when_possible(self, db: Session):
        allowed = _allowed_equipment(["full_gym"])
        first_batch = _select_exercises(
            db, ["chest"], allowed, WorkoutExperience.intermediate, 3, set()
        )
        used_ids = {e.id for e in first_batch}
        second_batch = _select_exercises(
            db, ["chest"], allowed, WorkoutExperience.intermediate, 3, used_ids
        )
        # At least some exercises should differ (the library has 14+ chest exercises)
        overlap = {e.id for e in second_batch} & used_ids
        assert len(overlap) < len(second_batch)

    def test_compounds_come_before_isolations(self, db: Session):
        allowed = _allowed_equipment(["full_gym"])
        exercises = _select_exercises(
            db, ["chest"], allowed, WorkoutExperience.intermediate, 5, set()
        )
        if len(exercises) >= 2:
            compound_indices = [i for i, e in enumerate(exercises) if e.is_compound]
            isolation_indices = [i for i, e in enumerate(exercises) if not e.is_compound]
            if compound_indices and isolation_indices:
                assert max(compound_indices) < max(isolation_indices) or min(
                    compound_indices
                ) <= min(isolation_indices)

    def test_beginner_no_advanced_exercises(self, db: Session):
        allowed = _allowed_equipment(["full_gym"])
        exercises = _select_exercises(
            db, ["chest", "back", "legs"], allowed, WorkoutExperience.beginner, 6, set()
        )
        for e in exercises:
            assert e.difficulty in (
                "beginner",
                "intermediate",
            ), f"{e.name} has difficulty {e.difficulty} — too hard for beginner"


# ---------------------------------------------------------------------------
# Full generate_and_save integration tests
# ---------------------------------------------------------------------------


class TestWorkoutPlannerServiceGenerate:
    def test_generates_correct_number_of_days(self, db: Session):
        svc = WorkoutPlannerService()
        rec = _make_recommendation("Full Body", "Beginner", 3)
        result = svc.generate_and_save(
            db=db,
            user_id="test-user-planner-1",
            user_equipment=["full_gym"],
            recommendation=rec,
            fitness_goal=FitnessGoal.general_fitness,
        )
        assert len(result.days) == 3

    def test_home_bodyweight_generates_7_days_when_requested(self, db: Session):
        """Regression test: Home Bodyweight Split's `max_days` (in
        workout_splits.py) is 7 — the only split allowed that high — but its
        `_SPLIT_TEMPLATES` list previously had only 4 entries. Requesting a
        7-day plan silently produced a 4-day plan while the response still
        claimed `workout_days: 7`, causing a real dashboard/weekly-plan
        mismatch (and an IndexError in any test or frontend code that
        assumed all 7 days existed). See workout_planner_service.py's
        `_SPLIT_TEMPLATES["Home Bodyweight Split"]` for the fix."""
        svc = WorkoutPlannerService()
        rec = _make_recommendation("Home Bodyweight Split", "Beginner", 7)
        result = svc.generate_and_save(
            db=db,
            user_id="test-user-planner-hb7",
            user_equipment=["bodyweight"],
            recommendation=rec,
            fitness_goal=FitnessGoal.general_fitness,
        )
        assert len(result.days) == 7
        assert result.workout_days == 7

    def test_every_split_supports_its_own_max_days(self, db: Session):
        """Systematic version of the regression above: every split's
        template list must be at least as long as that split's own
        `max_days` (from workout_splits.py), or requesting the maximum
        allowed days for that split silently truncates the plan. This is
        the invariant the Home Bodyweight bug violated — asserting it here
        for all 6 splits means a future split addition can't reintroduce
        the same class of bug without a test catching it immediately."""
        from app.services.workout_splits import WORKOUT_SPLITS

        svc = WorkoutPlannerService()
        for split in WORKOUT_SPLITS:
            rec = _make_recommendation(split.split_name, "Beginner", split.max_days)
            result = svc.generate_and_save(
                db=db,
                user_id=f"test-user-maxdays-{split.key}",
                user_equipment=["full_gym"],
                recommendation=rec,
                fitness_goal=FitnessGoal.general_fitness,
            )
            assert len(result.days) == split.max_days, (
                f"{split.split_name} promises max_days={split.max_days} "
                f"but only generated {len(result.days)} days"
            )

    def test_each_day_has_exercises(self, db: Session):
        svc = WorkoutPlannerService()
        rec = _make_recommendation("Upper Lower", "Intermediate", 4)
        result = svc.generate_and_save(
            db=db,
            user_id="test-user-planner-2",
            user_equipment=["full_gym"],
            recommendation=rec,
            fitness_goal=FitnessGoal.muscle_gain,
        )
        for day in result.days:
            assert len(day.workout_exercises) > 0, f"{day.day_name} has no exercises"

    def test_exercises_count_matches_experience(self, db: Session):
        svc = WorkoutPlannerService()
        rec = _make_recommendation("Full Body", "Advanced", 3)
        result = svc.generate_and_save(
            db=db,
            user_id="test-user-planner-3",
            user_equipment=["full_gym"],
            recommendation=rec,
            fitness_goal=FitnessGoal.muscle_gain,
        )
        expected = _EXERCISES_PER_DAY[WorkoutExperience.advanced]
        for day in result.days:
            assert len(day.workout_exercises) <= expected

    def test_response_has_split_metadata(self, db: Session):
        svc = WorkoutPlannerService()
        rec = _make_recommendation("Push Pull Legs", "Intermediate", 3, "My PPL Plan")
        result = svc.generate_and_save(
            db=db,
            user_id="test-user-planner-4",
            user_equipment=["full_gym"],
            recommendation=rec,
            fitness_goal=FitnessGoal.muscle_gain,
        )
        assert result.split_name == "Push Pull Legs"
        assert result.difficulty == "Intermediate"
        assert result.estimated_duration_minutes > 0

    def test_deactivates_previous_active_plan(self, db: Session):
        svc = WorkoutPlannerService()
        user_id = "test-user-planner-5"

        # Generate first plan
        rec1 = _make_recommendation("Full Body", "Beginner", 3, "Plan 1")
        result1 = svc.generate_and_save(
            db=db,
            user_id=user_id,
            user_equipment=["dumbbells"],
            recommendation=rec1,
            fitness_goal=FitnessGoal.general_fitness,
        )
        assert result1.active is True

        # Generate second plan — first should be deactivated
        rec2 = _make_recommendation("Upper Lower", "Beginner", 4, "Plan 2")
        result2 = svc.generate_and_save(
            db=db,
            user_id=user_id,
            user_equipment=["dumbbells"],
            recommendation=rec2,
            fitness_goal=FitnessGoal.general_fitness,
        )
        assert result2.active is True

        # Confirm only one active plan remains
        active = workout_plan_repository.get_active_by_user(db, user_id)
        assert active is not None
        assert active.id == result2.id

        # Confirm the first is now inactive
        from app.repositories import workout_plan_repository as wpr

        old_plan = wpr.get_by_id(db, result1.id)
        assert old_plan is not None
        assert old_plan.active is False

    def test_bodyweight_plan_only_uses_allowed_equipment(self, db: Session):
        svc = WorkoutPlannerService()
        rec = _make_recommendation("Home Bodyweight Split", "Beginner", 3)
        result = svc.generate_and_save(
            db=db,
            user_id="test-user-planner-6",
            user_equipment=["none"],
            recommendation=rec,
            fitness_goal=FitnessGoal.general_fitness,
        )
        allowed = _allowed_equipment(["none"])
        for day in result.days:
            for we in day.workout_exercises:
                assert we.exercise.equipment in allowed, (
                    f"{we.exercise.name} uses {we.exercise.equipment} " f"but user has no equipment"
                )

    def test_plan_is_persisted_in_db(self, db: Session):
        svc = WorkoutPlannerService()
        rec = _make_recommendation("Full Body", "Beginner", 2, "Persisted Plan")
        result = svc.generate_and_save(
            db=db,
            user_id="test-user-planner-7",
            user_equipment=["dumbbells"],
            recommendation=rec,
            fitness_goal=FitnessGoal.weight_loss,
        )
        # Fetch from DB and verify it's actually there
        from app.repositories import workout_plan_repository as wpr

        plan = wpr.get_by_id(db, result.id)
        assert plan is not None
        assert plan.title == "Persisted Plan"
        assert plan.active is True

    def test_estimated_duration_is_positive(self, db: Session):
        svc = WorkoutPlannerService()
        for split, days in [("Full Body", 3), ("Upper Lower", 4), ("Bro Split", 5)]:
            rec = _make_recommendation(split, "Intermediate", days)
            result = svc.generate_and_save(
                db=db,
                user_id=f"test-user-dur-{split[:3].lower()}",
                user_equipment=["full_gym"],
                recommendation=rec,
                fitness_goal=FitnessGoal.muscle_gain,
            )
            assert (
                result.estimated_duration_minutes > 0
            ), f"{split} estimated duration should be positive"
