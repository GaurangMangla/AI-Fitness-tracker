"""Unit tests for `app.services.metrics_service`.

Reference values are worked out by hand against the formulas documented in
the module itself (WHO BMI, Mifflin-St Jeor BMR × activity multiplier).
"""

from app.models.enums import ActivityLevel, FitnessGoal, Gender, WorkoutExperience
from app.models.profile import Profile
from app.services.metrics_service import bmi_category, calculate_bmi, calculate_daily_calories


def test_calculate_bmi_matches_the_standard_formula() -> None:
    # 70kg at 175cm -> 70 / 1.75^2 = 22.857... -> rounded to 22.9
    assert calculate_bmi(weight_kg=70, height_cm=175) == 22.9


def test_bmi_category_boundaries() -> None:
    assert bmi_category(18.4) == "underweight"
    assert bmi_category(18.5) == "normal"
    assert bmi_category(24.9) == "normal"
    assert bmi_category(25.0) == "overweight"
    assert bmi_category(29.9) == "overweight"
    assert bmi_category(30.0) == "obese"


def _make_profile(**overrides: object) -> Profile:
    defaults: dict[str, object] = dict(
        name="Test User",
        age=30,
        gender=Gender.male,
        height_cm=180.0,
        weight_kg=80.0,
        fitness_goal=FitnessGoal.maintenance,
        activity_level=ActivityLevel.sedentary,
        workout_experience=WorkoutExperience.beginner,
        equipment_available=["none"],
        diet_preference="vegetarian",
    )
    defaults.update(overrides)
    return Profile(**defaults)  # type: ignore[arg-type]


def test_daily_calories_for_a_sedentary_man() -> None:
    # BMR = 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
    # TDEE = 1780 * 1.2 (sedentary) = 2136
    profile = _make_profile()
    assert calculate_daily_calories(profile) == 2136


def test_daily_calories_for_a_very_active_woman() -> None:
    # BMR = 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
    # TDEE = 1345.25 * 1.725 (very_active) = 2320.56... -> rounds to 2321
    profile = _make_profile(
        gender=Gender.female,
        weight_kg=60.0,
        height_cm=165.0,
        age=25,
        activity_level=ActivityLevel.very_active,
    )
    assert calculate_daily_calories(profile) == 2321


def test_daily_calories_for_other_gender_averages_the_offsets() -> None:
    # base = 10*80 + 6.25*180 - 5*30 = 1775
    # offset = (5 + -161) / 2 = -78 -> BMR = 1775 - 78 = 1697
    # TDEE = 1697 * 1.2 = 2036.4 -> rounds to 2036
    profile = _make_profile(gender=Gender.other)
    assert calculate_daily_calories(profile) == 2036
