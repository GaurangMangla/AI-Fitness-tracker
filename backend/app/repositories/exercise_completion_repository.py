"""Data access for `ExerciseCompletion`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exercise_completion import ExerciseCompletion


def get_by_session_and_exercise(
    db: Session, *, session_id: str, workout_exercise_id: str
) -> ExerciseCompletion | None:
    """Returns the completion row for this (session, exercise) pair, or
    `None` if the exercise hasn't been touched yet in this session — see the
    model docstring for why "no row" is the deliberate representation of
    "not started" rather than a row with both flags false."""
    query = select(ExerciseCompletion).where(
        ExerciseCompletion.workout_session_id == session_id,
        ExerciseCompletion.workout_exercise_id == workout_exercise_id,
    )
    return db.execute(query).scalars().first()


def list_by_session(db: Session, session_id: str) -> list[ExerciseCompletion]:
    query = select(ExerciseCompletion).where(ExerciseCompletion.workout_session_id == session_id)
    return list(db.execute(query).scalars().all())


def create(db: Session, *, fields: dict) -> ExerciseCompletion:
    completion = ExerciseCompletion(**fields)
    db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion


def update(db: Session, *, completion: ExerciseCompletion, fields: dict) -> ExerciseCompletion:
    for key, value in fields.items():
        setattr(completion, key, value)
    db.commit()
    db.refresh(completion)
    return completion
