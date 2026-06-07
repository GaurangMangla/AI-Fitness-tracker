"""Builds the exact feature DataFrame the trained preprocessor expects.

This must match `ml/notebooks/train_model.ipynb`'s feature engineering
exactly — see `ml/ML_TRAINING.md` §3 for the full writeup of what's encoded
and why. The column names and order below are taken directly from
`ml/models/metadata.json`'s `feature_columns` list, not re-derived from
memory, specifically to avoid silent drift between what was trained and
what's served.

Requires `recommendation_input.diet_preference`, `.height_cm`, and
`.weight_kg` to be populated (the ML-only fields added to `RecommendationInput`
in Phase 2.3 — see `recommendation_types.py`). `WorkoutRecommendationService`
always populates them from the user's `Profile`, so in practice they're only
ever `None` if this function is called directly with a hand-built
`RecommendationInput` that omits them — raises `ValueError` in that case
rather than silently building a nonsense feature row.
"""

import pandas as pd

from app.models.enums import Equipment
from app.services.metrics_service import bmi_category, calculate_bmi
from app.services.recommendation_types import RecommendationInput

# Every equipment value that got its own `equip_<value>` one-hot column
# during training (see ml/notebooks/generate_dataset.py's equipment
# multi-hot encoding). This is exactly `list(Equipment)` today — asserted
# once at import time so a future enum change that adds/removes a value
# without retraining is caught immediately at startup, not silently
# mispredicted at request time.
_TRAINED_EQUIPMENT_VALUES = [
    "barbell",
    "dumbbells",
    "full_gym",
    "none",
    "pull_up_bar",
    "resistance_bands",
]

_actual_equipment_values = sorted(e.value for e in Equipment)
if _actual_equipment_values != sorted(_TRAINED_EQUIPMENT_VALUES):
    raise AssertionError(
        "Equipment enum has changed since the model was trained "
        f"(trained on {sorted(_TRAINED_EQUIPMENT_VALUES)}, "
        f"enum now has {_actual_equipment_values}) — retrain the model "
        "before using MLRecommendationService. See ml/ML_TRAINING.md."
    )

# Exact column order from ml/models/metadata.json's "feature_columns" list.
_FEATURE_COLUMNS = [
    "gender",
    "fitness_goal",
    "activity_level",
    "workout_experience",
    "diet_preference",
    "bmi_category",
    "age",
    "height_cm",
    "weight_kg",
    "bmi",
    "workout_days_per_week",
    "equipment_count",
    "has_gym_access",
    "equip_barbell",
    "equip_dumbbells",
    "equip_full_gym",
    "equip_none",
    "equip_pull_up_bar",
    "equip_resistance_bands",
]


def build_feature_row(recommendation_input: RecommendationInput) -> pd.DataFrame:
    """Builds a single-row DataFrame matching the training feature schema
    exactly — same column names, same order, same derivation logic as
    `ml/notebooks/generate_dataset.py`.
    """
    if (
        recommendation_input.diet_preference is None
        or recommendation_input.height_cm is None
        or recommendation_input.weight_kg is None
    ):
        raise ValueError(
            "RecommendationInput is missing diet_preference/height_cm/weight_kg — "
            "required for ML feature building. WorkoutRecommendationService "
            "always populates these from Profile; this only happens if "
            "build_feature_row was called with a hand-built input that omits them."
        )

    equipment = recommendation_input.equipment_available
    bmi = calculate_bmi(recommendation_input.weight_kg, recommendation_input.height_cm)

    row = {
        "gender": recommendation_input.gender.value,
        "fitness_goal": recommendation_input.fitness_goal.value,
        "activity_level": recommendation_input.activity_level.value,
        "workout_experience": recommendation_input.workout_experience.value,
        "diet_preference": recommendation_input.diet_preference.value,
        "bmi_category": bmi_category(bmi),
        "age": recommendation_input.age,
        "height_cm": recommendation_input.height_cm,
        "weight_kg": recommendation_input.weight_kg,
        "bmi": bmi,
        "workout_days_per_week": recommendation_input.workout_days_per_week,
        "equipment_count": len(equipment),
        "has_gym_access": Equipment.full_gym in equipment,
        "equip_barbell": Equipment.barbell in equipment,
        "equip_dumbbells": Equipment.dumbbells in equipment,
        "equip_full_gym": Equipment.full_gym in equipment,
        "equip_none": Equipment.none in equipment,
        "equip_pull_up_bar": Equipment.pull_up_bar in equipment,
        "equip_resistance_bands": Equipment.resistance_bands in equipment,
    }

    return pd.DataFrame([row], columns=_FEATURE_COLUMNS)
