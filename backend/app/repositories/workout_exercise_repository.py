"""Data access for `WorkoutExercise`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workout_exercise import WorkoutExercise


def get_by_id(db: Session, workout_exercise_id: str) -> WorkoutExercise | None:
    return db.get(WorkoutExercise, workout_exercise_id)


def list_by_day(db: Session, workout_day_id: str) -> list[WorkoutExercise]:
    query = (
        select(WorkoutExercise)
        .where(WorkoutExercise.workout_day_id == workout_day_id)
        .order_by(WorkoutExercise.order_index)
    )
    return list(db.execute(query).scalars().all())


def create(db: Session, *, workout_day_id: str, fields: dict) -> WorkoutExercise:
    workout_exercise = WorkoutExercise(workout_day_id=workout_day_id, **fields)
    db.add(workout_exercise)
    db.commit()
    db.refresh(workout_exercise)
    return workout_exercise


def update(db: Session, *, workout_exercise: WorkoutExercise, fields: dict) -> WorkoutExercise:
    for key, value in fields.items():
        setattr(workout_exercise, key, value)
    db.commit()
    db.refresh(workout_exercise)
    return workout_exercise


def delete(db: Session, *, workout_exercise: WorkoutExercise) -> None:
    db.delete(workout_exercise)
    db.commit()
