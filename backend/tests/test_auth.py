"""Tests for `POST /auth/register` and `POST /auth/login`."""

from fastapi.testclient import TestClient

from tests.factories import unique_email


def test_register_creates_a_user_and_returns_a_token(client: TestClient) -> None:
    email = unique_email("newuser")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == email
    assert body["user"]["profile"] is None
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_register_rejects_a_duplicate_email(client: TestClient) -> None:
    payload = {"email": unique_email("duplicate"), "password": "correct-horse-battery-staple"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409


def test_register_rejects_a_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email("shortpw"), "password": "short"},
    )
    assert response.status_code == 422


def test_register_rejects_an_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 422


def test_login_succeeds_with_correct_credentials(client: TestClient) -> None:
    payload = {"email": unique_email("logsuccess"), "password": "correct-horse-battery-staple"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_rejects_an_incorrect_password(client: TestClient) -> None:
    email = unique_email("wrongpw")
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_rejects_a_nonexistent_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email("doesnotexist"), "password": "whatever-password"},
    )
    assert response.status_code == 401
