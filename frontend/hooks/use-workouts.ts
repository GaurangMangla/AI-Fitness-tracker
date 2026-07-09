"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/lib/api-client";
import { getToken } from "@/lib/auth-token";
import type {
  GeneratedWorkoutPlanResponse,
  GenerateWorkoutRequest,
  WorkoutDayResponse,
  WorkoutPlanResponse,
} from "@/types/user";

export const CURRENT_WORKOUT_QUERY_KEY = ["workouts", "current"] as const;
export const TODAY_WORKOUT_QUERY_KEY = ["workouts", "today"] as const;

/**
 * GET /workouts/current — the user's active plan, or a 404 if none exists.
 * The 404 is a *real, expected* state (new user, never generated a plan), not
 * an error to surface — so `retry: false` keeps a single 404 from turning
 * into 3 failed requests by TanStack Query's default retry policy, and the
 * page itself reads `isNotFoundError(error)` to render the empty state
 * instead of an error banner.
 */
export function useCurrentWorkout() {
  return useQuery({
    queryKey: CURRENT_WORKOUT_QUERY_KEY,
    queryFn: () => apiFetch<WorkoutPlanResponse>("/workouts/current"),
    enabled: Boolean(getToken()),
    retry: false,
  });
}

/**
 * GET /workouts/today — today's specific day from the active plan. Also a
 * legitimate 404 (rest day, or no plan at all), handled the same way.
 */
export function useTodayWorkout() {
  return useQuery({
    queryKey: TODAY_WORKOUT_QUERY_KEY,
    queryFn: () => apiFetch<WorkoutDayResponse>("/workouts/today"),
    enabled: Boolean(getToken()),
    retry: false,
  });
}

/**
 * POST /workouts/generate — on success, both `current` and `today` are
 * invalidated so the dashboard refetches and reflects the freshly generated
 * plan without a manual page reload.
 */
export function useGenerateWorkout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: GenerateWorkoutRequest) =>
      apiFetch<GeneratedWorkoutPlanResponse>("/workouts/generate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CURRENT_WORKOUT_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: TODAY_WORKOUT_QUERY_KEY });
    },
  });
}

/** True when the error is the "no active plan" / "rest day" 404 — the one
 * non-error state the workout endpoints return via an HTTP error status. */
export function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
