"""/workouts/stats router — aggregate statistics over completed sessions."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.progress_nutrition import WorkoutStatsResponse
from app.services.workout_stats_service import WorkoutStatsService

router = APIRouter(prefix="/workouts/stats", tags=["workout-stats"])
_svc = WorkoutStatsService()


@router.get("/summary", response_model=WorkoutStatsResponse)
def get_stats_summary(current_user: CurrentUser, db: DbSession):
    return _svc.get_summary(db, current_user.id)


@router.get("/weekly-volume")
def get_weekly_volume(current_user: CurrentUser, db: DbSession, weeks: int = 8):
    return _svc.get_weekly_volume(db, current_user.id, weeks=min(weeks, 26))


@router.get("/personal-records")
def get_personal_records(current_user: CurrentUser, db: DbSession):
    return _svc.get_personal_records(db, current_user.id)


@router.get("/heatmap")
def get_heatmap(current_user: CurrentUser, db: DbSession, days: int = 365):
    return _svc.get_heatmap(db, current_user.id, days=min(days, 365))
