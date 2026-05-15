"""Nutrition models: NutritionPlan, Meal, NutritionLog.

NutritionPlan — a generated macro target + list of meals for the week.
Meal — one meal within a plan (breakfast/lunch/dinner/snack).
NutritionLog — a user's actual daily intake (what they ate vs. the plan).
"""

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DietPreference, MealType


class NutritionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_plans"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    diet_type: Mapped[DietPreference] = mapped_column(
        Enum(DietPreference, native_enum=False), nullable=False
    )

    # Daily macro targets
    target_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    target_protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    target_carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    target_fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    target_water_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=2500)

    meals: Mapped[list["Meal"]] = relationship(
        back_populates="nutrition_plan",
        cascade="all, delete-orphan",
        order_by="Meal.meal_type",
    )


class Meal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meals"

    nutrition_plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("nutrition_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType, native_enum=False), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    nutrition_plan: Mapped["NutritionPlan"] = relationship(back_populates="meals")


class NutritionLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Daily actual intake — what the user ate, not what the plan says."""

    __tablename__ = "nutrition_logs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    calories_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    water_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
