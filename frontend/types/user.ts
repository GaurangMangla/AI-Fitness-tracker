// Mirrors `backend/app/models/enums.py` and `backend/app/schemas/user.py`.
// No codegen in this project — these are kept in sync by hand, which is fine
// at this size (one small, slow-changing set of enums) and avoids adding a
// build step for a one-week project.

export type Gender = "male" | "female" | "other";

export type FitnessGoal =
  | "weight_loss"
  | "muscle_gain"
  | "maintenance"
  | "general_fitness";

export type ActivityLevel =
  | "sedentary"
  | "lightly_active"
  | "moderately_active"
  | "very_active"
  | "extra_active";

export type WorkoutExperience = "beginner" | "intermediate" | "advanced";

export type DietPreference = "vegetarian" | "non_vegetarian" | "vegan";

export type Equipment =
  | "none"
  | "dumbbells"
  | "barbell"
  | "resistance_bands"
  | "pull_up_bar"
  | "full_gym";

export interface ProfileResponse {
  name: string;
  age: number;
  gender: Gender;
  height_cm: number;
  weight_kg: number;
  fitness_goal: FitnessGoal;
  activity_level: ActivityLevel;
  workout_experience: WorkoutExperience;
  equipment_available: Equipment[];
  diet_preference: DietPreference;
}

export interface ProfileMetrics {
  bmi: number;
  bmi_category: "underweight" | "normal" | "overweight" | "obese";
  daily_calories: number;
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
  profile: ProfileResponse | null;
  metrics: ProfileMetrics | null;
}

export interface AuthResponse {
  user: UserResponse;
  access_token: string;
  token_type: string;
}

// --- Workouts (Milestone 2.3 backend / 2.4 frontend) -----------------------
// Mirrors `backend/app/models/enums.py` (Exercise-specific enums) and
// `backend/app/schemas/workout.py` / `recommendation.py`.

export type MuscleGroup = "chest" | "back" | "shoulders" | "legs" | "arms" | "core" | "cardio";

export type ExerciseEquipment =
  | "bodyweight"
  | "dumbbells"
  | "barbell"
  | "kettlebell"
  | "resistance_bands"
  | "machine"
  | "cable"
  | "bench"
  | "pull_up_bar";

export type ExerciseDifficulty = "beginner" | "intermediate" | "advanced";

export type ExerciseType = "strength" | "cardio" | "mobility" | "balance";

export interface ExerciseResponse {
  id: string;
  name: string;
  muscle_group: MuscleGroup;
  equipment: ExerciseEquipment;
  difficulty: ExerciseDifficulty;
  instructions: string;
  exercise_type: ExerciseType;
  default_sets: number;
  default_reps: string;
  rest_seconds: number;
  calories_per_set: number | null;
  is_compound: boolean;
  created_at: string;
}

export interface WorkoutExerciseResponse {
  id: string;
  workout_day_id: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  order_index: number;
  exercise: ExerciseResponse;
}

export interface WorkoutDayResponse {
  id: string;
  workout_plan_id: string;
  day_number: number;
  day_name: string;
  focus_area: string;
  workout_exercises: WorkoutExerciseResponse[];
}

export interface WorkoutPlanResponse {
  id: string;
  user_id: string;
  title: string;
  goal: FitnessGoal;
  experience: WorkoutExperience;
  workout_days: number;
  active: boolean;
  created_at: string;
  days: WorkoutDayResponse[];
}

// The /generate response adds computed fields on top of WorkoutPlanResponse.
/**
 * The profile inputs a recommendation was actually based on — mirrors the
 * backend's `RecommendationExplanation` (schemas/recommendation.py) exactly.
 */
export interface RecommendationExplanation {
  goal: string;
  experience: string;
  days_per_week: number;
  equipment: string;
  gender: string;
  age: number;
}

export interface GeneratedWorkoutPlanResponse extends WorkoutPlanResponse {
  split_name: string;
  difficulty: string;
  estimated_duration_minutes: number;
  // Added for the premium AI recommendation UI — see
  // backend/app/schemas/workout.py's GeneratedWorkoutPlanResponse for the
  // exact same fields on the Python side. `engine` defaults to "rule" on
  // the backend, but is always present; the others are `null` whenever
  // `engine === "rule"` (no meaningful confidence/model version for a
  // rule-based decision).
  engine: "ml" | "rule";
  confidence: number | null;
  latency_ms: number | null;
  model_version: string | null;
  explanation: RecommendationExplanation | null;
}

export interface GenerateWorkoutRequest {
  workout_days_per_week: number;
}

// --- Workout Tracking (Milestone 2.5) -----------------------------------

export type WorkoutSessionStatus = "active" | "paused" | "completed";

export interface ExerciseCompletionResponse {
  id: string;
  workout_session_id: string;
  workout_exercise_id: string;
  completed_sets: number;
  completed_reps: string | null;
  completed: boolean;
  skipped: boolean;
  notes: string | null;
}

export interface WorkoutSessionResponse {
  id: string;
  user_id: string;
  workout_plan_id: string;
  workout_day_id: string;
  status: WorkoutSessionStatus;
  started_at: string;
  completed_at: string | null;
  total_duration_minutes: number | null;
  calories_burned_estimate: number | null;
  exercise_completions: ExerciseCompletionResponse[];
  // Internal bookkeeping fields returned by the API — used by the live timer
  accumulated_active_seconds: number;
  last_resumed_at: string;
}

export interface FinishWorkoutResponse {
  session: WorkoutSessionResponse;
  total_duration_minutes: number;
  exercises_completed: number;
  exercises_skipped: number;
  calories_burned_estimate: number;
}

export interface ExerciseCompletionRequest {
  completed_sets?: number;
  completed_reps?: string;
  notes?: string;
}

// --- Workout Stats -----------------------------------------------------------

export interface WorkoutStatsSummary {
  total_sessions: number;
  total_minutes: number;
  total_calories_burned: number;
  total_exercises_completed: number;
  current_streak_days: number;
  longest_streak_days: number;
  sessions_last_7_days: number;
  sessions_last_30_days: number;
  avg_session_minutes: number;
  avg_calories_per_session: number;
}

// --- Progress ----------------------------------------------------------------

export interface ProgressLog {
  id: string;
  log_date: string;
  weight_kg: number | null;
  body_fat_pct: number | null;
  sleep_hours: number | null;
  notes: string | null;
  created_at: string;
}

export interface ProgressSummary {
  current_weight_kg: number | null;
  current_body_fat_pct: number | null;
  last_sleep_hours: number | null;
  weight_change_30d_kg: number | null;
  total_logs: number;
  weight_entries: number;
}

// --- Nutrition ----------------------------------------------------------------

export interface NutritionMeal {
  id: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  name: string;
  description: string | null;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
}

export interface NutritionPlan {
  id: string;
  diet_type: string;
  active: boolean;
  target_calories: number;
  target_protein_g: number;
  target_carbs_g: number;
  target_fat_g: number;
  target_water_ml: number;
  meals: NutritionMeal[];
  created_at: string;
}

export interface NutritionLogEntry {
  id: string;
  log_date: string;
  calories_consumed: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  water_ml: number;
  notes: string | null;
  created_at: string;
}

export interface NutritionWeeklySummary {
  avg_calories: number;
  avg_protein_g: number;
  avg_carbs_g: number;
  avg_fat_g: number;
  days_logged: number;
}
