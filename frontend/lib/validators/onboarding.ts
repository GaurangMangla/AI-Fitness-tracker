import { z } from "zod";

export const onboardingSchema = z.object({
  name: z.string().min(1, "Name is required.").max(100, "Name is too long."),
  age: z.coerce
    .number({ message: "Age is required." })
    .int("Age must be a whole number.")
    .min(13, "Must be at least 13.")
    .max(100, "Must be 100 or under."),
  gender: z.enum(["male", "female", "other"], { message: "Select a gender." }),
  height_cm: z.coerce
    .number({ message: "Height is required." })
    .min(100, "Enter a height between 100–250 cm.")
    .max(250, "Enter a height between 100–250 cm."),
  weight_kg: z.coerce
    .number({ message: "Weight is required." })
    .min(30, "Enter a weight between 30–300 kg.")
    .max(300, "Enter a weight between 30–300 kg."),
  fitness_goal: z.enum(["weight_loss", "muscle_gain", "maintenance", "general_fitness"], {
    message: "Select a fitness goal.",
  }),
  activity_level: z.enum(
    ["sedentary", "lightly_active", "moderately_active", "very_active", "extra_active"],
    { message: "Select an activity level." },
  ),
  workout_experience: z.enum(["beginner", "intermediate", "advanced"], {
    message: "Select your experience level.",
  }),
  equipment_available: z
    .array(z.enum(["none", "dumbbells", "barbell", "resistance_bands", "pull_up_bar", "full_gym"]))
    .min(1, "Select at least one option."),
  diet_preference: z.enum(["vegetarian", "non_vegetarian", "vegan"], {
    message: "Select a diet preference.",
  }),
});

export type OnboardingFormValues = z.infer<typeof onboardingSchema>;
