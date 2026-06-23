"""Unit tests for `app.services.exercise_service`."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import Difficulty, ExerciseEquipment, ExerciseType, MuscleGroup
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from app.services import exercise_service


def _sample_exercise_data(**overrides: object) -> ExerciseCreate:
    defaults: dict[str, object] = dict(
        name="Unit Test Curl",
        muscle_group=MuscleGroup.arms,
        equipment=ExerciseEquipment.dumbbells,
        difficulty=Difficulty.beginner,
        instructions="Curl the weight up, then lower it with control.",
        exercise_type=ExerciseType.strength,
        default_sets=3,
        default_reps="10-12",
        rest_seconds=60,
        calories_per_set=4.0,
        is_compound=False,
    )
    defaults.update(overrides)
    return ExerciseCreate(**defaults)


def test_create_and_get_exercise(db: Session) -> None:
    created = exercise_service.create_exercise(db, _sample_exercise_data())

    fetched = exercise_service.get_exercise(db, created.id)

    assert fetched.id == created.id
    assert fetched.name == "Unit Test Curl"
    assert fetched.muscle_group == MuscleGroup.arms


def test_get_exercise_raises_not_found_for_unknown_id(db: Session) -> None:
    with pytest.raises(NotFoundError):
        exercise_service.get_exercise(db, "does-not-exist")


def test_update_exercise_applies_only_provided_fields(db: Session) -> None:
    created = exercise_service.create_exercise(db, _sample_exercise_data())

    updated = exercise_service.update_exercise(db, created.id, ExerciseUpdate(default_sets=5))

    assert updated.default_sets == 5
    assert updated.name == "Unit Test Curl"  # untouched by the partial update


def test_update_exercise_raises_not_found_for_unknown_id(db: Session) -> None:
    with pytest.raises(NotFoundError):
        exercise_service.update_exercise(db, "does-not-exist", ExerciseUpdate(default_sets=5))


def test_delete_exercise_removes_it(db: Session) -> None:
    created = exercise_service.create_exercise(db, _sample_exercise_data())

    exercise_service.delete_exercise(db, created.id)

    with pytest.raises(NotFoundError):
        exercise_service.get_exercise(db, created.id)


def test_list_exercises_filters_by_muscle_group(db: Session) -> None:
    exercise_service.create_exercise(
        db, _sample_exercise_data(name="Unit Test Chest Press", muscle_group=MuscleGroup.chest)
    )
    exercise_service.create_exercise(
        db, _sample_exercise_data(name="Unit Test Back Row", muscle_group=MuscleGroup.back)
    )

    results = exercise_service.list_exercises(db, muscle_group=MuscleGroup.chest)

    assert any(item.name == "Unit Test Chest Press" for item in results)
    assert all(item.muscle_group == MuscleGroup.chest for item in results)


def test_list_exercises_with_no_filters_returns_everything(db: Session) -> None:
    exercise_service.create_exercise(db, _sample_exercise_data(name="Unit Test Unfiltered"))

    results = exercise_service.list_exercises(db)

    assert any(item.name == "Unit Test Unfiltered" for item in results)


def test_calories_per_set_can_be_null(db: Session) -> None:
    created = exercise_service.create_exercise(
        db, _sample_exercise_data(name="Unit Test Plank", calories_per_set=None)
    )

    fetched = exercise_service.get_exercise(db, created.id)

    assert fetched.calories_per_set is None
