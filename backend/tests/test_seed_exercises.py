"""Tests for `app.db.seed_exercises`.

`test_seed_exercises_inserts_exactly_100_into_an_empty_database` uses its own
fully isolated in-memory engine rather than the shared `db` fixture — the
shared test database persists across the whole pytest session (the same
in-memory SQLite engine the app itself uses), so other tests that create
their own `Exercise` rows (e.g. `test_exercise_service.py`) mean the shared
table is generally *not* empty by the time this file's tests run. Asserting
"empty, then seed, then exactly 100" needs a database nothing else has
touched.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.seed_exercises import _EXERCISES, seed_exercises
from app.repositories import exercise_repository

_REQUIRED_MUSCLE_GROUPS = {"chest", "back", "shoulders", "legs", "arms", "core", "cardio"}


def test_seed_data_has_exactly_100_exercises() -> None:
    assert len(_EXERCISES) == 100


def test_seed_data_covers_every_required_muscle_group() -> None:
    groups = {row["muscle_group"] for row in _EXERCISES}
    assert groups == _REQUIRED_MUSCLE_GROUPS


def test_seed_data_names_are_unique() -> None:
    names = [row["name"] for row in _EXERCISES]
    assert len(names) == len(set(names))


def test_seed_exercises_inserts_exactly_100_into_an_empty_database() -> None:
    isolated_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=isolated_engine)
    isolated_session: Session = sessionmaker(bind=isolated_engine)()

    try:
        assert exercise_repository.count(isolated_session) == 0

        inserted = seed_exercises(isolated_session)

        assert inserted == 100
        assert exercise_repository.count(isolated_session) == 100
    finally:
        isolated_session.close()


def test_seed_exercises_is_idempotent(db: Session) -> None:
    """Regardless of how many rows already exist when this test runs, calling
    `seed_exercises` twice in a row must not change the count between those
    two calls — the second call is always a no-op once the first has run."""
    seed_exercises(db)
    count_after_first_call = exercise_repository.count(db)

    second_call_inserted = seed_exercises(db)

    assert second_call_inserted == 0
    assert exercise_repository.count(db) == count_after_first_call
