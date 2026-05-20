"""Data access for NutritionPlan, Meal, NutritionLog."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.nutrition import Meal, NutritionLog, NutritionPlan

# ── NutritionPlan ──────────────────────────────────────────────────────────


def get_active_by_user(db: Session, user_id: str) -> NutritionPlan | None:
    return (
        db.execute(
            select(NutritionPlan)
            .where(NutritionPlan.user_id == user_id, NutritionPlan.active == True)  # noqa: E712
            .options(joinedload(NutritionPlan.meals))
            .limit(1)
        )
        .unique()
        .scalars()
        .first()
    )


def list_by_user(db: Session, user_id: str) -> list[NutritionPlan]:
    return list(
        db.execute(
            select(NutritionPlan)
            .where(NutritionPlan.user_id == user_id)
            .options(joinedload(NutritionPlan.meals))
            .order_by(NutritionPlan.created_at.desc())
        )
        .unique()
        .scalars()
        .all()
    )


def deactivate_all(db: Session, user_id: str) -> None:
    plans = (
        db.execute(
            select(NutritionPlan).where(
                NutritionPlan.user_id == user_id,
                NutritionPlan.active == True,  # noqa: E712
            )
        )
        .scalars()
        .all()
    )
    for p in plans:
        p.active = False
    db.commit()


def create(db: Session, fields: dict) -> NutritionPlan:
    plan = NutritionPlan(**fields)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def create_meal(db: Session, fields: dict) -> Meal:
    meal = Meal(**fields)
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


def get_with_meals(db: Session, plan_id: str) -> NutritionPlan | None:
    return (
        db.execute(
            select(NutritionPlan)
            .where(NutritionPlan.id == plan_id)
            .options(joinedload(NutritionPlan.meals))
        )
        .unique()
        .scalars()
        .first()
    )


# ── NutritionLog ───────────────────────────────────────────────────────────


def get_log_by_user_and_date(db: Session, user_id: str, log_date: str) -> NutritionLog | None:
    return (
        db.execute(
            select(NutritionLog).where(
                NutritionLog.user_id == user_id,
                NutritionLog.log_date == log_date,
            )
        )
        .scalars()
        .first()
    )


def list_logs_by_user(db: Session, user_id: str, limit: int = 30) -> list[NutritionLog]:
    return list(
        db.execute(
            select(NutritionLog)
            .where(NutritionLog.user_id == user_id)
            .order_by(NutritionLog.log_date.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def upsert_log(db: Session, user_id: str, log_date: str, fields: dict) -> NutritionLog:
    existing = get_log_by_user_and_date(db, user_id, log_date)
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    log = NutritionLog(user_id=user_id, log_date=log_date, **fields)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
