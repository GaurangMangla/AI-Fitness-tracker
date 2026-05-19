"""`/exercises` — the shared exercise library.

Deliberately public (no `CurrentUser` dependency): this is read-only
reference data, not user-specific, and nothing in the spec for this milestone
calls for gating it behind auth. Every other piece of user data in this app
*is* behind auth — this is the one exception, and it's an exception because
of what the data actually is, not an oversight.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.models.enums import Difficulty, ExerciseEquipment, MuscleGroup
from app.schemas.exercise import ExerciseResponse
from app.services.exercise_service import get_exercise, list_exercises

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseResponse])
def list_exercises_route(
    db: DbSession,
    muscle_group: Annotated[MuscleGroup | None, Query()] = None,
    equipment: Annotated[ExerciseEquipment | None, Query()] = None,
    difficulty: Annotated[Difficulty | None, Query()] = None,
) -> list[ExerciseResponse]:
    """List exercises. All three filters are optional and combine with AND.
    An invalid value for any of them (e.g. `?difficulty=expert`) is rejected
    with a 422 automatically — they're typed as real enums, not strings, so
    FastAPI validates them before this function ever runs.
    """
    exercises = list_exercises(
        db, muscle_group=muscle_group, equipment=equipment, difficulty=difficulty
    )
    return [ExerciseResponse.model_validate(exercise) for exercise in exercises]


@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise_route(exercise_id: str, db: DbSession) -> ExerciseResponse:
    exercise = get_exercise(db, exercise_id)
    return ExerciseResponse.model_validate(exercise)
