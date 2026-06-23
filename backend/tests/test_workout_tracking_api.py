"""Integration tests for Milestone 2.5 workout tracking endpoints.

Covers:
  POST /workouts/start
  POST /workouts/{session_id}/pause
  POST /workouts/{session_id}/resume
  POST /workouts/{session_id}/exercise/{exercise_id}/complete
  POST /workouts/{session_id}/exercise/{exercise_id}/skip
  POST /workouts/{session_id}/finish
  GET  /workouts/history
  GET  /workouts/history/{session_id}
"""

from fastapi.testclient import TestClient

from tests.factories import unique_email as make_email

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ONBOARD_PAYLOAD = {
    "name": "Tracker Test",
    "age": 28,
    "gender": "male",
    "height_cm": 178.0,
    "weight_kg": 80.0,
    "fitness_goal": "muscle_gain",
    "activity_level": "moderately_active",
    "workout_experience": "intermediate",
    "equipment_available": ["full_gym"],
    "diet_preference": "non_vegetarian",
}


def _register_onboard_generate(client: TestClient) -> tuple[dict, str, str]:
    """Register → onboard → generate a 7-day plan (never a rest day).
    Returns (auth_headers, plan_id, first_workout_exercise_id_for_today)."""
    email = make_email("tr")
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPass123!"},
    )
    assert r.status_code == 201, r.json()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.patch("/api/v1/users/me", json=_ONBOARD_PAYLOAD, headers=headers)

    gen = client.post(
        "/api/v1/workouts/generate",
        json={"workout_days_per_week": 7},
        headers=headers,
    )
    assert gen.status_code == 201, gen.json()
    plan = gen.json()

    # Figure out today's day the same way the backend does (ISO weekday mod 7)
    from datetime import datetime

    today_iso = datetime.now().isoweekday()
    day_index = (today_iso - 1) % 7
    today_day = sorted(plan["days"], key=lambda d: d["day_number"])[day_index]
    we_id = today_day["workout_exercises"][0]["id"]

    return headers, plan["id"], we_id


def _start(client, headers) -> dict:
    r = client.post("/api/v1/workouts/start", headers=headers)
    assert r.status_code == 201, r.json()
    return r.json()


# ---------------------------------------------------------------------------
# POST /workouts/start
# ---------------------------------------------------------------------------


class TestStartWorkout:
    def test_creates_active_session(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        r = client.post("/api/v1/workouts/start", headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "active"
        assert data["completed_at"] is None
        assert "id" in data

    def test_returns_409_if_session_already_active(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        client.post("/api/v1/workouts/start", headers=headers)
        r = client.post("/api/v1/workouts/start", headers=headers)
        assert r.status_code == 409

    def test_returns_404_without_a_plan(self, client: TestClient):
        email = make_email("noplan")
        r = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Pass123!"},
        )
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.patch("/api/v1/users/me", json=_ONBOARD_PAYLOAD, headers=headers)

        r2 = client.post("/api/v1/workouts/start", headers=headers)
        assert r2.status_code == 404

    def test_requires_authentication(self, client: TestClient):
        r = client.post("/api/v1/workouts/start")
        assert r.status_code == 401

    def test_response_includes_plan_and_day_ids(self, client: TestClient):
        headers, plan_id, _ = _register_onboard_generate(client)
        data = _start(client, headers)
        assert data["workout_plan_id"] == plan_id
        assert data["workout_day_id"]


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/pause and /resume
# ---------------------------------------------------------------------------


class TestPauseResume:
    def test_pause_sets_status_paused(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(f"/api/v1/workouts/{session['id']}/pause", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "paused"

    def test_resume_sets_status_active(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(f"/api/v1/workouts/{session['id']}/pause", headers=headers)
        r = client.post(f"/api/v1/workouts/{session['id']}/resume", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_cannot_pause_twice(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(f"/api/v1/workouts/{session['id']}/pause", headers=headers)
        r = client.post(f"/api/v1/workouts/{session['id']}/pause", headers=headers)
        assert r.status_code == 409

    def test_cannot_resume_active_session(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(f"/api/v1/workouts/{session['id']}/resume", headers=headers)
        assert r.status_code == 409

    def test_404_for_wrong_user(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)

        other_email = make_email("other")
        r2 = client.post(
            "/api/v1/auth/register",
            json={"email": other_email, "password": "Pass123!"},
        )
        other_headers = {"Authorization": f"Bearer {r2.json()['access_token']}"}
        r3 = client.post(f"/api/v1/workouts/{session['id']}/pause", headers=other_headers)
        assert r3.status_code == 404


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/exercise/{exercise_id}/complete
# ---------------------------------------------------------------------------


class TestCompleteExercise:
    def test_marks_exercise_completed(self, client: TestClient):
        headers, _, we_id = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(
            f"/api/v1/workouts/{session['id']}/exercise/{we_id}/complete",
            json={},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["completed"] is True
        assert data["skipped"] is False

    def test_respects_submitted_sets_reps(self, client: TestClient):
        headers, _, we_id = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(
            f"/api/v1/workouts/{session['id']}/exercise/{we_id}/complete",
            json={"completed_sets": 2, "completed_reps": "10"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["completed_sets"] == 2
        assert r.json()["completed_reps"] == "10"

    def test_returns_404_for_wrong_exercise(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(
            f"/api/v1/workouts/{session['id']}/exercise/not-a-real-id/complete",
            json={},
            headers=headers,
        )
        assert r.status_code == 404

    def test_returns_409_for_finished_session(self, client: TestClient):
        headers, _, we_id = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)
        r = client.post(
            f"/api/v1/workouts/{session['id']}/exercise/{we_id}/complete",
            json={},
            headers=headers,
        )
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/exercise/{exercise_id}/skip
# ---------------------------------------------------------------------------


class TestSkipExercise:
    def test_marks_exercise_skipped(self, client: TestClient):
        headers, _, we_id = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(
            f"/api/v1/workouts/{session['id']}/exercise/{we_id}/skip",
            json={},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["skipped"] is True
        assert data["completed"] is False

    def test_can_add_notes_when_skipping(self, client: TestClient):
        headers, _, we_id = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(
            f"/api/v1/workouts/{session['id']}/exercise/{we_id}/skip",
            json={"notes": "Injury"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["notes"] == "Injury"


# ---------------------------------------------------------------------------
# POST /workouts/{session_id}/finish
# ---------------------------------------------------------------------------


class TestFinishWorkout:
    def test_returns_summary_with_required_fields(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)
        assert r.status_code == 200
        data = r.json()
        for field in (
            "session",
            "total_duration_minutes",
            "exercises_completed",
            "exercises_skipped",
            "calories_burned_estimate",
        ):
            assert field in data, f"Missing: {field}"

    def test_session_status_is_completed_after_finish(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        r = client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)
        assert r.json()["session"]["status"] == "completed"
        assert r.json()["session"]["completed_at"] is not None

    def test_counts_completed_and_skipped_exercises(self, client: TestClient):
        headers, _, we_id = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(
            f"/api/v1/workouts/{session['id']}/exercise/{we_id}/complete",
            json={},
            headers=headers,
        )
        r = client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)
        data = r.json()
        assert data["exercises_completed"] == 1
        assert data["exercises_skipped"] == 0

    def test_cannot_finish_twice(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)
        r = client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)
        assert r.status_code == 409

    def test_can_start_new_session_after_finishing(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)
        r = client.post("/api/v1/workouts/start", headers=headers)
        assert r.status_code == 201

    def test_requires_authentication(self, client: TestClient):
        r = client.post("/api/v1/workouts/fake-id/finish")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /workouts/history  and  GET /workouts/history/{session_id}
# ---------------------------------------------------------------------------


class TestWorkoutHistory:
    def test_empty_history_before_any_workout(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        r = client.get("/api/v1/workouts/history", headers=headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_finished_session_appears_in_history(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)

        r = client.get("/api/v1/workouts/history", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["id"] == session["id"]
        assert data[0]["status"] == "completed"

    def test_active_session_not_in_history(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        _start(client, headers)
        r = client.get("/api/v1/workouts/history", headers=headers)
        assert r.json() == []

    def test_history_detail_returns_exercise_completions(self, client: TestClient):
        headers, _, we_id = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(
            f"/api/v1/workouts/{session['id']}/exercise/{we_id}/complete",
            json={},
            headers=headers,
        )
        client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)

        r = client.get(f"/api/v1/workouts/history/{session['id']}", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data["exercise_completions"]) == 1
        assert data["exercise_completions"][0]["completed"] is True

    def test_history_detail_404_for_wrong_user(self, client: TestClient):
        headers, _, _ = _register_onboard_generate(client)
        session = _start(client, headers)
        client.post(f"/api/v1/workouts/{session['id']}/finish", headers=headers)

        other_email = make_email("hist")
        r2 = client.post(
            "/api/v1/auth/register",
            json={"email": other_email, "password": "Pass123!"},
        )
        other_headers = {"Authorization": f"Bearer {r2.json()['access_token']}"}
        r3 = client.get(f"/api/v1/workouts/history/{session['id']}", headers=other_headers)
        assert r3.status_code == 404

    def test_requires_authentication(self, client: TestClient):
        r = client.get("/api/v1/workouts/history")
        assert r.status_code == 401
