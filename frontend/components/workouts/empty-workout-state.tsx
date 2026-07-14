import { Dumbbell } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PrimaryButton } from "@/components/shared/primary-button";

/**
 * Section 5 — shown whenever GET /workouts/current 404s (no active plan).
 * Composes the generic `EmptyState` shell with workout-specific copy and
 * the "Generate Workout" action.
 */
export function EmptyWorkoutState({
  onGenerate,
  isGenerating,
}: {
  onGenerate: () => void;
  isGenerating: boolean;
}) {
  return (
    <EmptyState
      icon={Dumbbell}
      title="No active workout plan yet"
      description="Generate a personalized plan based on your profile to get started."
      action={
        <PrimaryButton onClick={onGenerate} disabled={isGenerating}>
          {isGenerating ? (
            <span className="flex items-center gap-2">
              <span className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Generating…
            </span>
          ) : (
            "Generate Workout"
          )}
        </PrimaryButton>
      }
    />
  );
}
