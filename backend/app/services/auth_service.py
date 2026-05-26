"""Business logic for registration and login.

Kept as plain functions, not a class — there's no shared state between them
worth wrapping in a constructor, and FastAPI's dependency injection works
equally well with module-level functions.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import LoginRequest, RegisterRequest


def register_user(db: Session, data: RegisterRequest) -> User:
    if user_repository.get_by_email(db, data.email) is not None:
        raise ConflictError("An account with this email already exists.")

    return user_repository.create(db, email=data.email, password_hash=hash_password(data.password))


def authenticate_user(db: Session, data: LoginRequest) -> User:
    user = user_repository.get_by_email(db, data.email)

    # Deliberately the same error for "no such user" and "wrong password" —
    # distinguishing them would let an attacker enumerate which emails are
    # registered.
    invalid_credentials = UnauthorizedError("Incorrect email or password.")

    if user is None:
        raise invalid_credentials
    if not verify_password(data.password, user.password_hash):
        raise invalid_credentials

    return user
