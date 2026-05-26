"""Business logic for `/users/me`."""

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.user import User
from app.repositories import profile_repository
from app.schemas.user import ProfileMetrics, ProfileResponse, ProfileUpdate, UserResponse
from app.services.metrics_service import bmi_category, calculate_bmi, calculate_daily_calories

# Every column on `Profile` except the primary key, FK, and timestamps —
# required to all be present the *first* time a profile is created, since
# they're all NOT NULL columns. Kept as a tuple of field names (matching
# `ProfileUpdate`'s fields) rather than re-deriving from the model, since the
# point is checking what the *request* provided, not introspecting the table.
_REQUIRED_PROFILE_FIELDS = (
    "name",
    "age",
    "gender",
    "height_cm",
    "weight_kg",
    "fitness_goal",
    "activity_level",
    "workout_experience",
    "equipment_available",
    "diet_preference",
)


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    """Create the profile on first submission (onboarding), or merge changes
    into an existing one (e.g. a later edit from a settings page).

    The "every field is required on first submission" rule lives here, in the
    service layer, rather than as a second, stricter schema — it's a business
    rule about *when* completeness is required (once, at creation), not a
    static shape `ProfileUpdate` itself should enforce on every call.
    """
    fields = data.model_dump(exclude_unset=True)
    existing_profile = user.profile

    if existing_profile is None:
        missing = [name for name in _REQUIRED_PROFILE_FIELDS if fields.get(name) is None]
        if missing:
            raise ValidationError(
                "Completing your profile for the first time requires every field. "
                f"Missing: {', '.join(missing)}."
            )
        user.profile = profile_repository.create(db, user_id=user.id, fields=fields)
    else:
        profile_repository.update(db, profile=existing_profile, fields=fields)

    return user


def build_user_response(user: User) -> UserResponse:
    """Assemble the `/users/me` response, including derived BMI/calorie
    metrics. Built field-by-field rather than `UserResponse.model_validate(user)`,
    since `metrics` isn't a real attribute on the ORM model — there's nothing
    to validate it from without computing it first.
    """
    profile = user.profile
    profile_response: ProfileResponse | None = None
    metrics: ProfileMetrics | None = None

    if profile is not None:
        profile_response = ProfileResponse.model_validate(profile)
        bmi = calculate_bmi(profile.weight_kg, profile.height_cm)
        metrics = ProfileMetrics(
            bmi=bmi,
            bmi_category=bmi_category(bmi),
            daily_calories=calculate_daily_calories(profile),
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        profile=profile_response,
        metrics=metrics,
    )
