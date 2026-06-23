"""Tests for `app.core.security`. Exercised in isolation, ahead of Feature 1
wiring these into actual auth endpoints."""

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_the_plaintext() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"


def test_verify_password_accepts_the_correct_password() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_verify_password_rejects_an_incorrect_password() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


def test_access_token_round_trips_to_the_same_user_id() -> None:
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_a_malformed_token_is_rejected() -> None:
    with pytest.raises(UnauthorizedError):
        decode_access_token("not-a-real-jwt")
