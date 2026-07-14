import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Shared error state for any workout-related fetch that failed for a reason
 * other than "no plan exists" (that's `EmptyWorkoutState`'s job — see
 * `isNotFoundError` in `hooks/use-workouts.ts`). Covers real failures:
 * network errors, 500s, auth hiccups not already caught by the app layout.
 */
export function WorkoutErrorState({
  message = "Something went wrong loading your workout.",
  onRetry,
}: {
  message?: string;
  onRetry: () => void;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
        <p className="text-sm text-muted-foreground">{message}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}
