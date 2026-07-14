"use client";

import { motion } from "framer-motion";

import { Badge } from "@/components/ui/badge";
import { TiltCard } from "@/components/shared/tilt-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { WorkoutDayResponse } from "@/types/user";

/**
 * One day within the weekly plan grid (Section 3). Clickable — selecting it
 * drives Section 4 (Workout Details) below. `isToday` adds a visual
 * highlight so the user's current day stands out among the week's cards.
 * `index` drives Framer Motion's stagger (via the parent's `staggerChildren`
 * transition) so the grid fills in card-by-card rather than popping in
 * together.
 */
export function WeeklyPlanCard({
  day,
  isToday,
  isSelected,
  estimatedDurationMinutes,
  onSelect,
}: {
  day: WorkoutDayResponse;
  isToday: boolean;
  isSelected: boolean;
  estimatedDurationMinutes: number;
  onSelect: () => void;
}) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 12 },
        visible: { opacity: 1, y: 0 },
      }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      whileTap={{ scale: 0.98 }}
    >
      <TiltCard intensity={5}>
      <Card
        role="button"
        tabIndex={0}
        onClick={onSelect}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onSelect();
          }
        }}
        className={cn(
          "cursor-pointer transition-shadow duration-200",
          isSelected
            ? "border-primary shadow-md ring-1 ring-primary"
            : "hover:border-primary/50 hover:shadow-md",
        )}
      >
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base">{day.day_name}</CardTitle>
            {isToday && (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2 }}>
                <Badge>Today</Badge>
              </motion.div>
            )}
          </div>
          <CardDescription>{day.focus_area}</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{day.workout_exercises.length} exercises</span>
          <span>~{estimatedDurationMinutes} min</span>
        </CardContent>
      </Card>
      </TiltCard>
    </motion.div>
  );
}
