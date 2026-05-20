"""Data access for `WorkoutDay`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workout_day import WorkoutDay


def get_by_id(db: Session, day_id: str) -> WorkoutDay | None:
    return db.get(WorkoutDay, day_id)


def list_by_plan(db: Session, workout_plan_id: str) -> list[WorkoutDay]:
    query = (
        select(WorkoutDay)
        .where(WorkoutDay.workout_plan_id == workout_plan_id)
        .order_by(WorkoutDay.day_number)
    )
    return list(db.execute(query).scalars().all())


def create(db: Session, *, workout_plan_id: str, fields: dict) -> WorkoutDay:
    day = WorkoutDay(workout_plan_id=workout_plan_id, **fields)
    db.add(day)
    db.commit()
    db.refresh(day)
    return day


def update(db: Session, *, day: WorkoutDay, fields: dict) -> WorkoutDay:
    for key, value in fields.items():
        setattr(day, key, value)
    db.commit()
    db.refresh(day)
    return day


def delete(db: Session, *, day: WorkoutDay) -> None:
    db.delete(day)
    db.commit()
