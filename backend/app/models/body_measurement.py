"""BodyMeasurement — circumference measurements in centimetres.

Separate from ProgressLog because measurements are taken much less
frequently (typically every 2–4 weeks) and the two tables would otherwise
have lots of nullable columns in a single row. Keeping them separate makes
each insert more meaningful and the analytics cleaner.
"""

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BodyMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "body_measurements"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # All optional — record whatever the user measured
    chest_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hips_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    left_arm_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    right_arm_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    left_thigh_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    right_thigh_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
