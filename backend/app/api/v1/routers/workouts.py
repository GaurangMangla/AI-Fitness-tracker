"""`/workouts` router — recommendation + plan generation + plan retrieval +
session tracking.

Endpoints:
  POST /workouts/recommend  — stateless split recommendation (Milestone 2.2)
  POST /workouts/generate   — generate & persist a full weekly plan (Milestone 2.3)
  GET  /workouts/current    — return the user's active plan (Milestone 2.3)
  GET  /workouts/today      — return today's workout day (Milestone 2.3)
  POST /workouts/start                                    (Milestone 2.5)
  POST /workouts/{session_id}/pause                       (Milestone 2.5)
  POST /workouts/{session_id}/resume                       (Milestone 2.5)
  POST /workouts/{session_id}/exercise/{exercise_id}/complete  (Milestone 2.5)
  POST /workouts/{session_id}/exercise/{exercise_id}/skip      (Milestone 2.5)
  POST /workouts/{session_id}/finish                       (Milestone 2.5)
  GET  /workouts/history                                   (Milestone 2.5)
  GET  /workouts/history/{session_id}                      (Milestone 2.5)
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, RecommendationService
from app.repositories import workout_plan_repository
from app.schemas.recommendation import RecommendationResponse, WorkoutRecommendationRequest
from app.schemas.workout import (
    GeneratedWorkoutPlanResponse,
    GenerateWorkoutRequest,
    WorkoutDayResponse,
    WorkoutPlanResponse,
)
from app.schemas.workout_session import (
    ExerciseCompletionRequest,
    ExerciseCompletionResponse,
    FinishWorkoutResponse,
    WorkoutSessionResponse,
)
from app.services.workout_planner_service import WorkoutPlannerService
from app.services.workout_tracking_service import WorkoutTrackingService

router = APIRouter(prefix="/workouts", tags=["workouts"])

_planner_service = WorkoutPlannerService()
_tracking_service = WorkoutTrackingService()


# ---------------------------------------------------------------------------
# POST /workouts/recommend  (Milestone 2.2 — unchanged)
# ---------------------------------------------------------------------------


@router.post("/recommend", response_model=RecommendationResponse)
def recommend_workout_split(
    data: WorkoutRecommendationRequest,
    current_user: CurrentUser,
    recommendation_service: RecommendationService,
) -> RecommendationResponse:
    """Recommend a workout split for the current user without persisting anything."""
    return recommendation_service.recommend(current_user.profile, data.workout_days_per_week)


# ---------------------------------------------------------------------------
# POST /workouts/generate  (Milestone 2.3)
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=GeneratedWorkoutPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_workout_plan(
    data: GenerateWorkoutRequest,
    current_user: CurrentUser,
    db: DbSession,
    recommendation_service: RecommendationService,
) -> GeneratedWorkoutPlanResponse:
    """Full pipeline: recommend a split → build a weekly plan from DB exercises
    → deactivate any existing active plan → persist → return the complete plan.

    Raises 422 if onboarding is incomplete (no profile / missing fields).
    """
    # Step 1: recommend a split (reuses the same service as /recommend)
    recommendation = recommendation_service.recommend(
        current_user.profile, data.workout_days_per_week
    )

    # Step 2: generate and persist the plan
    profile = current_user.profile
    # profile is guaranteed non-None here — recommend() raises 422 if it's None
    assert profile is not None

    return _planner_service.generate_and_save(
        db=db,
        user_id=current_user.id,
        user_equipment=profile.equipment_available,
        recommendation=recommendation,
        fitness_goal=profile.fitness_goal,
    )


# ---------------------------------------------------------------------------
# GET /workouts/current  (Milestone 2.3)
# ---------------------------------------------------------------------------


@router.get("/current", response_model=WorkoutPlanResponse)
def get_current_plan(
    current_user: CurrentUser,
    db: DbSession,
) -> WorkoutPlanResponse:
    """Return the user's current active workout plan with all days and exercises.

    Raises 404 if no active plan exists (i.e. the user hasn't generated one
    yet, or all plans have been deactivated).
    """
    plan = workout_plan_repository.get_active_by_user(db, current_user.id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active workout plan found. Generate one at POST /workouts/generate.",
        )
    return WorkoutPlanResponse.model_validate(plan)


# ---------------------------------------------------------------------------
# GET /workouts/today  (Milestone 2.3)
# ---------------------------------------------------------------------------


@router.get("/today", response_model=WorkoutDayResponse)
def get_todays_workout(
    current_user: CurrentUser,
    db: DbSession,
) -> WorkoutDayResponse:
    """Return the workout scheduled for today based on the day of the week.

    Logic: day_number is 1-indexed starting Monday (ISO weekday). Today's
    weekday (1=Mon … 7=Sun) is mapped to the plan's day list by position.
    If today is a rest day (weekday > plan.workout_days), raises 404 with a
    clear message rather than silently returning nothing.
    """
    plan = workout_plan_repository.get_active_by_user(db, current_user.id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active workout plan found. Generate one at POST /workouts/generate.",
        )

    today_iso = datetime.now().isoweekday()  # 1 = Monday, 7 = Sunday
    # Map to a 0-based index into the plan's training days
    day_index = (today_iso - 1) % plan.workout_days

    if not plan.days:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your workout plan has no days. Please regenerate.",
        )

    # plan.days is ordered by day_number (see WorkoutPlan relationship)
    sorted_days = sorted(plan.days, key=lambda d: d.day_number)

    # If today's index is a rest day (beyond the scheduled training days)
    if day_index >= len(sorted_days):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Today is a rest day. Enjoy the recovery!",
        )

    today_day = sorted_days[day_index]
    return WorkoutDayResponse.model_validate(today_day)


# ---------------------------------------------------------------------------
# POST /workouts/start  (Milestone 2.5)
# ---------------------------------------------------------------------------


@router.post(
    "/start",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_workout(current_user: CurrentUser, db: DbSession) -> WorkoutSessionResponse:
    """Start today's workout, creating a new `WorkoutSession`.

    Raises 404 if there's no active plan, 422 if today is a rest day, and
    409 if the user already has an active or paused session open.
    """
    session = _tracking_service.start_session(db, current_user.id)
    return WorkoutSessionResponse.model_validate(session)


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/pause and /resume  (Milestone 2.5)
# Not in the milestone's literal endpoint list, but required by its feature
# list ("Pause and resume workouts") — see WorkoutTrackingService for the
# full rationale.
# ---------------------------------------------------------------------------


@router.post("/{session_id}/pause", response_model=WorkoutSessionResponse)
def pause_workout(
    session_id: str, current_user: CurrentUser, db: DbSession
) -> WorkoutSessionResponse:
    session = _tracking_service.pause_session(db, current_user.id, session_id)
    return WorkoutSessionResponse.model_validate(session)


@router.post("/{session_id}/resume", response_model=WorkoutSessionResponse)
def resume_workout(
    session_id: str, current_user: CurrentUser, db: DbSession
) -> WorkoutSessionResponse:
    session = _tracking_service.resume_session(db, current_user.id, session_id)
    return WorkoutSessionResponse.model_validate(session)


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/exercise/{exercise_id}/complete  (Milestone 2.5)
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/exercise/{exercise_id}/complete",
    response_model=ExerciseCompletionResponse,
)
def complete_exercise(
    session_id: str,
    exercise_id: str,
    data: ExerciseCompletionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ExerciseCompletionResponse:
    """Mark a `WorkoutExercise` as completed within this session.

    `exercise_id` here refers to the `WorkoutExercise` row (the specific
    placement within the plan, with its prescribed sets/reps), not the
    shared `Exercise` library row — consistent with every other workout
    endpoint that deals in plan-specific exercise placements.
    """
    completion = _tracking_service.complete_exercise(
        db, current_user.id, session_id, exercise_id, data
    )
    return ExerciseCompletionResponse.model_validate(completion)


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/exercise/{exercise_id}/skip  (Milestone 2.5)
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/exercise/{exercise_id}/skip",
    response_model=ExerciseCompletionResponse,
)
def skip_exercise(
    session_id: str,
    exercise_id: str,
    data: ExerciseCompletionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ExerciseCompletionResponse:
    """Mark a `WorkoutExercise` as skipped within this session."""
    completion = _tracking_service.skip_exercise(db, current_user.id, session_id, exercise_id, data)
    return ExerciseCompletionResponse.model_validate(completion)


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/finish  (Milestone 2.5)
# ---------------------------------------------------------------------------


@router.post("/{session_id}/finish", response_model=FinishWorkoutResponse)
def finish_workout(
    session_id: str, current_user: CurrentUser, db: DbSession
) -> FinishWorkoutResponse:
    """Finish a workout session: computes total active duration (excluding
    any paused time), estimates calories burned, and returns a summary.

    Raises 409 if the session is already completed — a finished workout
    cannot be re-finished or otherwise modified.
    """
    profile = current_user.profile
    assert profile is not None  # every user with a session also onboarded
    return _tracking_service.finish_session(db, current_user.id, session_id, profile)


# ---------------------------------------------------------------------------
# GET /workouts/history  (Milestone 2.5)
# ---------------------------------------------------------------------------


@router.get("/history", response_model=list[WorkoutSessionResponse])
def get_workout_history(current_user: CurrentUser, db: DbSession) -> list[WorkoutSessionResponse]:
    """Every completed workout session for the user, most recent first.
    Never empty-vs-404 — an empty list is a perfectly normal response for a
    user who hasn't finished a workout yet."""
    sessions = _tracking_service.get_history(db, current_user.id)
    return [WorkoutSessionResponse.model_validate(s) for s in sessions]


# ---------------------------------------------------------------------------
# GET /workouts/history/{session_id}  (Milestone 2.5)
# ---------------------------------------------------------------------------


@router.get("/history/{session_id}", response_model=WorkoutSessionResponse)
def get_workout_session_detail(
    session_id: str, current_user: CurrentUser, db: DbSession
) -> WorkoutSessionResponse:
    """Full detail for a single session — completed or still in progress."""
    session = _tracking_service.get_session_detail(db, current_user.id, session_id)
    return WorkoutSessionResponse.model_validate(session)
