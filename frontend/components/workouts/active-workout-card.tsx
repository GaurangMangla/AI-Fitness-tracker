"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  CheckCircle2,
  Circle,
  Clock,
  Flame,
  Pause,
  Play,
  SkipForward,
  Trophy,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PrimaryButton } from "@/components/shared/primary-button";
import {
  useCompleteExercise,
  useFinishWorkout,
  usePauseWorkout,
  useResumeWorkout,
  useSessionDetail,
  useSkipExercise,
} from "@/hooks/use-workout-session";
import type {
  ExerciseCompletionResponse,
  FinishWorkoutResponse,
  WorkoutDayResponse,
  WorkoutSessionResponse,
} from "@/types/user";

// ---------------------------------------------------------------------------
// Live timer hook — counts seconds since the session started, pausing when
// the session status is "paused". Runs on an interval, not rAF, since
// per-second precision is all we need.
// ---------------------------------------------------------------------------
function useElapsedSeconds(session: WorkoutSessionResponse): number {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (session.status === "completed") return;

    function compute() {
      const base = session.accumulated_active_seconds ?? 0;
      if (session.status === "paused") {
        setElapsed(base);
        return;
      }
      const resumedAt = new Date(session.last_resumed_at ?? session.started_at).getTime();
      const now = Date.now();
      setElapsed(base + Math.floor((now - resumedAt) / 1000));
    }

    compute();
    const id = setInterval(compute, 1000);
    return () => clearInterval(id);
  }, [session]);

  return elapsed;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// ---------------------------------------------------------------------------
// Finish screen — shown after POST /finish succeeds
// ---------------------------------------------------------------------------
function FinishScreen({
  result,
  onDone,
}: {
  result: FinishWorkoutResponse;
  onDone: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center gap-6 py-8 text-center"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.1 }}
      >
        <Trophy className="h-16 w-16 text-yellow-500" />
      </motion.div>

      <div>
        <h2 className="text-2xl font-bold">Workout complete!</h2>
        <p className="mt-1 text-muted-foreground">Great work. Here&apos;s your summary.</p>
      </div>

      <div className="grid w-full max-w-sm grid-cols-3 gap-3">
        {[
          { label: "Duration", value: `${result.total_duration_minutes} min` },
          { label: "Completed", value: String(result.exercises_completed) },
          { label: "Calories", value: `~${Math.round(result.calories_burned_estimate)} kcal` },
        ].map(({ label, value }) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg bg-muted/60 py-3"
          >
            <p className="text-xl font-bold">{value}</p>
            <p className="text-xs text-muted-foreground">{label}</p>
          </motion.div>
        ))}
      </div>

      <PrimaryButton onClick={onDone} className="w-full max-w-sm">
        Back to dashboard
      </PrimaryButton>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Single exercise row
// ---------------------------------------------------------------------------
function ExerciseRow({
  workoutExercise,
  completion,
  onComplete,
  onSkip,
  isPending,
}: {
  workoutExercise: WorkoutDayResponse["workout_exercises"][0];
  completion: ExerciseCompletionResponse | undefined;
  onComplete: () => void;
  onSkip: () => void;
  isPending: boolean;
}) {
  const done = completion?.completed ?? false;
  const skipped = completion?.skipped ?? false;
  const touched = done || skipped;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
        done
          ? "border-green-500/30 bg-green-500/8"
          : skipped
          ? "border-muted/50 bg-muted/20 opacity-60"
          : "border-border bg-card"
      }`}
    >
      {/* Status icon */}
      <div className="shrink-0">
        <AnimatePresence mode="wait">
          {done ? (
            <motion.div
              key="done"
              initial={{ scale: 0, rotate: -45 }}
              animate={{ scale: 1, rotate: 0 }}
              exit={{ scale: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </motion.div>
          ) : skipped ? (
            <motion.div key="skip" initial={{ scale: 0 }} animate={{ scale: 1 }}>
              <SkipForward className="h-5 w-5 text-muted-foreground" />
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ scale: 0 }} animate={{ scale: 1 }}>
              <Circle className="h-5 w-5 text-muted-foreground/50" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Name + sets/reps */}
      <div className="min-w-0 flex-1">
        <p className={`truncate text-sm font-medium ${skipped ? "line-through" : ""}`}>
          {workoutExercise.exercise.name}
        </p>
        <p className="text-xs text-muted-foreground">
          {workoutExercise.sets} sets × {workoutExercise.reps} · {workoutExercise.rest_seconds}s rest
        </p>
      </div>

      {/* Actions — hidden once the exercise is touched */}
      {!touched && (
        <div className="flex shrink-0 gap-1.5">
          <Button
            size="sm"
            variant="outline"
            onClick={onSkip}
            disabled={isPending}
            className="h-7 px-2 text-xs"
          >
            Skip
          </Button>
          <Button
            size="sm"
            onClick={onComplete}
            disabled={isPending}
            className="h-7 bg-green-600 px-2 text-xs text-white hover:bg-green-700"
          >
            Done
          </Button>
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function ActiveWorkoutCard({
  sessionId,
  day,
  onSessionEnded,
}: {
  sessionId: string;
  day: WorkoutDayResponse;
  onSessionEnded: () => void;
}) {
  const { data: session, isLoading } = useSessionDetail(sessionId);
  const pauseMutation = usePauseWorkout();
  const resumeMutation = useResumeWorkout();
  const completeMutation = useCompleteExercise();
  const skipMutation = useSkipExercise();
  const finishMutation = useFinishWorkout();

  const [finishResult, setFinishResult] = useState<FinishWorkoutResponse | null>(null);

  const elapsed = useElapsedSeconds(
    session ?? {
      id: sessionId,
      status: "active",
      started_at: new Date().toISOString(),
      accumulated_active_seconds: 0,
      last_resumed_at: new Date().toISOString(),
      user_id: "",
      workout_plan_id: "",
      workout_day_id: "",
      completed_at: null,
      total_duration_minutes: null,
      calories_burned_estimate: null,
      exercise_completions: [],
    }
  );

  if (isLoading || !session) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </CardContent>
      </Card>
    );
  }

  // Show finish screen after successfully completing
  if (finishResult) {
    return (
      <Card className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-yellow-500/8 via-transparent to-transparent" />
        <CardContent className="relative">
          <FinishScreen result={finishResult} onDone={onSessionEnded} />
        </CardContent>
      </Card>
    );
  }

  const completions = session.exercise_completions ?? [];
  const totalExercises = day.workout_exercises.length;
  const touchedCount = completions.filter((c) => c.completed || c.skipped).length;
  const completedCount = completions.filter((c) => c.completed).length;
  const progressPct = totalExercises > 0 ? (touchedCount / totalExercises) * 100 : 0;
  const isPaused = session.status === "paused";
  const anyPending =
    pauseMutation.isPending ||
    resumeMutation.isPending ||
    completeMutation.isPending ||
    skipMutation.isPending;

  function getCompletion(weId: string) {
    return completions.find((c) => c.workout_exercise_id === weId);
  }

  async function handlePauseResume() {
    if (isPaused) {
      await resumeMutation.mutateAsync(sessionId);
    } else {
      await pauseMutation.mutateAsync(sessionId);
    }
  }

  async function handleComplete(weId: string) {
    await completeMutation.mutateAsync({
      sessionId,
      exerciseId: weId,
      data: {},
    });
  }

  async function handleSkip(weId: string) {
    await skipMutation.mutateAsync({
      sessionId,
      exerciseId: weId,
      data: {},
    });
  }

  async function handleFinish() {
    try {
      const result = await finishMutation.mutateAsync(sessionId);
      setFinishResult(result);
    } catch {
      toast.error("Failed to finish workout. Please try again.");
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="relative overflow-hidden">
        {/* Gradient wash — stronger than the idle card since this is the active state */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-accent/5 to-transparent" />

        <CardHeader className="relative">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {isPaused ? (
                  <span className="text-muted-foreground">Paused</span>
                ) : (
                  <span className="text-gradient-brand">Workout in progress</span>
                )}
              </CardTitle>
              <p className="mt-0.5 text-sm text-muted-foreground">{day.day_name}</p>
            </div>

            {/* Live timer */}
            <div className={`flex items-center gap-1.5 ${isPaused ? "" : "animate-timer-tick"}`}>
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-lg font-bold">{formatTime(elapsed)}</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{completedCount} of {totalExercises} completed</span>
              <span>{Math.round(progressPct)}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-primary to-accent-foreground"
                initial={{ width: 0 }}
                animate={{ width: `${progressPct}%` }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="relative space-y-3">
          {/* Exercise list */}
          <motion.div className="space-y-2" layout>
            {day.workout_exercises.map((we) => (
              <ExerciseRow
                key={we.id}
                workoutExercise={we}
                completion={getCompletion(we.id)}
                onComplete={() => handleComplete(we.id)}
                onSkip={() => handleSkip(we.id)}
                isPending={anyPending}
              />
            ))}
          </motion.div>

          {/* Controls */}
          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              onClick={handlePauseResume}
              disabled={anyPending || finishMutation.isPending}
              className="flex-1 gap-2"
            >
              {isPaused ? (
                <>
                  <Play className="h-4 w-4" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="h-4 w-4" />
                  Pause
                </>
              )}
            </Button>

            <PrimaryButton
              onClick={handleFinish}
              disabled={anyPending || finishMutation.isPending}
              className="flex-1 gap-2"
            >
              {finishMutation.isPending ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : (
                <>
                  <Flame className="h-4 w-4" />
                  Finish workout
                </>
              )}
            </PrimaryButton>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
