"""BMI and daily-calorie estimation.

Pure functions, no DB access — easy to unit test and easy to reuse later from
the (not-yet-built) workout/diet generators, which will need the same numbers.

Formula choices, both standard and worth being able to cite in an interview:
- **BMI**: `weight_kg / height_m^2`, the standard WHO formula. Categories use
  the standard WHO adult thresholds (underweight/normal/overweight/obese).
- **BMR**: the Mifflin-St Jeor equation, generally considered more accurate
  for a general population than the older Harris-Benedict formula:
  - Men:   10 * weight_kg + 6.25 * height_cm - 5 * age + 5
  - Women: 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
  For `gender == "other"`, the male and female results are averaged. This is
  an approximation, not a third validated formula — Mifflin-St Jeor doesn't
  define one — but it's a defensible midpoint rather than silently defaulting
  to one gender's formula.
- **TDEE** (daily calorie estimate): BMR multiplied by a standard activity
  factor (1.2 sedentary → 1.9 extremely active), the conventional approach
  used by most calorie calculators.
"""

from app.models.enums import ActivityLevel, Gender
from app.models.profile import Profile

_ACTIVITY_MULTIPLIERS: dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.lightly_active: 1.375,
    ActivityLevel.moderately_active: 1.55,
    ActivityLevel.very_active: 1.725,
    ActivityLevel.extra_active: 1.9,
}


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 1)


def bmi_category(bmi: float) -> str:
    """Standard WHO adult BMI categories."""
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "overweight"
    return "obese"


def _calculate_bmr(*, weight_kg: float, height_cm: float, age: int, gender: Gender) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender == Gender.male:
        return base + 5
    if gender == Gender.female:
        return base - 161
    # gender == "other": average of the male and female offsets (+5 and -161)
    return base + (5 - 161) / 2


def calculate_daily_calories(profile: Profile) -> int:
    bmr = _calculate_bmr(
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        gender=profile.gender,
    )
    tdee = bmr * _ACTIVITY_MULTIPLIERS[profile.activity_level]
    return round(tdee)
