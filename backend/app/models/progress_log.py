"""ProgressLog — one daily snapshot of a user's measurable stats.

One row per user per date — logging twice on the same day overwrites via the
service layer's upsert logic rather than creating a duplicate row. The date
is stored as a string in ISO format (YYYY-MM-DD) rather than a Date column
because SQLite doesn't have a native Date type, and the app always works in
the user's local date anyway.
"""

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProgressLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "progress_logs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Nullable — the user logs whichever they have on hand, not all at once
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
