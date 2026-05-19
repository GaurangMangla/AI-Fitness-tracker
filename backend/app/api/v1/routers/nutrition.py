"""/nutrition router."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.progress_nutrition import (
    NutritionLogRequest,
    NutritionLogResponse,
    NutritionPlanResponse,
    NutritionWeeklySummary,
)
from app.services.nutrition_service import NutritionService

router = APIRouter(prefix="/nutrition", tags=["nutrition"])
_svc = NutritionService()


@router.post(
    "/plans/generate",
    response_model=NutritionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_plan(current_user: CurrentUser, db: DbSession):
    """Generate a personalised meal plan from the user's profile.
    Requires completed onboarding (profile must exist)."""
    profile = current_user.profile
    if not profile:
        raise ValidationError("Complete onboarding before generating a nutrition plan.")
    plan = _svc.generate_plan(db, current_user.id, profile)
    return NutritionPlanResponse.model_validate(plan)


@router.get("/plans/current", response_model=NutritionPlanResponse)
def get_current_plan(current_user: CurrentUser, db: DbSession):
    plan = _svc.get_current_plan(db, current_user.id)
    if not plan:
        raise NotFoundError("No active nutrition plan. Generate one first.")
    return NutritionPlanResponse.model_validate(plan)


@router.post("/logs", response_model=NutritionLogResponse, status_code=status.HTTP_201_CREATED)
def log_nutrition(body: NutritionLogRequest, current_user: CurrentUser, db: DbSession):
    log = _svc.log_nutrition(
        db,
        user_id=current_user.id,
        log_date=body.log_date,
        calories_consumed=body.calories_consumed,
        protein_g=body.protein_g,
        carbs_g=body.carbs_g,
        fat_g=body.fat_g,
        water_ml=body.water_ml,
        notes=body.notes,
    )
    return NutritionLogResponse.model_validate(log)


@router.get("/logs", response_model=list[NutritionLogResponse])
def get_logs(current_user: CurrentUser, db: DbSession, limit: int = 30):
    logs = _svc.get_logs(db, current_user.id, limit=min(limit, 90))
    return [NutritionLogResponse.model_validate(lg) for lg in logs]


@router.get("/logs/today", response_model=NutritionLogResponse | None)
def get_today(current_user: CurrentUser, db: DbSession):
    return _svc.get_today_log(db, current_user.id)


@router.get("/summary/weekly", response_model=NutritionWeeklySummary)
def weekly_summary(current_user: CurrentUser, db: DbSession):
    return _svc.get_weekly_summary(db, current_user.id)
