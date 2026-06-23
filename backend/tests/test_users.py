"""Tests for `GET /users/me` and `PATCH /users/me`."""

from fastapi.testclient import TestClient

from tests.factories import unique_email

_ONBOARDING_PAYLOAD = {
    "name": "Jane Doe",
    "age": 28,
    "gender": "female",
    "height_cm": 165,
    "weight_kg": 60,
    "fitness_goal": "weight_loss",
    "activity_level": "moderately_active",
    "workout_experience": "beginner",
    "equipment_available": ["dumbbells", "resistance_bands"],
    "diet_preference": "vegetarian",
}


def _register_and_get_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email("onboarding"), "password": "correct-horse-battery-staple"},
    )
    return response.json()["access_token"]


def test_get_me_without_a_token_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_get_me_with_an_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_get_me_right_after_register_has_no_profile_or_metrics(client: TestClient) -> None:
    token = _register_and_get_token(client)

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["profile"] is None
    assert body["metrics"] is None


def test_completing_onboarding_creates_a_profile_with_computed_metrics(
    client: TestClient,
) -> None:
    token = _register_and_get_token(client)

    response = client.patch(
        "/api/v1/users/me",
        json=_ONBOARDING_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["name"] == "Jane Doe"
    assert body["profile"]["equipment_available"] == ["dumbbells", "resistance_bands"]
    assert body["metrics"]["bmi"] > 0
    assert body["metrics"]["daily_calories"] > 0
    assert body["metrics"]["bmi_category"] in {
        "underweight",
        "normal",
        "overweight",
        "obese",
    }


def test_onboarding_with_missing_fields_is_rejected(client: TestClient) -> None:
    token = _register_and_get_token(client)
    incomplete_payload = {"name": "Jane Doe", "age": 28}

    response = client.patch(
        "/api/v1/users/me",
        json=incomplete_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert "Missing" in response.json()["detail"]


def test_a_later_partial_update_merges_into_the_existing_profile(client: TestClient) -> None:
    token = _register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.patch("/api/v1/users/me", json=_ONBOARDING_PAYLOAD, headers=headers)

    response = client.patch("/api/v1/users/me", json={"weight_kg": 58}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["weight_kg"] == 58
    # Untouched fields survive the partial update.
    assert body["profile"]["name"] == "Jane Doe"
    assert body["profile"]["diet_preference"] == "vegetarian"


def test_onboarding_rejects_an_invalid_enum_value(client: TestClient) -> None:
    token = _register_and_get_token(client)
    payload = {**_ONBOARDING_PAYLOAD, "fitness_goal": "not-a-real-goal"}

    response = client.patch(
        "/api/v1/users/me", json=payload, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422
