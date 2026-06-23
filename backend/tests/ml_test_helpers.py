"""Builds a tiny, real `RandomForestClassifier` + `ColumnTransformer` pair
for tests — same class types, same interface, same feature schema as the
real `ml/models/model.joblib`/`preprocessor.joblib`, just trained on a
handful of synthetic rows instead of 100,000.

Deliberately NOT a hand-rolled stub with a fake `.predict_proba()` method —
using the real sklearn classes means these tests exercise the actual
`ColumnTransformer.transform()` and `RandomForestClassifier.predict_proba()`
code paths `MLRecommendationService` really calls, catching integration bugs
(wrong column name, wrong dtype, wrong shape) that a hand-written stub would
silently paper over.
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder

from app.ml.feature_builder import (
    _FEATURE_COLUMNS,  # test-only introspection of the real column list
)

_CATEGORICAL_COLUMNS = [
    "gender",
    "fitness_goal",
    "activity_level",
    "workout_experience",
    "diet_preference",
    "bmi_category",
]

# A handful of synthetic training rows spanning a few of the real observed
# classes — enough for RandomForestClassifier to fit without error and
# produce genuine (if not particularly accurate) predict_proba() output.
_TRAINING_ROWS = [
    {
        "gender": "male",
        "fitness_goal": "muscle_gain",
        "activity_level": "moderately_active",
        "workout_experience": "intermediate",
        "diet_preference": "non_vegetarian",
        "bmi_category": "normal",
        "age": 28,
        "height_cm": 178.0,
        "weight_kg": 78.0,
        "bmi": 24.6,
        "workout_days_per_week": 5,
        "equipment_count": 1,
        "has_gym_access": True,
        "equip_barbell": False,
        "equip_dumbbells": False,
        "equip_full_gym": True,
        "equip_none": False,
        "equip_pull_up_bar": False,
        "equip_resistance_bands": False,
        "target": "push_pull_legs",
    },
    {
        "gender": "female",
        "fitness_goal": "weight_loss",
        "activity_level": "lightly_active",
        "workout_experience": "beginner",
        "diet_preference": "vegetarian",
        "bmi_category": "overweight",
        "age": 34,
        "height_cm": 162.0,
        "weight_kg": 70.0,
        "bmi": 26.7,
        "workout_days_per_week": 3,
        "equipment_count": 0,
        "has_gym_access": False,
        "equip_barbell": False,
        "equip_dumbbells": False,
        "equip_full_gym": False,
        "equip_none": True,
        "equip_pull_up_bar": False,
        "equip_resistance_bands": False,
        "target": "home_bodyweight",
    },
    {
        "gender": "male",
        "fitness_goal": "general_fitness",
        "activity_level": "sedentary",
        "workout_experience": "beginner",
        "diet_preference": "vegan",
        "bmi_category": "normal",
        "age": 45,
        "height_cm": 170.0,
        "weight_kg": 68.0,
        "bmi": 23.5,
        "workout_days_per_week": 4,
        "equipment_count": 1,
        "has_gym_access": False,
        "equip_barbell": False,
        "equip_dumbbells": True,
        "equip_full_gym": False,
        "equip_none": False,
        "equip_pull_up_bar": False,
        "equip_resistance_bands": False,
        "target": "upper_lower",
    },
] * 10  # repeated so RandomForestClassifier has enough rows per class to fit


def build_tiny_model_and_preprocessor() -> tuple[RandomForestClassifier, ColumnTransformer]:
    """Returns (model, preprocessor) — both real, fitted sklearn objects,
    matching the production feature schema exactly."""
    df = pd.DataFrame(_TRAINING_ROWS)
    X = df[_FEATURE_COLUMNS]
    y = df["target"]

    preprocessor = ColumnTransformer(
        transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), _CATEGORICAL_COLUMNS)],
        remainder="passthrough",
    )
    X_encoded = preprocessor.fit_transform(X)

    model = RandomForestClassifier(n_estimators=10, max_depth=5, random_state=42)
    model.fit(X_encoded, y)

    return model, preprocessor
