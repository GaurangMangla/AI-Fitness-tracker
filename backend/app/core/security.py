"""Security primitives: password hashing and JWT creation/verification.

Infrastructure only at this point in Project Setup — nothing calls these yet.
Feature 1 (Authentication) wires them into `/auth/register` and `/auth/login`.

Design decisions:
- Passwords are hashed with bcrypt, calling the `bcrypt` package directly
  rather than going through `passlib`. `passlib` is the more commonly
  recommended wrapper, but its last release was in 2020 and it's incompatible
  with modern bcrypt releases (4.x/5.x removed an internal module passlib's
  version-detection depends on) — calling bcrypt directly avoids an
  unmaintained dependency and one less layer around a security-critical
  function.
- JWTs are handled with `PyJWT`, the actively-maintained library FastAPI's own
  docs now point to (rather than `python-jose`).
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from jwt import PyJWTError

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError, ValidationError

# bcrypt only ever uses the first 72 bytes of its input — longer passwords are
# rejected explicitly rather than silently truncated.
_MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage. Never store or log the plaintext."""
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > _MAX_PASSWORD_BYTES:
        raise ValidationError("Password is too long (max 72 bytes).")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > _MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(user_id: str | UUID) -> str:
    """Create a signed JWT for the given user id, valid for
    `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 7 days — see `core/config.py` for
    why this project uses one long-lived token rather than access+refresh
    rotation)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """Decode and validate a JWT, returning the user id (`sub` claim) it was
    issued for. Raises `UnauthorizedError` for every failure mode (expired,
    malformed, bad signature) — callers only ever need to handle one error
    type."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Token is missing a subject claim.")
    return str(subject)
