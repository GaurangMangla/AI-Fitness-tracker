"""`/users/me` (GET and PATCH) — always the *current* authenticated user, never
a user looked up by id. There is no "get any user by id" endpoint in this
milestone, deliberately: nothing in the app needs to look up another user
yet, and not building that endpoint means there's no need to design an
authorization rule for it either.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import ProfileUpdate, UserResponse
from app.services.user_service import build_user_response, update_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: CurrentUser) -> UserResponse:
    return build_user_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(data: ProfileUpdate, current_user: CurrentUser, db: DbSession) -> UserResponse:
    user = update_profile(db, current_user, data)
    return build_user_response(user)
