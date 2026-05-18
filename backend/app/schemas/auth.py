"""Schemas for `/auth/register` and `/auth/login`.

Both endpoints return the same `AuthResponse` shape (user + token) — the
frontend needs to know whether the user has a completed profile right after
either action, to decide whether to route to onboarding or straight to the
dashboard, without a second round trip.
"""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    # max_length=72 matches bcrypt's hashing limit (see app/core/security.py) —
    # validated here too so a too-long password fails with a normal 422 field
    # error instead of the ValidationError raised deeper in hash_password.
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
