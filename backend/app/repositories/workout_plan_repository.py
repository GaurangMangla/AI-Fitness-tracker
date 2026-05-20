"""Data access for `WorkoutPlan`."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.workout_day import WorkoutDay
from app.models.workout_exercise import WorkoutExercise
from app.models.workout_plan import WorkoutPlan


def get_by_id(db: Session, plan_id: str) -> WorkoutPlan | None:
    return db.get(WorkoutPlan, plan_id)


def get_active_by_user(db: Session, user_id: str) -> WorkoutPlan | None:
    """Return the single active plan for a user, eagerly loading the full
    day → exercise → exercise chain so the caller never triggers lazy loads.
    Returns None if no active plan exists."""
    query = (
        select(WorkoutPlan)
        .where(WorkoutPlan.user_id == user_id, WorkoutPlan.active == True)  # noqa: E712
        .options(
            joinedload(WorkoutPlan.days)
            .joinedload(WorkoutDay.workout_exercises)
            .joinedload(WorkoutExercise.exercise)
        )
        .limit(1)
    )
    return db.execute(query).unique().scalars().first()


def deactivate_all(db: Session, user_id: str) -> int:
    """Set `active = False` on every active plan for this user.
    Returns the count of rows updated. Called before creating a new plan
    so there's never more than one active plan per user at a time — we
    deactivate rather than delete so history is preserved."""
    plans = (
        db.execute(
            select(WorkoutPlan).where(
                WorkoutPlan.user_id == user_id, WorkoutPlan.active == True  # noqa: E712
            )
        )
        .scalars()
        .all()
    )
    for plan in plans:
        plan.active = False
    db.commit()
    return len(plans)


def list_by_user(db: Session, user_id: str) -> list[WorkoutPlan]:
    query = (
        select(WorkoutPlan)
        .where(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
    )
    return list(db.execute(query).scalars().all())


def create(db: Session, *, user_id: str, fields: dict) -> WorkoutPlan:
    plan = WorkoutPlan(user_id=user_id, **fields)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update(db: Session, *, plan: WorkoutPlan, fields: dict) -> WorkoutPlan:
    for key, value in fields.items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


def delete(db: Session, *, plan: WorkoutPlan) -> None:
    """Cascades to the plan's `WorkoutDay` (and their `WorkoutExercise`) rows
    via the ORM-level `cascade="all, delete-orphan"` declared on
    `WorkoutPlan.days` — not just a DB-level FK cascade, so this works the
    same on SQLite (which doesn't enforce FK constraints by default) and
    Postgres."""
    db.delete(plan)
    db.commit()
