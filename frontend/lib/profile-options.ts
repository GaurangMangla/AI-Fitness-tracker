// Mirrors `backend/app/models/enums.py`. Defined once here so the Select/
// Checkbox UI and the Zod validation schema (`lib/validators/onboarding.ts`)
// render and validate against the exact same set of options.

export const GENDER_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
] as const;

export const FITNESS_GOAL_OPTIONS = [
  { value: "weight_loss", label: "Weight loss" },
  { value: "muscle_gain", label: "Muscle gain" },
  { value: "maintenance", label: "Maintenance" },
  { value: "general_fitness", label: "General fitness" },
] as const;

export const ACTIVITY_LEVEL_OPTIONS = [
  { value: "sedentary", label: "Sedentary — little to no exercise" },
  { value: "lightly_active", label: "Lightly active — 1–3 days/week" },
  { value: "moderately_active", label: "Moderately active — 3–5 days/week" },
  { value: "very_active", label: "Very active — 6–7 days/week" },
  { value: "extra_active", label: "Extra active — physical job + training" },
] as const;

export const WORKOUT_EXPERIENCE_OPTIONS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
] as const;

export const DIET_PREFERENCE_OPTIONS = [
  { value: "vegetarian", label: "Vegetarian" },
  { value: "non_vegetarian", label: "Non-vegetarian" },
  { value: "vegan", label: "Vegan" },
] as const;

export const EQUIPMENT_OPTIONS = [
  { value: "none", label: "No equipment" },
  { value: "dumbbells", label: "Dumbbells" },
  { value: "barbell", label: "Barbell" },
  { value: "resistance_bands", label: "Resistance bands" },
  { value: "pull_up_bar", label: "Pull-up bar" },
  { value: "full_gym", label: "Full gym access" },
] as const;

// --- Exercise-specific options (Milestone 2.4) ------------------------------
// Distinct from the profile's own EQUIPMENT_OPTIONS above — exercises use a
// finer-grained equipment vocabulary (see backend `ExerciseEquipment` enum).

export const MUSCLE_GROUP_LABELS: Record<string, string> = {
  chest: "Chest",
  back: "Back",
  shoulders: "Shoulders",
  legs: "Legs",
  arms: "Arms",
  core: "Core",
  cardio: "Cardio",
};

export const EXERCISE_EQUIPMENT_LABELS: Record<string, string> = {
  bodyweight: "Bodyweight",
  dumbbells: "Dumbbells",
  barbell: "Barbell",
  kettlebell: "Kettlebell",
  resistance_bands: "Resistance bands",
  machine: "Machine",
  cable: "Cable",
  bench: "Bench",
  pull_up_bar: "Pull-up bar",
};

export const EXERCISE_DIFFICULTY_LABELS: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};
