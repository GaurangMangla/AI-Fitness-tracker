# Athlyt — API Reference

Base URL (prod): `https://athlyt-backend.vercel.app/api/v1`
Base URL (dev): `http://localhost:8000/api/v1`

All responses follow one of two shapes:
- **Success**: the response body directly (no envelope wrapper)
- **Error**: `{"detail": "Human-readable error message"}`

Authentication: `Authorization: Bearer <access_token>` header on all protected endpoints.

Swagger UI available at `https://athlyt-backend.vercel.app/docs` (prod) or `http://localhost:8000/docs` (dev).

---

## Auth

### `POST /auth/register`
Create a new user account.

**Request body:**
```json
{ "email": "user@example.com", "password": "SecurePass123" }
```

**Response 201:**
```json
{
  "user": { "id": "uuid", "email": "user@example.com", "profile": null, "metrics": null },
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `409` email already registered, `422` invalid email or password too long (>72 bytes)

---

### `POST /auth/login`
Authenticate and receive a JWT.

**Request body:**
```json
{ "email": "user@example.com", "password": "SecurePass123" }
```

**Response 200:** Same shape as register.

**Errors:** `401` invalid credentials

---

## Users / Profile

### `GET /users/me` 🔒
Current user with profile and computed metrics.

**Response 200:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "profile": {
    "name": "Gaurang",
    "age": 25,
    "gender": "male",
    "height_cm": 178.0,
    "weight_kg": 80.0,
    "fitness_goal": "muscle_gain",
    "activity_level": "moderately_active",
    "workout_experience": "intermediate",
    "equipment_available": ["full_gym"],
    "diet_preference": "non_vegetarian"
  },
  "metrics": { "bmi": 25.2, "bmi_category": "Normal weight", "daily_calories": 2850 }
}
```

---

### `PATCH /users/me` 🔒
Update profile. All fields required on first submission (onboarding), optional after.

**Request body:** Any subset of profile fields.

**Response 200:** Same as `GET /users/me`

---

## Exercises

### `GET /exercises` 🔒
Exercise catalog. Filterable.

**Query params:** `muscle_group`, `equipment`, `difficulty` (all optional, combinable)

**Response 200:** Array of exercise objects.

---

### `GET /exercises/{exercise_id}` 🔒
Single exercise.

**Response 200:** Exercise object. **404** if not found.

---

## Workouts

### `POST /workouts/recommend` 🔒
Stateless split recommendation based on profile + requested days.

**Request body:**
```json
{ "workout_days_per_week": 5 }
```

**Response 200:**
```json
{
  "title": "Muscle Gain Plan",
  "split_name": "Push Pull Legs",
  "workout_days": 5,
  "difficulty": "Intermediate",
  "reason": "Recommended because..."
}
```

---

### `POST /workouts/generate` 🔒
Generate and persist a complete weekly plan. Deactivates any existing active plan.

**Request body:**
```json
{ "workout_days_per_week": 5 }
```

**Response 201:** Full plan with all days and exercises.

**Errors:** `422` onboarding incomplete

---

### `GET /workouts/current` 🔒
The user's currently active workout plan.

**Response 200:** Full plan object. **404** if no active plan.

---

### `GET /workouts/today` 🔒
Today's workout day from the active plan (weekday-mapped).

**Response 200:** Workout day with exercises. **404** if no plan or rest day.

---

### `POST /workouts/start` 🔒
Start a new workout session for today's workout day.

**Response 201:** `WorkoutSession` object.

**Errors:** `404` no active plan or rest day, `409` session already active

---

### `POST /workouts/{session_id}/pause` 🔒
Pause an active session. Accumulates active seconds correctly.

**Response 200:** Updated session. **409** if already paused or completed.

---

### `POST /workouts/{session_id}/resume` 🔒
Resume a paused session.

**Response 200:** Updated session. **409** if already active or completed.

---

### `POST /workouts/{session_id}/exercise/{exercise_id}/complete` 🔒
Mark a workout exercise as completed. Creates or updates the `ExerciseCompletion` row.

**Request body (all optional):**
```json
{ "completed_sets": 3, "completed_reps": "10", "notes": "Felt strong" }
```

**Response 200:** `ExerciseCompletion` object.

**Errors:** `404` exercise not in this session, `409` session already completed

---

### `POST /workouts/{session_id}/exercise/{exercise_id}/skip` 🔒
Mark an exercise as skipped.

**Request body (all optional):**
```json
{ "notes": "Shoulder injury" }
```

**Response 200:** `ExerciseCompletion` object.

---

### `POST /workouts/{session_id}/finish` 🔒
Finish a session. Computes duration (excluding paused time) and estimates calories burned.

**Response 200:**
```json
{
  "session": { "...session fields...", "status": "completed" },
  "total_duration_minutes": 47,
  "exercises_completed": 4,
  "exercises_skipped": 1,
  "calories_burned_estimate": 312.5
}
```

**Errors:** `409` session already completed

---

### `GET /workouts/history` 🔒
All completed sessions, most recent first.

**Response 200:** Array of `WorkoutSession` objects with `exercise_completions`.

---

### `GET /workouts/history/{session_id}` 🔒
Single session detail (works for active or completed sessions owned by the user).

**Response 200:** `WorkoutSession` with `exercise_completions`. **404** if not found or wrong user.

---

## Workout Statistics

### `GET /workouts/stats/summary` 🔒
Aggregate statistics over all completed sessions.

**Response 200:**
```json
{
  "total_sessions": 12,
  "total_minutes": 540,
  "total_calories_burned": 3250.5,
  "total_exercises_completed": 68,
  "current_streak_days": 3,
  "longest_streak_days": 7,
  "sessions_last_7_days": 3,
  "sessions_last_30_days": 10,
  "avg_session_minutes": 45.0,
  "avg_calories_per_session": 270.9
}
```

---

### `GET /workouts/stats/weekly-volume?weeks=8` 🔒
Per-week session counts and minutes. `weeks` defaults to 8, max 26.

**Response 200:** Array of `{ week_start, sessions, minutes, calories }`.

---

### `GET /workouts/stats/personal-records` 🔒
Best session by duration, most calories, most exercises completed.

**Response 200:** Array of `{ type, label, value, unit, session_id, achieved_at }`.

---

### `GET /workouts/stats/heatmap?days=365` 🔒
Daily workout counts for the last N days. `days` max 365.

**Response 200:** Array of `{ date, count }` oldest first.

---

## Progress

### `POST /progress/logs` 🔒
Log weight, body fat %, and/or sleep for a date. Upserts on same date.

**Request body (all optional except at least one metric):**
```json
{
  "log_date": "2025-01-15",
  "weight_kg": 80.5,
  "body_fat_pct": 18.2,
  "sleep_hours": 7.5,
  "notes": "Feeling good"
}
```

**Response 201:** `ProgressLog` object.

---

### `GET /progress/logs?limit=90` 🔒
Progress log history, most recent first. Max 365.

**Response 200:** Array of `ProgressLog` objects.

---

### `GET /progress/summary` 🔒
Current stats and 30-day weight change.

**Response 200:**
```json
{
  "current_weight_kg": 80.5,
  "current_body_fat_pct": 18.2,
  "last_sleep_hours": 7.5,
  "weight_change_30d_kg": -1.2,
  "total_logs": 25,
  "weight_entries": 20
}
```

---

### `POST /progress/measurements` 🔒
Log body circumference measurements. Upserts on same date.

**Request body (all optional):**
```json
{
  "log_date": "2025-01-15",
  "chest_cm": 100.0,
  "waist_cm": 82.0,
  "hips_cm": 95.0,
  "left_arm_cm": 35.0,
  "right_arm_cm": 35.5,
  "left_thigh_cm": 58.0,
  "right_thigh_cm": 58.5
}
```

**Response 201:** `BodyMeasurement` object.

---

### `GET /progress/measurements?limit=30` 🔒
Measurement history, most recent first. Max 100.

**Response 200:** Array of `BodyMeasurement` objects.

---

### `GET /progress/export?format=csv|pdf` 🔒
Downloadable report combining weight/body-fat/sleep logs, body measurements, nutrition logs, and workout history (up to the last 365 days) into a single file. `format` defaults to `csv`.

**Response 200:** File download.
- `format=csv` — `Content-Type: text/csv`, one section per data type.
- `format=pdf` — `Content-Type: application/pdf`, same sections rendered as tables (via `reportlab`).

Both responses set `Content-Disposition: attachment; filename="athlyt-report-YYYY-MM-DD.<ext>"`.

**Errors:** `422` invalid `format` value

---

## Nutrition

### `POST /nutrition/plans/generate` 🔒
Generate a rule-based meal plan from the user's profile. Deactivates any existing plan.

**Request body:** None required (reads from profile).

**Response 201:** `NutritionPlan` with 4 meals (breakfast, lunch, dinner, snack).

**Errors:** `422` onboarding incomplete

---

### `GET /nutrition/plans/current` 🔒
The user's currently active nutrition plan with all meals.

**Response 200:** `NutritionPlan`. **404** if no plan generated yet.

---

### `POST /nutrition/logs` 🔒
Log daily macro intake. Upserts on same date.

**Request body:**
```json
{
  "log_date": "2025-01-15",
  "calories_consumed": 2100,
  "protein_g": 160.0,
  "carbs_g": 210.0,
  "fat_g": 70.0,
  "water_ml": 2500,
  "notes": "Cheat meal at dinner"
}
```

**Response 201:** `NutritionLog` object.

---

### `GET /nutrition/logs?limit=30` 🔒
Nutrition log history, most recent first. Max 90.

**Response 200:** Array of `NutritionLog` objects.

---

### `GET /nutrition/logs/today` 🔒
Today's nutrition log entry.

**Response 200:** `NutritionLog` or `null` if nothing logged today.

---

### `GET /nutrition/summary/weekly` 🔒
Average macros across the last 7 logged days.

**Response 200:**
```json
{
  "avg_calories": 2050,
  "avg_protein_g": 155.2,
  "avg_carbs_g": 205.8,
  "avg_fat_g": 68.1,
  "days_logged": 5
}
```

---

## Health

### `GET /health`
Liveness check. No auth required.

**Response 200:**
```json
{ "status": "ok", "version": "0.1.0", "database": "healthy" }
```

---

### `GET /health/detailed`
Extended status with environment info. No auth required.

**Response 200:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "local",
  "database": "healthy",
  "python_version": "3.12.0"
}
```

---

## Common error codes

| Code | Meaning |
|---|---|
| `400` | Bad request (malformed JSON, etc.) |
| `401` | Not authenticated or token expired |
| `404` | Resource not found |
| `409` | Conflict (duplicate, already active, already completed) |
| `422` | Validation error (missing/invalid field) |
| `500` | Unexpected server error |

All errors return: `{"detail": "Human-readable message"}`
