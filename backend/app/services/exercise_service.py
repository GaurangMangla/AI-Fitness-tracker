"""Business logic for the exercise library — thin CRUD wrappers over
`exercise_repository`. Deliberately no recommendation/matching logic here —
that's a later milestone, once there's an actual workout-plan generator that
needs "find me good exercises for X" rather than "list/filter the library."
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import Difficulty, ExerciseEquipment, MuscleGroup
from app.models.exercise import Exercise
from app.repositories import exercise_repository
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate


def get_exercise(db: Session, exercise_id: str) -> Exercise:
    exercise = exercise_repository.get_by_id(db, exercise_id)
    if exercise is None:
        raise NotFoundError(f"Exercise {exercise_id} not found.")
    return exercise


def list_exercises(
    db: Session,
    *,
    muscle_group: MuscleGroup | None = None,
    equipment: ExerciseEquipment | None = None,
    difficulty: Difficulty | None = None,
) -> list[Exercise]:
    return exercise_repository.list_exercises(
        db, muscle_group=muscle_group, equipment=equipment, difficulty=difficulty
    )


def create_exercise(db: Session, data: ExerciseCreate) -> Exercise:
    return exercise_repository.create(db, fields=data.model_dump())


def update_exercise(db: Session, exercise_id: str, data: ExerciseUpdate) -> Exercise:
    exercise = get_exercise(db, exercise_id)
    fields = data.model_dump(exclude_unset=True)
    return exercise_repository.update(db, exercise=exercise, fields=fields)


def delete_exercise(db: Session, exercise_id: str) -> None:
    exercise = get_exercise(db, exercise_id)
    exercise_repository.delete(db, exercise=exercise)
