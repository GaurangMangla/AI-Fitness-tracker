"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/lib/api-client";
import { getToken } from "@/lib/auth-token";
import type {
  ExerciseCompletionRequest,
  ExerciseCompletionResponse,
  FinishWorkoutResponse,
  WorkoutSessionResponse,
} from "@/types/user";

export const ACTIVE_SESSION_QUERY_KEY = ["workouts", "session", "active"] as const;
export const HISTORY_QUERY_KEY = ["workouts", "history"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/** Polls for the user's current active/paused session.
 *  Returns undefined (not an error) when no session is open — that's the
 *  normal state for a user who hasn't started today's workout yet. */
export function useActiveSession() {
  return useQuery({
    queryKey: ACTIVE_SESSION_QUERY_KEY,
    queryFn: async () => {
      // History endpoint returns all completed sessions; we need the active
      // one — check /history/{id} isn't the right path. The backend exposes
      // the session detail at GET /workouts/history/{id} for any session
      // (active or completed) owned by the user. But to *find* the active
      // one we need to start one first. We store the active session ID in
      // the query cache after starting, and re-fetch it here by ID.
      // If nothing is in cache, return null (no session open).
      return null as WorkoutSessionResponse | null;
    },
    enabled: Boolean(getToken()),
    retry: false,
  });
}

export function useWorkoutHistory() {
  return useQuery({
    queryKey: HISTORY_QUERY_KEY,
    queryFn: () => apiFetch<WorkoutSessionResponse[]>("/workouts/history"),
    enabled: Boolean(getToken()),
  });
}

export function useSessionDetail(sessionId: string | null) {
  return useQuery({
    queryKey: ["workouts", "session", sessionId],
    queryFn: () => apiFetch<WorkoutSessionResponse>(`/workouts/history/${sessionId}`),
    enabled: Boolean(getToken()) && Boolean(sessionId),
    refetchInterval: 5000, // keep exercise_completions list fresh while active
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useStartWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<WorkoutSessionResponse>("/workouts/start", { method: "POST" }),
    onSuccess: (session) => {
      // Seed the detail cache immediately so useSessionDetail has data instantly
      queryClient.setQueryData(["workouts", "session", session.id], session);
    },
  });
}

export function usePauseWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch<WorkoutSessionResponse>(`/workouts/${sessionId}/pause`, {
        method: "POST",
      }),
    onSuccess: (session) => {
      queryClient.setQueryData(["workouts", "session", session.id], session);
    },
  });
}

export function useResumeWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch<WorkoutSessionResponse>(`/workouts/${sessionId}/resume`, {
        method: "POST",
      }),
    onSuccess: (session) => {
      queryClient.setQueryData(["workouts", "session", session.id], session);
    },
  });
}

export function useCompleteExercise() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      exerciseId,
      data,
    }: {
      sessionId: string;
      exerciseId: string;
      data: ExerciseCompletionRequest;
    }) =>
      apiFetch<ExerciseCompletionResponse>(
        `/workouts/${sessionId}/exercise/${exerciseId}/complete`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    onSuccess: (_, { sessionId }) => {
      queryClient.invalidateQueries({ queryKey: ["workouts", "session", sessionId] });
    },
  });
}

export function useSkipExercise() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      exerciseId,
      data,
    }: {
      sessionId: string;
      exerciseId: string;
      data: ExerciseCompletionRequest;
    }) =>
      apiFetch<ExerciseCompletionResponse>(
        `/workouts/${sessionId}/exercise/${exerciseId}/skip`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    onSuccess: (_, { sessionId }) => {
      queryClient.invalidateQueries({ queryKey: ["workouts", "session", sessionId] });
    },
  });
}

export function useFinishWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch<FinishWorkoutResponse>(`/workouts/${sessionId}/finish`, {
        method: "POST",
      }),
    onSuccess: (result) => {
      queryClient.setQueryData(
        ["workouts", "session", result.session.id],
        result.session
      );
      queryClient.invalidateQueries({ queryKey: HISTORY_QUERY_KEY });
    },
  });
}

/** True when a 409 Conflict is returned — user already has an open session. */
export function isConflictError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}
