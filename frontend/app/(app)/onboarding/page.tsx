"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { PrimaryButton } from "@/components/shared/primary-button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CURRENT_USER_QUERY_KEY, useCurrentUser } from "@/hooks/use-current-user";
import { ApiError, apiFetch } from "@/lib/api-client";
import {
  ACTIVITY_LEVEL_OPTIONS,
  DIET_PREFERENCE_OPTIONS,
  EQUIPMENT_OPTIONS,
  FITNESS_GOAL_OPTIONS,
  GENDER_OPTIONS,
  WORKOUT_EXPERIENCE_OPTIONS,
} from "@/lib/profile-options";
import { type OnboardingFormValues, onboardingSchema } from "@/lib/validators/onboarding";
import type { UserResponse } from "@/types/user";
import type { z } from "zod";

export default function OnboardingPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();

  // Three type parameters because `age`/`height_cm`/`weight_kg` use
  // `z.coerce.number()`: while the user is typing, those fields hold raw
  // strings (the schema's *input* type) — only after Zod validates on submit
  // do they become numbers (the *output* type, `OnboardingFormValues`). RHF's
  // third generic is what lets `handleSubmit`'s callback receive the
  // post-validation, properly-numeric values below.
  const form = useForm<z.input<typeof onboardingSchema>, unknown, OnboardingFormValues>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: { name: "", equipment_available: [] },
  });

  // A user who already completed onboarding has no reason to see this page
  // again — send them straight to the dashboard instead.
  useEffect(() => {
    if (user?.profile) {
      router.replace("/dashboard");
    }
  }, [user, router]);

  const mutation = useMutation({
    mutationFn: (values: OnboardingFormValues) =>
      apiFetch<UserResponse>("/users/me", {
        method: "PATCH",
        body: JSON.stringify(values),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, data);
      toast.success("Profile complete. Welcome to Athlyt.");
      router.push("/dashboard");
    },
    onError: (error: ApiError) => {
      toast.error(error.message);
    },
  });

  return (
    <div className="mx-auto max-w-2xl animate-fade-in-up">
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Set up your profile</CardTitle>
          <CardDescription>
            This takes a minute and powers your BMI, calorie target, and (soon) your workout
            and diet plans.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
              className="space-y-8"
            >
              <section className="space-y-4">
                <h3 className="text-sm font-semibold text-muted-foreground">About you</h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Your name" {...field} />
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
                            placeholder="Years"
                            {...field}
                            value={(field.value as string | number | undefined) ?? ""}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <FormField
                  control={form.control}
                  name="gender"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Gender</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select gender" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {GENDER_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>Used for an accurate calorie estimate.</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-semibold text-muted-foreground">Body metrics</h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="height_cm"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Height (cm)</FormLabel>
                        <FormControl>
                          <Input
                          type="number"
                          placeholder="e.g. 175"
                          {...field}
                          value={(field.value as string | number | undefined) ?? ""}
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
                          placeholder="e.g. 70"
                          {...field}
                          value={(field.value as string | number | undefined) ?? ""}
                        />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-semibold text-muted-foreground">Training</h3>
                <FormField
                  control={form.control}
                  name="fitness_goal"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Fitness goal</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select a goal" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {FITNESS_GOAL_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="activity_level"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Activity level</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select your activity level" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {ACTIVITY_LEVEL_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>This drives your daily calorie estimate.</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="workout_experience"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Workout experience</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select your experience level" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {WORKOUT_EXPERIENCE_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="equipment_available"
                  render={() => (
                    <FormItem>
                      <FormLabel>Equipment available</FormLabel>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {EQUIPMENT_OPTIONS.map((option) => (
                          <FormField
                            key={option.value}
                            control={form.control}
                            name="equipment_available"
                            render={({ field }) => {
                              const current = field.value ?? [];
                              const checked = current.includes(option.value);
                              return (
                                <FormItem className="flex items-center gap-2 space-y-0">
                                  <FormControl>
                                    <Checkbox
                                      checked={checked}
                                      onCheckedChange={(isChecked) => {
                                        field.onChange(
                                          isChecked
                                            ? [...current, option.value]
                                            : current.filter((value) => value !== option.value),
                                        );
                                      }}
                                    />
                                  </FormControl>
                                  <FormLabel className="font-normal">{option.label}</FormLabel>
                                </FormItem>
                              );
                            }}
                          />
                        ))}
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-semibold text-muted-foreground">Nutrition</h3>
                <FormField
                  control={form.control}
                  name="diet_preference"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Diet preference</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select a diet preference" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {DIET_PREFERENCE_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </section>

              <PrimaryButton type="submit" className="w-full" disabled={mutation.isPending}>
                {mutation.isPending ? "Saving…" : "Complete profile"}
              </PrimaryButton>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
