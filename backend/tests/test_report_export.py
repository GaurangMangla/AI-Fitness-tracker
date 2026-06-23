"""Integration tests for GET /progress/export (CSV/PDF progress reports)."""

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
    email = make_email("export")
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "Pass123!"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.patch("/api/v1/users/me", json=_ONBOARD, headers=headers)
    return headers


class TestReportExport:
    def test_csv_export_default_format(self, client):
        h = _auth(client)
        r = client.get("/api/v1/progress/export", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "attachment" in r.headers["content-disposition"]
        assert "Athlyt Progress Report" in r.text

    def test_csv_export_explicit_format(self, client):
        h = _auth(client)
        r = client.get("/api/v1/progress/export?format=csv", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")

    def test_csv_export_includes_logged_data(self, client):
        h = _auth(client)
        client.post(
            "/api/v1/progress/logs",
            json={"log_date": "2025-01-01", "weight_kg": 79.5, "sleep_hours": 7.5},
            headers=h,
        )
        client.post(
            "/api/v1/nutrition/logs",
            json={
                "log_date": "2025-01-01",
                "calories_consumed": 2000,
                "protein_g": 150,
                "carbs_g": 200,
                "fat_g": 70,
            },
            headers=h,
        )
        r = client.get("/api/v1/progress/export", headers=h)
        assert r.status_code == 200
        assert "79.5" in r.text
        assert "2000" in r.text

    def test_pdf_export(self, client):
        h = _auth(client)
        r = client.get("/api/v1/progress/export?format=pdf", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert "attachment" in r.headers["content-disposition"]
        assert r.content.startswith(b"%PDF")

    def test_invalid_format_returns_422(self, client):
        h = _auth(client)
        r = client.get("/api/v1/progress/export?format=xml", headers=h)
        assert r.status_code == 422

    def test_requires_auth(self, client):
        assert client.get("/api/v1/progress/export").status_code == 401
