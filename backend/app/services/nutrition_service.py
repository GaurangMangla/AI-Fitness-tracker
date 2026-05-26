"""NutritionService — generates meal plans and manages daily nutrition logs.

Plan generation is rule-based (not ML): daily calorie target comes from
`metrics_service.calculate_daily_calories`, macros are split using
well-established sports-nutrition guidelines, and meals are chosen from
a small curated library keyed on diet preference.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import DietPreference, MealType
from app.models.nutrition import NutritionLog, NutritionPlan
from app.models.profile import Profile
from app.repositories import nutrition_repository
from app.services.metrics_service import calculate_daily_calories

# ---------------------------------------------------------------------------
# Meal template library — curated for each diet type.
# Each entry: (meal_type, name, description, cal_pct, protein_g, carbs_g, fat_g, fiber_g)
# cal_pct = fraction of daily calories (used to compute actual calories at generation time)
# ---------------------------------------------------------------------------
_MEAL_TEMPLATES: dict[DietPreference, list[dict]] = {
    DietPreference.non_vegetarian: [
        {
            "meal_type": MealType.breakfast,
            "name": "Egg white omelette with whole grain toast",
            "description": "3 egg whites, 1 whole egg, 2 slices whole grain toast, spinach",
            "cal_pct": 0.25,
            "protein_g": 28,
            "carbs_g": 32,
            "fat_g": 8,
            "fiber_g": 4,
        },
        {
            "meal_type": MealType.lunch,
            "name": "Grilled chicken rice bowl",
            "description": "150g chicken breast, 1 cup brown rice, steamed broccoli, olive oil",
            "cal_pct": 0.35,
            "protein_g": 45,
            "carbs_g": 55,
            "fat_g": 10,
            "fiber_g": 6,
        },
        {
            "meal_type": MealType.snack,
            "name": "Greek yogurt with almonds",
            "description": "200g low-fat Greek yogurt, 20g almonds",
            "cal_pct": 0.10,
            "protein_g": 18,
            "carbs_g": 14,
            "fat_g": 9,
            "fiber_g": 2,
        },
        {
            "meal_type": MealType.dinner,
            "name": "Baked salmon with sweet potato",
            "description": "180g salmon fillet, 1 medium sweet potato, asparagus",
            "cal_pct": 0.30,
            "protein_g": 40,
            "carbs_g": 38,
            "fat_g": 14,
            "fiber_g": 5,
        },
    ],
    DietPreference.vegetarian: [
        {
            "meal_type": MealType.breakfast,
            "name": "Overnight oats with berries",
            "description": "80g rolled oats, 250ml milk, mixed berries, honey, chia seeds",
            "cal_pct": 0.25,
            "protein_g": 16,
            "carbs_g": 55,
            "fat_g": 8,
            "fiber_g": 7,
        },
        {
            "meal_type": MealType.lunch,
            "name": "Paneer and chickpea curry with rice",
            "description": "100g paneer, 150g chickpeas, 1 cup basmati rice, Indian spices",
            "cal_pct": 0.35,
            "protein_g": 28,
            "carbs_g": 65,
            "fat_g": 14,
            "fiber_g": 8,
        },
        {
            "meal_type": MealType.snack,
            "name": "Cottage cheese with fruit",
            "description": "200g low-fat cottage cheese, seasonal fruit, handful of walnuts",
            "cal_pct": 0.10,
            "protein_g": 20,
            "carbs_g": 18,
            "fat_g": 6,
            "fiber_g": 2,
        },
        {
            "meal_type": MealType.dinner,
            "name": "Lentil soup with whole grain roti",
            "description": "250ml dal, 2 whole wheat rotis, cucumber raita",
            "cal_pct": 0.30,
            "protein_g": 22,
            "carbs_g": 58,
            "fat_g": 8,
            "fiber_g": 10,
        },
    ],
    DietPreference.vegan: [
        {
            "meal_type": MealType.breakfast,
            "name": "Tofu scramble with whole grain toast",
            "description": "150g firm tofu, nutritional yeast, turmeric, 2 slices toast, avocado",
            "cal_pct": 0.25,
            "protein_g": 20,
            "carbs_g": 35,
            "fat_g": 12,
            "fiber_g": 6,
        },
        {
            "meal_type": MealType.lunch,
            "name": "Tempeh Buddha bowl",
            "description": "150g tempeh, quinoa, roasted vegetables, tahini dressing",
            "cal_pct": 0.35,
            "protein_g": 30,
            "carbs_g": 52,
            "fat_g": 14,
            "fiber_g": 9,
        },
        {
            "meal_type": MealType.snack,
            "name": "Peanut butter banana smoothie",
            "description": "1 banana, 2 tbsp peanut butter, plant milk, protein powder",
            "cal_pct": 0.10,
            "protein_g": 16,
            "carbs_g": 30,
            "fat_g": 8,
            "fiber_g": 3,
        },
        {
            "meal_type": MealType.dinner,
            "name": "Black bean tacos with guacamole",
            "description": "2 corn tortillas, 200g black beans, guacamole, salsa, lime",
            "cal_pct": 0.30,
            "protein_g": 18,
            "carbs_g": 60,
            "fat_g": 10,
            "fiber_g": 12,
        },
    ],
}

# Indian meal variant — swapped in when diet_preference is non-vegetarian but
# region signals Indian food preferences. Kept as additive option for now.
_INDIAN_NON_VEG_MEALS = [
    {
        "meal_type": MealType.breakfast,
        "name": "Masala omelette with multigrain paratha",
        "description": "3 eggs, onion, tomato, green chilli, 2 multigrain parathas",
        "cal_pct": 0.25,
        "protein_g": 26,
        "carbs_g": 38,
        "fat_g": 12,
        "fiber_g": 4,
    },
    {
        "meal_type": MealType.lunch,
        "name": "Chicken dal with brown rice",
        "description": "150g chicken, 200ml toor dal, 1 cup brown rice, salad",
        "cal_pct": 0.35,
        "protein_g": 48,
        "carbs_g": 58,
        "fat_g": 10,
        "fiber_g": 7,
    },
    {
        "meal_type": MealType.snack,
        "name": "Roasted makhana with chai",
        "description": "30g roasted fox nuts, 1 cup low-fat milk tea",
        "cal_pct": 0.10,
        "protein_g": 6,
        "carbs_g": 22,
        "fat_g": 2,
        "fiber_g": 1,
    },
    {
        "meal_type": MealType.dinner,
        "name": "Grilled fish with vegetable sabzi and roti",
        "description": "200g fish tikka, mixed vegetable sabzi, 2 whole wheat rotis",
        "cal_pct": 0.30,
        "protein_g": 42,
        "carbs_g": 40,
        "fat_g": 12,
        "fiber_g": 6,
    },
]


class NutritionService:
    # ── Plan generation ─────────────────────────────────────────────────────

    def generate_plan(self, db: Session, user_id: str, profile: Profile) -> NutritionPlan:
        """Generate and persist a rule-based meal plan from the user's profile.
        Deactivates any existing active plan first (same pattern as WorkoutPlannerService)."""
        daily_cals = calculate_daily_calories(profile)
        protein_g, carbs_g, fat_g = self._split_macros(daily_cals, profile.fitness_goal)

        nutrition_repository.deactivate_all(db, user_id)

        plan = nutrition_repository.create(
            db,
            {
                "user_id": user_id,
                "active": True,
                "diet_type": profile.diet_preference,
                "target_calories": daily_cals,
                "target_protein_g": protein_g,
                "target_carbs_g": carbs_g,
                "target_fat_g": fat_g,
                "target_water_ml": 2500,
            },
        )

        templates = _MEAL_TEMPLATES.get(
            profile.diet_preference,
            _MEAL_TEMPLATES[DietPreference.non_vegetarian],
        )
        for t in templates:
            cal = round(daily_cals * t["cal_pct"])
            nutrition_repository.create_meal(
                db,
                {
                    "nutrition_plan_id": plan.id,
                    "meal_type": t["meal_type"],
                    "name": t["name"],
                    "description": t.get("description"),
                    "calories": cal,
                    "protein_g": t["protein_g"],
                    "carbs_g": t["carbs_g"],
                    "fat_g": t["fat_g"],
                    "fiber_g": t.get("fiber_g", 0),
                },
            )

        return nutrition_repository.get_with_meals(db, plan.id)  # type: ignore[return-value]

    def get_current_plan(self, db: Session, user_id: str) -> NutritionPlan | None:
        return nutrition_repository.get_active_by_user(db, user_id)

    # ── Nutrition logs ──────────────────────────────────────────────────────

    def log_nutrition(
        self,
        db: Session,
        user_id: str,
        log_date: str | None,
        calories_consumed: int,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        water_ml: int = 0,
        notes: str | None = None,
    ) -> NutritionLog:
        date_str = log_date or datetime.now(UTC).date().isoformat()
        return nutrition_repository.upsert_log(
            db,
            user_id=user_id,
            log_date=date_str,
            fields={
                "calories_consumed": calories_consumed,
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
                "water_ml": water_ml,
                "notes": notes,
            },
        )

    def get_logs(self, db: Session, user_id: str, limit: int = 30) -> list[NutritionLog]:
        return nutrition_repository.list_logs_by_user(db, user_id, limit=limit)

    def get_today_log(self, db: Session, user_id: str) -> NutritionLog | None:
        today = datetime.now(UTC).date().isoformat()
        return nutrition_repository.get_log_by_user_and_date(db, user_id, today)

    def get_weekly_summary(self, db: Session, user_id: str) -> dict:
        logs = nutrition_repository.list_logs_by_user(db, user_id, limit=7)
        if not logs:
            return {
                "avg_calories": 0,
                "avg_protein_g": 0,
                "avg_carbs_g": 0,
                "avg_fat_g": 0,
                "days_logged": 0,
            }
        n = len(logs)
        return {
            "avg_calories": round(sum(lg.calories_consumed for lg in logs) / n),
            "avg_protein_g": round(sum(lg.protein_g for lg in logs) / n, 1),
            "avg_carbs_g": round(sum(lg.carbs_g for lg in logs) / n, 1),
            "avg_fat_g": round(sum(lg.fat_g for lg in logs) / n, 1),
            "days_logged": n,
        }

    # ── Macro splitting ─────────────────────────────────────────────────────

    @staticmethod
    def _split_macros(calories: int, goal: str) -> tuple[float, float, float]:
        """Sports-nutrition macro splits by goal (protein/carbs/fat %).
        Sources: NSCA, ACSM general guidelines."""
        splits = {
            "muscle_gain": (0.30, 0.45, 0.25),
            "weight_loss": (0.35, 0.40, 0.25),
            "maintenance": (0.25, 0.50, 0.25),
            "general_fitness": (0.25, 0.50, 0.25),
        }
        p_pct, c_pct, f_pct = splits.get(goal, (0.25, 0.50, 0.25))
        protein_g = round(calories * p_pct / 4, 1)  # 4 kcal/g
        carbs_g = round(calories * c_pct / 4, 1)
        fat_g = round(calories * f_pct / 9, 1)  # 9 kcal/g
        return protein_g, carbs_g, fat_g
