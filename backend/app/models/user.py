"""The `User` model — authentication identity only (email + password hash).

Fitness/onboarding data deliberately lives on a separate `Profile` model
(`app/models/profile.py`), not here: a user can exist (registered, able to log
in) before they've completed onboarding. Keeping the two separate means
"registered but not onboarded" is just "profile is None" rather than a model
full of nullable fields with no clear meaning for when they're empty.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    profile: Mapped["Profile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
