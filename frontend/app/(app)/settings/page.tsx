"use client";

import { useEffect } from "react";
import { motion, type Variants } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { SectionHeader } from "@/components/shared/section-header";
import { PrimaryButton } from "@/components/shared/primary-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCurrentUser } from "@/hooks/use-current-user";
import { apiFetch } from "@/lib/api-client";
import {
  ACTIVITY_LEVEL_OPTIONS,
  DIET_PREFERENCE_OPTIONS,
  FITNESS_GOAL_OPTIONS,
  GENDER_OPTIONS,
  WORKOUT_EXPERIENCE_OPTIONS,
} from "@/lib/profile-options";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  age: z.number().int().min(13, "Must be at least 13").max(100),
  gender: z.string(),
  height_cm: z.number().min(100).max(250),
  weight_kg: z.number().min(30).max(300),
  fitness_goal: z.string(),
  activity_level: z.string(),
  workout_experience: z.string(),
  diet_preference: z.string(),
});

type FormValues = z.infer<typeof schema>;

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

// Defined outside component so it's not re-created every render
const SELECT_CONFIGS = [
  { name: "gender" as const, label: "Gender", options: GENDER_OPTIONS },
  { name: "fitness_goal" as const, label: "Fitness goal", options: FITNESS_GOAL_OPTIONS },
  { name: "activity_level" as const, label: "Activity level", options: ACTIVITY_LEVEL_OPTIONS },
  { name: "workout_experience" as const, label: "Experience", options: WORKOUT_EXPERIENCE_OPTIONS },
  { name: "diet_preference" as const, label: "Diet preference", options: DIET_PREFERENCE_OPTIONS },
];

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { data: user, isLoading } = useCurrentUser();
  const profile = user?.profile;

  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (profile) {
      form.reset({
        name: profile.name,
        age: profile.age,
        gender: profile.gender,
        height_cm: profile.height_cm,
        weight_kg: profile.weight_kg,
        fitness_goal: profile.fitness_goal,
        activity_level: profile.activity_level,
        workout_experience: profile.workout_experience,
        diet_preference: profile.diet_preference,
      });
    }
  }, [profile, form]);

  const mutation = useMutation({
    mutationFn: (data: FormValues) =>
      apiFetch("/users/me", { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      toast.success("Profile updated!");
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });
    },
    onError: () => toast.error("Failed to update profile."),
  });

  return (
    <motion.div variants={container} initial="hidden" animate="visible" className="space-y-8">
      <motion.div variants={item}>
        <SectionHeader title="Settings" description="Update your profile and fitness preferences" />
      </motion.div>

      <motion.div variants={item}>
        {isLoading ? (
          <Skeleton className="h-96 rounded-xl" />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit((d) => mutation.mutate(d))}
                  className="space-y-4"
                >
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
                          <FormControl>
                            <Input {...field} autoComplete="name" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="age"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Age</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              {...field}
                              onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="height_cm"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Height (cm)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              step="0.1"
                              {...field}
                              onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="weight_kg"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Weight (kg)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              step="0.1"
                              {...field}
                              onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {SELECT_CONFIGS.map(({ name, label, options }) => (
                      <FormField
                        key={name}
                        control={form.control}
                        name={name}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>{label}</FormLabel>
                            <Select onValueChange={field.onChange} value={field.value as string}>
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {options.map((o) => (
                                  <SelectItem key={o.value} value={o.value}>
                                    {o.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    ))}
                  </div>

                  <PrimaryButton type="submit" disabled={mutation.isPending}>
                    {mutation.isPending ? "Saving…" : "Save changes"}
                  </PrimaryButton>
                </form>
              </Form>
            </CardContent>
          </Card>
        )}
      </motion.div>
    </motion.div>
  );
}
