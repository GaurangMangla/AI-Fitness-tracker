"""`/auth/register` and `/auth/login`."""

from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.core.security import create_access_token
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth_service import authenticate_user, register_user
from app.services.user_service import build_user_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> AuthResponse:
    """Create an account and log the user in immediately — returning a token
    on register (rather than making the client call `/login` right after)
    means the frontend can redirect straight into onboarding with one request
    instead of two."""
    user = register_user(db, data)
    return AuthResponse(
        user=build_user_response(user),
        access_token=create_access_token(user.id),
    )


@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, db: DbSession) -> AuthResponse:
    user = authenticate_user(db, data)
    return AuthResponse(
        user=build_user_response(user),
        access_token=create_access_token(user.id),
    )
