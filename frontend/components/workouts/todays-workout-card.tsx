"use client";

import { useState } from "react";
import { Clock, Dumbbell, Target } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardStatCard } from "@/components/shared/dashboard-stat-card";
import { PrimaryButton } from "@/components/shared/primary-button";
import { ActiveWorkoutCard } from "@/components/workouts/active-workout-card";
import { useStartWorkout, isConflictError } from "@/hooks/use-workout-session";
import type { WorkoutDayResponse } from "@/types/user";

export function TodaysWorkoutCard({
  day,
  estimatedDurationMinutes,
}: {
  day: WorkoutDayResponse;
  estimatedDurationMinutes: number | null;
}) {
  // null  = no session open yet
  // string = session ID currently active
  const [sessionId, setSessionId] = useState<string | null>(null);
  const startWorkout = useStartWorkout();

  // Once a session is finished, the ActiveWorkoutCard calls onSessionEnded —
  // we clear the session ID so this card returns to its idle state.
  function handleSessionEnded() {
    setSessionId(null);
  }

  async function handleStart() {
    try {
      const session = await startWorkout.mutateAsync();
      setSessionId(session.id);
    } catch (err) {
      if (isConflictError(err)) {
        toast.error("You already have an active session. Refresh and try again.");
      } else {
        toast.error(err instanceof Error ? err.message : "Failed to start workout.");
      }
    }
  }

  // ── Active session view ──────────────────────────────────────────────────
  if (sessionId) {
    return (
      <ActiveWorkoutCard
        sessionId={sessionId}
        day={day}
        onSessionEnded={handleSessionEnded}
      />
    );
  }

  // ── Idle view ────────────────────────────────────────────────────────────
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.06, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/8 via-accent/5 to-transparent"
        />
        <CardHeader className="relative">
          <CardTitle>Today&apos;s workout</CardTitle>
          <CardDescription>{day.day_name}</CardDescription>
        </CardHeader>
        <CardContent className="relative space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <DashboardStatCard icon={Target} label="Focus area" value={day.focus_area} />
            <DashboardStatCard
              icon={Clock}
              label="Est. duration"
              value={estimatedDurationMinutes !== null ? `~${estimatedDurationMinutes} min` : "—"}
            />
            <DashboardStatCard
              icon={Dumbbell}
              label="Exercises"
              numericValue={day.workout_exercises.length}
            />
          </div>

          <PrimaryButton
            className="w-full animate-pulse-glow"
            onClick={handleStart}
            disabled={startWorkout.isPending}
          >
            {startWorkout.isPending ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Starting…
              </span>
            ) : (
              "Start Workout"
            )}
          </PrimaryButton>
        </CardContent>
      </Card>
    </motion.div>
  );
}
