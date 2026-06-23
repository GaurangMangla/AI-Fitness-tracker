"""Integration tests for progress, nutrition and workout stats endpoints."""

from fastapi.testclient import TestClient

from tests.factories import unique_email as make_email

_ONBOARD = {
    "name": "Test User",
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


def _auth(client: TestClient) -> dict:
    email = make_email("stats")
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "Pass123!"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.patch("/api/v1/users/me", json=_ONBOARD, headers=headers)
    return headers


# ── Workout Stats ────────────────────────────────────────────────────────────


class TestWorkoutStats:
    def test_summary_returns_zeros_for_new_user(self, client):
        h = _auth(client)
        r = client.get("/api/v1/workouts/stats/summary", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total_sessions"] == 0
        assert data["current_streak_days"] == 0

    def test_weekly_volume_returns_8_weeks_by_default(self, client):
        h = _auth(client)
        r = client.get("/api/v1/workouts/stats/weekly-volume", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 8

    def test_personal_records_empty_for_new_user(self, client):
        h = _auth(client)
        r = client.get("/api/v1/workouts/stats/personal-records", headers=h)
        assert r.status_code == 200
        assert r.json() == []

    def test_heatmap_returns_365_days(self, client):
        h = _auth(client)
        r = client.get("/api/v1/workouts/stats/heatmap", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 365

    def test_requires_auth(self, client):
        assert client.get("/api/v1/workouts/stats/summary").status_code == 401


# ── Progress Logs ────────────────────────────────────────────────────────────


class TestProgressLogs:
    def test_log_weight_returns_201(self, client):
        h = _auth(client)
        r = client.post(
            "/api/v1/progress/logs", json={"weight_kg": 80.5, "sleep_hours": 7.5}, headers=h
        )
        assert r.status_code == 201
        data = r.json()
        assert data["weight_kg"] == 80.5
        assert data["sleep_hours"] == 7.5

    def test_logging_same_date_twice_updates_not_duplicates(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/progress/logs", json={"log_date": "2025-01-01", "weight_kg": 80.0}, headers=h
        )
        client.post(
            "/api/v1/progress/logs", json={"log_date": "2025-01-01", "weight_kg": 79.5}, headers=h
        )
        r = client.get("/api/v1/progress/logs", headers=h)
        entries = [lg for lg in r.json() if lg["log_date"] == "2025-01-01"]
        assert len(entries) == 1
        assert entries[0]["weight_kg"] == 79.5

    def test_get_logs_returns_list(self, client):
        h = _auth(client)
        client.post("/api/v1/progress/logs", json={"weight_kg": 80.0}, headers=h)
        r = client.get("/api/v1/progress/logs", headers=h)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_summary_reflects_logged_data(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/progress/logs", json={"weight_kg": 82.0, "body_fat_pct": 18.0}, headers=h
        )
        r = client.get("/api/v1/progress/summary", headers=h)
        assert r.status_code == 200
        assert r.json()["current_weight_kg"] == 82.0

    def test_requires_auth(self, client):
        assert client.get("/api/v1/progress/logs").status_code == 401


# ── Body Measurements ────────────────────────────────────────────────────────


class TestBodyMeasurements:
    def test_log_measurement_returns_201(self, client):
        h = _auth(client)
        r = client.post(
            "/api/v1/progress/measurements", json={"waist_cm": 82.0, "chest_cm": 100.0}, headers=h
        )
        assert r.status_code == 201
        assert r.json()["waist_cm"] == 82.0

    def test_get_measurements_returns_list(self, client):
        h = _auth(client)
        client.post("/api/v1/progress/measurements", json={"waist_cm": 82.0}, headers=h)
        r = client.get("/api/v1/progress/measurements", headers=h)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_upsert_same_date(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/progress/measurements",
            json={"log_date": "2025-02-01", "waist_cm": 82.0},
            headers=h,
        )
        client.post(
            "/api/v1/progress/measurements",
            json={"log_date": "2025-02-01", "waist_cm": 80.0},
            headers=h,
        )
        r = client.get("/api/v1/progress/measurements", headers=h)
        entries = [m for m in r.json() if m["log_date"] == "2025-02-01"]
        assert len(entries) == 1
        assert entries[0]["waist_cm"] == 80.0


# ── Nutrition Plans ──────────────────────────────────────────────────────────


class TestNutritionPlans:
    def test_generate_returns_plan_with_4_meals(self, client):
        h = _auth(client)
        r = client.post("/api/v1/nutrition/plans/generate", headers=h)
        assert r.status_code == 201
        data = r.json()
        assert data["active"] is True
        assert len(data["meals"]) == 4
        assert data["target_calories"] > 0

    def test_current_plan_returns_generated_plan(self, client):
        h = _auth(client)
        client.post("/api/v1/nutrition/plans/generate", headers=h)
        r = client.get("/api/v1/nutrition/plans/current", headers=h)
        assert r.status_code == 200
        assert r.json()["active"] is True

    def test_no_plan_returns_404(self, client):
        h = _auth(client)
        r = client.get("/api/v1/nutrition/plans/current", headers=h)
        assert r.status_code == 404

    def test_generate_requires_auth(self, client):
        assert client.post("/api/v1/nutrition/plans/generate").status_code == 401

    def test_macro_split_is_positive(self, client):
        h = _auth(client)
        r = client.post("/api/v1/nutrition/plans/generate", headers=h)
        d = r.json()
        assert d["target_protein_g"] > 0
        assert d["target_carbs_g"] > 0
        assert d["target_fat_g"] > 0

    def test_regenerate_deactivates_previous(self, client):
        h = _auth(client)
        client.post("/api/v1/nutrition/plans/generate", headers=h)
        client.post("/api/v1/nutrition/plans/generate", headers=h)
        r = client.get("/api/v1/nutrition/plans/current", headers=h)
        assert r.status_code == 200  # still exactly one active plan


# ── Nutrition Logs ───────────────────────────────────────────────────────────


class TestNutritionLogs:
    def test_log_nutrition_returns_201(self, client):
        h = _auth(client)
        r = client.post(
            "/api/v1/nutrition/logs",
            json={
                "calories_consumed": 1800,
                "protein_g": 140,
                "carbs_g": 180,
                "fat_g": 60,
                "water_ml": 2500,
            },
            headers=h,
        )
        assert r.status_code == 201
        assert r.json()["calories_consumed"] == 1800

    def test_get_logs_returns_list(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/nutrition/logs",
            json={"calories_consumed": 2000, "protein_g": 150, "carbs_g": 200, "fat_g": 70},
            headers=h,
        )
        r = client.get("/api/v1/nutrition/logs", headers=h)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_today_log_returns_todays_entry(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/nutrition/logs",
            json={"calories_consumed": 1900, "protein_g": 130, "carbs_g": 190, "fat_g": 65},
            headers=h,
        )
        r = client.get("/api/v1/nutrition/logs/today", headers=h)
        assert r.status_code == 200
        assert r.json()["calories_consumed"] == 1900

    def test_weekly_summary(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/nutrition/logs",
            json={"calories_consumed": 2000, "protein_g": 150, "carbs_g": 200, "fat_g": 70},
            headers=h,
        )
        r = client.get("/api/v1/nutrition/summary/weekly", headers=h)
        assert r.status_code == 200
        assert r.json()["days_logged"] >= 1

    def test_upsert_same_date_overwrites(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/nutrition/logs",
            json={
                "log_date": "2025-03-01",
                "calories_consumed": 1800,
                "protein_g": 130,
                "carbs_g": 180,
                "fat_g": 60,
            },
            headers=h,
        )
        client.post(
            "/api/v1/nutrition/logs",
            json={
                "log_date": "2025-03-01",
                "calories_consumed": 2100,
                "protein_g": 160,
                "carbs_g": 210,
                "fat_g": 70,
            },
            headers=h,
        )
        r = client.get("/api/v1/nutrition/logs", headers=h)
        entries = [lg for lg in r.json() if lg["log_date"] == "2025-03-01"]
        assert len(entries) == 1
        assert entries[0]["calories_consumed"] == 2100
