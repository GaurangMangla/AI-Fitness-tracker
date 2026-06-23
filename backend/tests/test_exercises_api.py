"""Integration tests for `GET /exercises` and `GET /exercises/{id}`.

Assertions here are deliberately written to be robust to *extra* exercise
rows existing in the table (e.g. ones created directly by
`test_exercise_service.py`'s unit tests against the same shared test
database) — checking "every seeded exercise is present" rather than "there
are exactly N exercises" is both more robust and a more meaningful check of
seed-data integrity anyway. See `tests/factories.py` for the same philosophy
applied to user emails.
"""

from fastapi.testclient import TestClient

from app.db.seed_exercises import _EXERCISES

_SEEDED_NAMES = {row["name"] for row in _EXERCISES}
_REQUIRED_MUSCLE_GROUPS = {"chest", "back", "shoulders", "legs", "arms", "core", "cardio"}


def test_list_exercises_includes_the_full_seeded_library(client: TestClient) -> None:
    response = client.get("/api/v1/exercises")

    assert response.status_code == 200
    body = response.json()
    names = {item["name"] for item in body}
    assert _SEEDED_NAMES.issubset(names)
    assert len(body) >= 100


def test_seeded_library_covers_every_required_muscle_group(client: TestClient) -> None:
    body = client.get("/api/v1/exercises").json()
    groups = {item["muscle_group"] for item in body}
    assert groups == _REQUIRED_MUSCLE_GROUPS


def test_every_exercise_has_required_fields_populated(client: TestClient) -> None:
    """Data-quality check on the seed data: every row has real instructions,
    a real name, and sane numeric fields — would catch an accidentally-blank
    field in the seed list."""
    body = client.get("/api/v1/exercises").json()
    for item in body:
        assert item["name"].strip()
        assert item["instructions"].strip()
        assert item["default_sets"] >= 1
        assert item["default_reps"].strip()
        assert item["rest_seconds"] >= 0


def test_list_exercises_filters_by_muscle_group(client: TestClient) -> None:
    response = client.get("/api/v1/exercises", params={"muscle_group": "chest"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["muscle_group"] == "chest" for item in body)


def test_list_exercises_filters_by_equipment(client: TestClient) -> None:
    response = client.get("/api/v1/exercises", params={"equipment": "barbell"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["equipment"] == "barbell" for item in body)


def test_list_exercises_filters_by_difficulty(client: TestClient) -> None:
    response = client.get("/api/v1/exercises", params={"difficulty": "advanced"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["difficulty"] == "advanced" for item in body)


def test_list_exercises_combines_filters_with_and(client: TestClient) -> None:
    response = client.get(
        "/api/v1/exercises", params={"muscle_group": "legs", "difficulty": "beginner"}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(item["muscle_group"] == "legs" and item["difficulty"] == "beginner" for item in body)


def test_list_exercises_rejects_an_invalid_muscle_group(client: TestClient) -> None:
    response = client.get("/api/v1/exercises", params={"muscle_group": "not-a-real-group"})
    assert response.status_code == 422


def test_list_exercises_rejects_an_invalid_difficulty(client: TestClient) -> None:
    response = client.get("/api/v1/exercises", params={"difficulty": "expert"})
    assert response.status_code == 422


def test_get_exercise_by_id_returns_full_detail(client: TestClient) -> None:
    listing = client.get("/api/v1/exercises").json()
    first_id = listing[0]["id"]

    response = client.get(f"/api/v1/exercises/{first_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == first_id
    assert body["instructions"]
    assert body["default_sets"] > 0


def test_get_exercise_with_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/exercises/does-not-exist")
    assert response.status_code == 404
