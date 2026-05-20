"""Data access for `Exercise` — the shared exercise library."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import Difficulty, ExerciseEquipment, MuscleGroup
from app.models.exercise import Exercise


def get_by_id(db: Session, exercise_id: str) -> Exercise | None:
    return db.get(Exercise, exercise_id)


def list_exercises(
    db: Session,
    *,
    muscle_group: MuscleGroup | None = None,
    equipment: ExerciseEquipment | None = None,
    difficulty: Difficulty | None = None,
) -> list[Exercise]:
    """List exercises, optionally filtered. Filters combine with AND — e.g.
    `muscle_group=chest` + `equipment=barbell` returns only chest exercises
    that use a barbell, not either independently."""
    query = select(Exercise)
    if muscle_group is not None:
        query = query.where(Exercise.muscle_group == muscle_group)
    if equipment is not None:
        query = query.where(Exercise.equipment == equipment)
    if difficulty is not None:
        query = query.where(Exercise.difficulty == difficulty)
    query = query.order_by(Exercise.name)
    return list(db.execute(query).scalars().all())


def count(db: Session) -> int:
    """Used by the startup seed check — "is the library already populated?"
    (see `app/db/seed_exercises.py`)."""
    return db.execute(select(func.count()).select_from(Exercise)).scalar_one()


def create(db: Session, *, fields: dict) -> Exercise:
    exercise = Exercise(**fields)
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


def bulk_create(db: Session, *, rows: list[dict]) -> list[Exercise]:
    """Inserts many exercises in a single transaction — used by the seed
    script so seeding ~100 rows is one commit, not a hundred."""
    exercises = [Exercise(**row) for row in rows]
    db.add_all(exercises)
    db.commit()
    return exercises


def update(db: Session, *, exercise: Exercise, fields: dict) -> Exercise:
    for key, value in fields.items():
        setattr(exercise, key, value)
    db.commit()
    db.refresh(exercise)
    return exercise


def delete(db: Session, *, exercise: Exercise) -> None:
    db.delete(exercise)
    db.commit()
