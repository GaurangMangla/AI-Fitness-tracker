# Athlyt — Database Schema

SQLite in development, PostgreSQL-compatible by design. See `docs/ARCHITECTURE.md` for the portability rationale.

All tables share three base columns from `UUIDPrimaryKeyMixin` + `TimestampMixin`:

| Column | Type | Notes |
|---|---|---|
| `id` | `VARCHAR(36)` | UUID4, application-generated |
| `created_at` | `DATETIME` | Set at insert time |
| `updated_at` | `DATETIME` | Set at insert time; update-trigger pending Alembic |

---

## `users`

| Column | Type | Constraints |
|---|---|---|
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL |
| `password_hash` | `VARCHAR(255)` | NOT NULL — bcrypt hash |

---

## `profiles`

One-to-one with `users`.

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(36)` | FK → users.id, UNIQUE |
| `name` | `VARCHAR(100)` | |
| `age` | `INTEGER` | |
| `gender` | `VARCHAR(6)` | Enum: male/female/other |
| `height_cm` | `FLOAT` | |
| `weight_kg` | `FLOAT` | |
| `fitness_goal` | `VARCHAR(15)` | Enum: muscle_gain/weight_loss/maintenance/general_fitness |
| `activity_level` | `VARCHAR(17)` | Enum: sedentary/lightly_active/moderately_active/very_active/extremely_active |
| `workout_experience` | `VARCHAR(12)` | Enum: beginner/intermediate/advanced |
| `equipment_available` | `JSON` | Array of Equipment enum values |
| `diet_preference` | `VARCHAR(14)` | Enum: non_vegetarian/vegetarian/vegan |

---

## `exercises` (seed data — not user-owned)

| Column | Type | Notes |
|---|---|---|
| `name` | `VARCHAR(150)` | |
| `muscle_group` | `VARCHAR(9)` | Enum: chest/back/shoulders/legs/arms/core/cardio |
| `equipment` | `VARCHAR(16)` | Enum: bodyweight/dumbbells/barbell/cables/... |
| `difficulty` | `VARCHAR(12)` | Enum: beginner/intermediate/advanced |
| `instructions` | `TEXT` | |
| `exercise_type` | `VARCHAR(8)` | Enum: strength/cardio/mobility |
| `default_sets` | `INTEGER` | |
| `default_reps` | `VARCHAR(20)` | String to support ranges like "8-12" |
| `rest_seconds` | `INTEGER` | |
| `calories_per_set` | `FLOAT` | NULLABLE |
| `is_compound` | `BOOLEAN` | |

---

## `workout_plans`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(36)` | FK → users.id |
| `title` | `VARCHAR(150)` | |
| `goal` | `VARCHAR(15)` | Mirrors profile.fitness_goal |
| `experience` | `VARCHAR(12)` | Mirrors profile.workout_experience |
| `workout_days` | `INTEGER` | 1–7 |
| `active` | `BOOLEAN` | Only one active plan per user |

---

## `workout_days`

| Column | Type | Notes |
|---|---|---|
| `workout_plan_id` | `VARCHAR(36)` | FK → workout_plans.id, CASCADE DELETE |
| `day_number` | `INTEGER` | 1-indexed within the plan |
| `day_name` | `VARCHAR(100)` | e.g. "Day 1 — Push" |
| `focus_area` | `VARCHAR(100)` | e.g. "Chest, Shoulders & Triceps" |

---

## `workout_exercises`

Join table between `workout_days` and `exercises`, with plan-specific overrides.

| Column | Type | Notes |
|---|---|---|
| `workout_day_id` | `VARCHAR(36)` | FK → workout_days.id, CASCADE DELETE |
| `exercise_id` | `VARCHAR(36)` | FK → exercises.id (no cascade — exercises are shared) |
| `sets` | `INTEGER` | Overrides exercise.default_sets |
| `reps` | `VARCHAR(20)` | Overrides exercise.default_reps |
| `rest_seconds` | `INTEGER` | |
| `order_index` | `INTEGER` | Display order within the day |

---

## `workout_sessions`

One attempt at a `workout_day`, on a specific occasion.

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(36)` | FK → users.id, CASCADE DELETE |
| `workout_plan_id` | `VARCHAR(36)` | FK → workout_plans.id, CASCADE DELETE; denormalized for history resilience |
| `workout_day_id` | `VARCHAR(36)` | FK → workout_days.id, CASCADE DELETE |
| `status` | `VARCHAR(9)` | Enum: active/paused/completed |
| `started_at` | `DATETIME` | |
| `completed_at` | `DATETIME` | NULLABLE |
| `total_duration_minutes` | `INTEGER` | NULLABLE until finished |
| `calories_burned_estimate` | `FLOAT` | NULLABLE until finished; MET × weight × hours |
| `accumulated_active_seconds` | `INTEGER` | Excludes paused time |
| `last_resumed_at` | `DATETIME` | For computing the current active slice |

---

## `exercise_completions`

One row per (session, workout_exercise) pair, created lazily on first interaction.

| Column | Type | Notes |
|---|---|---|
| `workout_session_id` | `VARCHAR(36)` | FK → workout_sessions.id, CASCADE DELETE |
| `workout_exercise_id` | `VARCHAR(36)` | FK → workout_exercises.id (no cascade) |
| `completed_sets` | `INTEGER` | |
| `completed_reps` | `VARCHAR(20)` | NULLABLE |
| `completed` | `BOOLEAN` | |
| `skipped` | `BOOLEAN` | |
| `notes` | `TEXT` | NULLABLE |

---

## `progress_logs`

Daily snapshot. Upserted (not appended) per user per date.

| Column | Type |
|---|---|
| `user_id` | `VARCHAR(36)` FK → users.id, CASCADE |
| `log_date` | `VARCHAR(10)` ISO date YYYY-MM-DD |
| `weight_kg` | `FLOAT` NULLABLE |
| `body_fat_pct` | `FLOAT` NULLABLE |
| `sleep_hours` | `FLOAT` NULLABLE |
| `notes` | `TEXT` NULLABLE |

---

## `body_measurements`

Less-frequent circumference snapshots. Upserted per user per date.

| Column | Type |
|---|---|
| `user_id` | `VARCHAR(36)` FK → users.id, CASCADE |
| `log_date` | `VARCHAR(10)` |
| `chest_cm` | `FLOAT` NULLABLE |
| `waist_cm` | `FLOAT` NULLABLE |
| `hips_cm` | `FLOAT` NULLABLE |
| `left_arm_cm` | `FLOAT` NULLABLE |
| `right_arm_cm` | `FLOAT` NULLABLE |
| `left_thigh_cm` | `FLOAT` NULLABLE |
| `right_thigh_cm` | `FLOAT` NULLABLE |

---

## `nutrition_plans`

| Column | Type |
|---|---|
| `user_id` | `VARCHAR(36)` FK → users.id, CASCADE |
| `active` | `BOOLEAN` |
| `diet_type` | `VARCHAR(14)` Enum: non_vegetarian/vegetarian/vegan |
| `target_calories` | `INTEGER` |
| `target_protein_g` | `FLOAT` |
| `target_carbs_g` | `FLOAT` |
| `target_fat_g` | `FLOAT` |
| `target_water_ml` | `INTEGER` |

---

## `meals`

| Column | Type |
|---|---|
| `nutrition_plan_id` | `VARCHAR(36)` FK → nutrition_plans.id, CASCADE |
| `meal_type` | `VARCHAR(9)` Enum: breakfast/lunch/dinner/snack |
| `name` | `VARCHAR(200)` |
| `description` | `TEXT` NULLABLE |
| `calories` | `INTEGER` |
| `protein_g` | `FLOAT` |
| `carbs_g` | `FLOAT` |
| `fat_g` | `FLOAT` |
| `fiber_g` | `FLOAT` |

---

## `nutrition_logs`

Daily actual intake. Upserted per user per date.

| Column | Type |
|---|---|
| `user_id` | `VARCHAR(36)` FK → users.id, CASCADE |
| `log_date` | `VARCHAR(10)` |
| `calories_consumed` | `INTEGER` |
| `protein_g` | `FLOAT` |
| `carbs_g` | `FLOAT` |
| `fat_g` | `FLOAT` |
| `water_ml` | `INTEGER` |
| `notes` | `TEXT` NULLABLE |

---

## Indexes

Every FK column is indexed. Additional indexes:
- `users.email` — UNIQUE (covers login lookups)
- `progress_logs.(user_id, log_date)` — compound covered by individual indexes; date range queries use `log_date DESC`
- `nutrition_logs.(user_id, log_date)` — same
- `exercises.(muscle_group, equipment, difficulty)` — individual indexes for filter combinations
- `workout_sessions.(user_id, status)` — active-session lookup
