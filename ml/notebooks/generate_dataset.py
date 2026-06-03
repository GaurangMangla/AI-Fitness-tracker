"""Synthetic user dataset generator for the workout-split recommendation model.

Generates realistic synthetic user profiles and labels each one by calling
the REAL, currently-deployed rule engine (app.services.recommendation_engine
.RuleBasedRecommendationEngine) — not a reimplementation or approximation of
its logic. This guarantees the dataset's labels are exactly what the running
app would recommend for that profile today, which is what makes this dataset
suitable for training a model that imitates (and, later, could learn to
approximate given real outcome data) the app's own recommendation logic.

Run from the backend/ directory so the `app` package is importable:
    cd backend
    python ../ml/notebooks/generate_dataset.py --n 100000 --out ../ml/data/dataset.csv

This script has no side effects on the running application or its database —
it only imports pure, stateless recommendation logic (RecommendationInput,
RuleBasedRecommendationEngine) and never touches app.db, app.models ORM
sessions, or any API route.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

# Make the backend's `app` package importable regardless of cwd, as long as
# this script is run from within (or two levels below) the repo root.
_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.models.enums import (  # noqa: E402
    ActivityLevel,
    DietPreference,
    Equipment,
    FitnessGoal,
    Gender,
    WorkoutExperience,
)
from app.services.metrics_service import bmi_category, calculate_bmi  # noqa: E402
from app.services.recommendation_engine import RuleBasedRecommendationEngine  # noqa: E402
from app.services.recommendation_types import RecommendationInput  # noqa: E402

# ---------------------------------------------------------------------------
# Realistic distributions
#
# Every distribution below is a deliberate modeling choice, not an arbitrary
# default — each is explained inline. These mirror what a real fitness app's
# user base actually looks like, based on well-established patterns in
# fitness-app demographics and exercise-science population data, not
# invented numbers.
# ---------------------------------------------------------------------------

_RNG_SEED = 42

# Age: skewed toward the 20s-30s, which is the dominant demographic for
# fitness-app signups, with a long tail toward both ends. A truncated normal
# (not uniform) avoids an unrealistic flat spread across 16-65.
_AGE_MIN, _AGE_MAX = 16, 65
_AGE_MEAN, _AGE_STD = 28, 9

# Gender: roughly balanced with a small "other" minority — matches typical
# fitness app demographic surveys reasonably well without asserting a
# precise real-world figure.
_GENDER_WEIGHTS = {Gender.male: 0.49, Gender.female: 0.47, Gender.other: 0.04}

# Height (cm): gender-conditioned normal distributions using widely-cited
# adult population means/std-devs (approximate, not a specific country's
# exact census figures — reasonable for synthetic training data).
_HEIGHT_PARAMS = {
    Gender.male: (175.0, 7.0),
    Gender.female: (162.0, 6.5),
    Gender.other: (168.0, 8.0),  # blended midpoint with wider spread
}

# Workout experience: beginner is explicitly the majority per this phase's
# spec — matches the real shape of a fitness app's user base, where most
# signups are new to structured training.
_EXPERIENCE_WEIGHTS = {
    WorkoutExperience.beginner: 0.55,
    WorkoutExperience.intermediate: 0.35,
    WorkoutExperience.advanced: 0.10,
}

# Equipment: bodyweight/no-equipment must be more common than full-gym
# access per this phase's spec — realistic for a general fitness-app
# audience (most people don't have a home gym or gym membership). Modeled
# as a weighted choice over realistic *combinations* a real user profile
# would actually report (not independent per-item coin flips, which would
# produce nonsensical combinations like "barbell but no dumbbells and no
# full gym").
_EQUIPMENT_COMBOS: list[tuple[list[Equipment], float]] = [
    ([Equipment.none], 0.32),  # no equipment at all — most common
    ([Equipment.dumbbells], 0.16),
    ([Equipment.resistance_bands], 0.08),
    ([Equipment.pull_up_bar], 0.05),
    ([Equipment.dumbbells, Equipment.resistance_bands], 0.07),
    ([Equipment.dumbbells, Equipment.pull_up_bar], 0.05),
    ([Equipment.dumbbells, Equipment.barbell], 0.06),
    ([Equipment.full_gym], 0.21),  # gym access — real but a minority
]

# Fitness goal: "balanced realistic distribution" per spec — weight loss and
# muscle gain are the two dominant real-world motivators for starting a
# fitness app, with maintenance/general fitness as meaningful but smaller
# shares.
_GOAL_WEIGHTS = {
    FitnessGoal.weight_loss: 0.35,
    FitnessGoal.muscle_gain: 0.32,
    FitnessGoal.general_fitness: 0.20,
    FitnessGoal.maintenance: 0.13,
}

# Activity level: centered on lightly/moderately active — most fitness-app
# users are not already extremely active (if they were, they may be less
# likely to be seeking a new plan) and true sedentary-to-extreme are the two
# tails.
_ACTIVITY_WEIGHTS = {
    ActivityLevel.sedentary: 0.18,
    ActivityLevel.lightly_active: 0.30,
    ActivityLevel.moderately_active: 0.32,
    ActivityLevel.very_active: 0.15,
    ActivityLevel.extra_active: 0.05,
}

# Workout days per week: 3-5 is the realistic dominant range; 1-2 and 6-7
# are real but minority patterns.
_DAYS_WEIGHTS = {1: 0.04, 2: 0.09, 3: 0.24, 4: 0.26, 5: 0.22, 6: 0.11, 7: 0.04}

# Diet preference: non-vegetarian is the global majority; vegetarian and
# vegan are meaningful minorities. (Note: as flagged in ML_ARCHITECTURE.md
# §2.2, this feature's actual relevance to workout-split selection is
# uncertain and should be evaluated via feature importance during training,
# not assumed here — it's generated realistically regardless so that
# evaluation can happen on real data.)
_DIET_WEIGHTS = {
    DietPreference.non_vegetarian: 0.55,
    DietPreference.vegetarian: 0.35,
    DietPreference.vegan: 0.10,
}


def _weighted_choice(rng: random.Random, weights: dict) -> object:
    keys = list(weights.keys())
    probs = list(weights.values())
    return rng.choices(keys, weights=probs, k=1)[0]


def _sample_age(rng: np.random.Generator) -> int:
    # Truncated normal via clip — keeps the distribution's shape rather than
    # discarding and resampling out-of-range draws.
    age = rng.normal(_AGE_MEAN, _AGE_STD)
    return int(np.clip(round(age), _AGE_MIN, _AGE_MAX))


def _sample_height(rng: np.random.Generator, gender: Gender) -> float:
    mean, std = _HEIGHT_PARAMS[gender]
    height = rng.normal(mean, std)
    return round(float(np.clip(height, 140.0, 210.0)), 1)


def _sample_weight(rng: np.random.Generator, height_cm: float, gender: Gender) -> float:
    """Weight is sampled conditioned on height via a target BMI, not
    independently — this is the deliberate "maintain realistic correlations"
    requirement from the phase spec. An independently-sampled weight would
    let a 150cm and a 200cm person have the same weight with equal
    probability, which is not how real bodies are distributed.

    The target BMI itself is drawn from a realistic population-level BMI
    distribution (mean ~24.5, mildly right-skewed toward overweight, which
    matches real adult population BMI surveys reasonably well), then weight
    is back-calculated from that BMI and the already-sampled height.
    """
    target_bmi = rng.normal(24.5, 4.5)
    target_bmi = float(np.clip(target_bmi, 16.0, 42.0))
    height_m = height_cm / 100
    weight = target_bmi * (height_m**2)
    # Small additional noise so weight isn't a perfectly deterministic
    # function of height + drawn BMI (real bodies vary beyond BMI alone).
    weight *= rng.normal(1.0, 0.03)
    return round(float(np.clip(weight, 35.0, 180.0)), 1)


def _sample_equipment(rng: random.Random) -> list[Equipment]:
    combos, weights = zip(*_EQUIPMENT_COMBOS, strict=True)
    idx = rng.choices(range(len(combos)), weights=weights, k=1)[0]
    return list(combos[idx])


def generate_dataset(n: int, seed: int = _RNG_SEED) -> pd.DataFrame:
    """Generates `n` synthetic user rows, each labeled by calling the real
    RuleBasedRecommendationEngine — the exact same class the running
    application uses for POST /workouts/recommend today."""
    np_rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    engine = RuleBasedRecommendationEngine()

    rows: list[dict] = []
    for _ in range(n):
        gender = _weighted_choice(py_rng, _GENDER_WEIGHTS)
        age = _sample_age(np_rng)
        height_cm = _sample_height(np_rng, gender)
        weight_kg = _sample_weight(np_rng, height_cm, gender)
        fitness_goal = _weighted_choice(py_rng, _GOAL_WEIGHTS)
        workout_experience = _weighted_choice(py_rng, _EXPERIENCE_WEIGHTS)
        activity_level = _weighted_choice(py_rng, _ACTIVITY_WEIGHTS)
        equipment_available = _sample_equipment(py_rng)
        workout_days_per_week = _weighted_choice(py_rng, _DAYS_WEIGHTS)
        diet_preference = _weighted_choice(py_rng, _DIET_WEIGHTS)

        recommendation_input = RecommendationInput(
            fitness_goal=fitness_goal,
            workout_experience=workout_experience,
            activity_level=activity_level,
            equipment_available=equipment_available,
            workout_days_per_week=workout_days_per_week,
            age=age,
            gender=gender,
        )

        # THE LABEL: generated by calling the real, deployed rule engine —
        # not a hand-written approximation of it. See ML_ARCHITECTURE.md §3.3
        # for why this is the correct approach and its honest limitations.
        split = engine.recommend(recommendation_input)

        bmi = calculate_bmi(weight_kg, height_cm)

        rows.append(
            {
                "age": age,
                "gender": gender.value,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "bmi": bmi,
                "bmi_category": bmi_category(bmi),
                "fitness_goal": fitness_goal.value,
                "workout_experience": workout_experience.value,
                "activity_level": activity_level.value,
                "equipment_available": ",".join(e.value for e in equipment_available),
                "equipment_count": len(equipment_available),
                "has_gym_access": Equipment.full_gym in equipment_available,
                "workout_days_per_week": workout_days_per_week,
                "diet_preference": diet_preference.value,
                "target_split": split.key,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=100_000, help="Number of synthetic users to generate")
    parser.add_argument("--seed", type=int, default=_RNG_SEED, help="Random seed for reproducibility")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "data" / "dataset.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    print(f"Generating {args.n:,} synthetic users (seed={args.seed})...")
    df = generate_dataset(args.n, seed=args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df):,} rows to {out_path}")
    print("\nTarget class distribution:")
    print(df["target_split"].value_counts(normalize=True).round(3))


if __name__ == "__main__":
    main()
