"""Data access for `Profile`."""

from sqlalchemy.orm import Session

from app.models.profile import Profile


def get_by_user_id(db: Session, user_id: str) -> Profile | None:
    return db.query(Profile).filter(Profile.user_id == user_id).one_or_none()


def create(db: Session, *, user_id: str, fields: dict) -> Profile:
    profile = Profile(user_id=user_id, **fields)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update(db: Session, *, profile: Profile, fields: dict) -> Profile:
    """Apply only the fields actually supplied (already filtered to non-None
    by the caller — see `user_service.update_profile`) onto an existing row."""
    for key, value in fields.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile
