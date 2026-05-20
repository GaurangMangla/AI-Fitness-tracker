"""Data access for `User`. The only module allowed to query `users` directly —
services call these functions rather than touching the ORM session themselves.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def create(db: Session, *, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
