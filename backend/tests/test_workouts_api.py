"""Integration tests for `POST /workouts/recommend`."""

from fastapi.testclient import TestClient

from tests.factories import unique_email

_ONBOARDING_PAYLOAD = {
    "name": "Workout Tester",
    "age": 27,
    "gender": "male",
    "height_cm": 180,
    "weight_kg": 78,
    "fitness_goal": "muscle_gain",
    "activity_level": "moderately_active",
    "workout_experience": "intermediate",
    "equipment_available": ["full_gym"],
    "diet_preference": "non_vegetarian",
}


def _register_and_onboard(client: TestClient, *, onboard: bool = True) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email("workoutuser"), "password": "correct-horse-battery-staple"},
    )
    token: str = response.json()["access_token"]
    if onboard:
        client.patch(
            "/api/v1/users/me",
            json=_ONBOARDING_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
    return token


def test_recommend_workout_split_returns_a_full_recommendation(client: TestClient) -> None:
    token = _register_and_onboard(client)

    response = client.post(
        "/api/v1/workouts/recommend",
        json={"workout_days_per_week": 5},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["split_name"] == "Push Pull Legs"
    assert body["title"] == "Muscle Gain Plan"
    assert body["workout_days"] == 5
    assert body["difficulty"] == "Intermediate"
    assert "Muscle Gain" in body["reason"]


def test_recommend_workout_split_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/workouts/recommend", json={"workout_days_per_week": 4})
    assert response.status_code == 401


def test_recommend_workout_split_rejects_incomplete_onboarding(client: TestClient) -> None:
    token = _register_and_onboard(client, onboard=False)

    response = client.post(
        "/api/v1/workouts/recommend",
        json={"workout_days_per_week": 4},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert "profile" in response.json()["detail"].lower()


def test_recommend_workout_split_rejects_an_out_of_range_day_count(client: TestClient) -> None:
    token = _register_and_onboard(client)

    response = client.post(
        "/api/v1/workouts/recommend",
        json={"workout_days_per_week": 8},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_recommend_workout_split_rejects_a_missing_day_count(client: TestClient) -> None:
    token = _register_and_onboard(client)

    response = client.post(
        "/api/v1/workouts/recommend", json={}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422


def test_recommend_workout_split_does_not_persist_anything(client: TestClient) -> None:
    """Calling the endpoint twice with different day counts returns two
    independent, differing results — nothing from the first call is saved
    and reused for the second."""
    token = _register_and_onboard(client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/api/v1/workouts/recommend", json={"workout_days_per_week": 3}, headers=headers
    )
    second = client.post(
        "/api/v1/workouts/recommend", json={"workout_days_per_week": 5}, headers=headers
    )

    assert first.json()["workout_days"] == 3
    assert second.json()["workout_days"] == 5
