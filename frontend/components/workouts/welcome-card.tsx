"use client";

import { Flame, Target, Calendar, Beef } from "lucide-react";
import { motion } from "framer-motion";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardStatCard } from "@/components/shared/dashboard-stat-card";
import { FITNESS_GOAL_OPTIONS } from "@/lib/profile-options";
import type { ProfileMetrics, ProfileResponse, WorkoutPlanResponse } from "@/types/user";

function labelFor(options: readonly { value: string; label: string }[], value: string): string {
  return options.find((option) => option.value === value)?.label ?? value;
}

/** A greeting that changes with the time of day — one of the "dashboard
 * feel" cues called for in the design spec, computed client-side from the
 * visitor's local clock rather than the server's (which could be in a
 * different timezone). */
function timeOfDayGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 5) return "Still up";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  if (hour < 21) return "Good evening";
  return "Good evening";
}

/**
 * Section 1 — the welcome summary. `plan` is nullable: a user who hasn't
 * generated a workout yet still has a name/goal/calorie target to show, just
 * no split/workout-days values, which render as an em dash instead of being
 * left blank or crashing on a null access.
 */
export function WelcomeCard({
  profile,
  metrics,
  plan,
}: {
  profile: ProfileResponse;
  metrics: ProfileMetrics;
  plan: WorkoutPlanResponse | null;
}) {
  return (
    <Card className="animate-fade-in-up overflow-hidden">
      <CardHeader>
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <p className="text-sm text-muted-foreground">{timeOfDayGreeting()},</p>
          <CardTitle className="text-2xl">
            <span className="text-gradient-brand">{profile.name}</span>
          </CardTitle>
        </motion.div>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <DashboardStatCard
          icon={Target}
          label="Fitness goal"
          value={labelFor(FITNESS_GOAL_OPTIONS, profile.fitness_goal)}
        />
        <DashboardStatCard icon={Flame} label="Current split" value={plan?.title ?? "—"} />
        <DashboardStatCard
          icon={Calendar}
          label="Workout days"
          value={plan ? `${plan.workout_days} / week` : "—"}
        />
        <DashboardStatCard
          icon={Beef}
          label="Daily calorie target"
          numericValue={metrics.daily_calories}
          suffix=" kcal"
        />
      </CardContent>
    </Card>
  );
}
