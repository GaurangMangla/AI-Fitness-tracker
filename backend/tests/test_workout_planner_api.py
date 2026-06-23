"""Integration tests for the Milestone 2.3 workout planner endpoints.

Tests cover:
  POST /workouts/generate  — full flow, validation errors, deactivation
  GET  /workouts/current   — happy path and 404 when no plan exists
  GET  /workouts/today     — happy path and rest-day 404
"""

from fastapi.testclient import TestClient

from tests.factories import unique_email as make_email

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_onboard(
    client: TestClient,
    *,
    experience: str = "intermediate",
    equipment: list[str] | None = None,
    goal: str = "muscle_gain",
) -> dict[str, str]:
    """Register, login, and complete onboarding. Returns auth headers."""
    if equipment is None:
        equipment = ["full_gym"]

    email = make_email("wp")
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPass123!"},
    )
    assert r.status_code == 201, r.json()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patch = client.patch(
        "/api/v1/users/me",
        json={
            "name": "Integration Tester",
            "age": 28,
            "gender": "male",
            "height_cm": 178.0,
            "weight_kg": 80.0,
            "fitness_goal": goal,
            "activity_level": "moderately_active",
            "workout_experience": experience,
            "equipment_available": equipment,
            "diet_preference": "non_vegetarian",
        },
        headers=headers,
    )
    assert patch.status_code == 200, patch.json()
    return headers


# ---------------------------------------------------------------------------
# POST /workouts/generate
# ---------------------------------------------------------------------------


class TestGenerateWorkoutPlan:
    def test_returns_201_with_full_plan(self, client: TestClient):
        headers = _register_and_onboard(client)
        r = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        assert r.status_code == 201, r.json()
        data = r.json()
        assert data["active"] is True
        assert len(data["days"]) == 3
        assert data["split_name"]
        assert data["difficulty"]
        assert data["estimated_duration_minutes"] > 0

    def test_each_day_has_exercises(self, client: TestClient):
        headers = _register_and_onboard(client)
        r = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 4},
            headers=headers,
        )
        assert r.status_code == 201
        for day in r.json()["days"]:
            assert len(day["workout_exercises"]) > 0, f"Day {day['day_name']} has no exercises"

    def test_exercises_include_sets_reps_rest(self, client: TestClient):
        headers = _register_and_onboard(client)
        r = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        assert r.status_code == 201
        day = r.json()["days"][0]
        we = day["workout_exercises"][0]
        assert we["sets"] > 0
        assert we["reps"]
        assert we["rest_seconds"] >= 0

    def test_generates_plan_for_bodyweight_user(self, client: TestClient):
        headers = _register_and_onboard(
            client, experience="beginner", equipment=["none"], goal="general_fitness"
        )
        r = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert len(data["days"]) > 0
        # All exercises must be bodyweight
        for day in data["days"]:
            for we in day["workout_exercises"]:
                assert we["exercise"]["equipment"] == "bodyweight", (
                    f"{we['exercise']['name']} uses {we['exercise']['equipment']} "
                    f"but user has no equipment"
                )

    def test_second_generate_deactivates_first(self, client: TestClient):
        headers = _register_and_onboard(client)

        r1 = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        assert r1.status_code == 201
        plan1_id = r1.json()["id"]

        r2 = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 4},
            headers=headers,
        )
        assert r2.status_code == 201
        plan2_id = r2.json()["id"]
        assert plan1_id != plan2_id

        # Current plan should now be the second one
        current = client.get("/api/v1/workouts/current", headers=headers)
        assert current.status_code == 200
        assert current.json()["id"] == plan2_id

    def test_requires_authentication(self, client: TestClient):
        r = client.post("/api/v1/workouts/generate", json={"workout_days_per_week": 3})
        assert r.status_code == 401

    def test_requires_onboarding(self, client: TestClient):
        """User who registered but never onboarded should get 422."""
        email = make_email("noprofile")
        r = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "TestPass123!"},
        )
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r2 = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        assert r2.status_code == 422

    def test_validates_workout_days_range(self, client: TestClient):
        headers = _register_and_onboard(client)
        # 0 is below minimum
        r = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 0},
            headers=headers,
        )
        assert r.status_code == 422

        # 8 is above maximum
        r2 = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 8},
            headers=headers,
        )
        assert r2.status_code == 422

    def test_response_schema_has_all_required_fields(self, client: TestClient):
        headers = _register_and_onboard(client)
        r = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        for field in (
            "id",
            "user_id",
            "title",
            "goal",
            "experience",
            "workout_days",
            "active",
            "created_at",
            "days",
            "split_name",
            "difficulty",
            "estimated_duration_minutes",
        ):
            assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# GET /workouts/current
# ---------------------------------------------------------------------------


class TestGetCurrentPlan:
    def test_returns_active_plan(self, client: TestClient):
        headers = _register_and_onboard(client)
        client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        r = client.get("/api/v1/workouts/current", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["active"] is True
        assert len(data["days"]) == 3

    def test_404_when_no_plan_exists(self, client: TestClient):
        headers = _register_and_onboard(client)
        r = client.get("/api/v1/workouts/current", headers=headers)
        assert r.status_code == 404

    def test_requires_authentication(self, client: TestClient):
        r = client.get("/api/v1/workouts/current")
        assert r.status_code == 401

    def test_includes_exercises_in_days(self, client: TestClient):
        headers = _register_and_onboard(client)
        client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 3},
            headers=headers,
        )
        r = client.get("/api/v1/workouts/current", headers=headers)
        assert r.status_code == 200
        for day in r.json()["days"]:
            assert "workout_exercises" in day
            assert len(day["workout_exercises"]) > 0

    def test_current_plan_matches_last_generated(self, client: TestClient):
        headers = _register_and_onboard(client)
        gen = client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 5},
            headers=headers,
        )
        generated_id = gen.json()["id"]

        current = client.get("/api/v1/workouts/current", headers=headers)
        assert current.json()["id"] == generated_id


# ---------------------------------------------------------------------------
# GET /workouts/today
# ---------------------------------------------------------------------------


class TestGetTodaysWorkout:
    def test_returns_a_workout_day(self, client: TestClient):
        headers = _register_and_onboard(client)
        client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 7},  # 7 days = never a rest day
            headers=headers,
        )
        r = client.get("/api/v1/workouts/today", headers=headers)
        # With a 7-day plan every day is a training day — always 200
        assert r.status_code == 200
        data = r.json()
        assert data["day_name"]
        assert data["focus_area"]
        assert "workout_exercises" in data

    def test_today_exercises_have_full_detail(self, client: TestClient):
        headers = _register_and_onboard(client)
        client.post(
            "/api/v1/workouts/generate",
            json={"workout_days_per_week": 7},
            headers=headers,
        )
        r = client.get("/api/v1/workouts/today", headers=headers)
        assert r.status_code == 200
        for we in r.json()["workout_exercises"]:
            assert we["exercise"]["name"]
            assert we["sets"] > 0
            assert we["reps"]

    def test_404_when_no_plan_exists(self, client: TestClient):
        headers = _register_and_onboard(client)
        r = client.get("/api/v1/workouts/today", headers=headers)
        assert r.status_code == 404

    def test_requires_authentication(self, client: TestClient):
        r = client.get("/api/v1/workouts/today")
        assert r.status_code == 401
