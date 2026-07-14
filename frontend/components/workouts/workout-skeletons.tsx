import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";

export function WelcomeCardSkeleton() {
  return (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <LoadingSkeleton className="h-7 w-56" />
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="space-y-2">
            <LoadingSkeleton className="h-3 w-20" />
            <LoadingSkeleton className="h-5 w-24" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function TodaysWorkoutCardSkeleton() {
  return (
    <Card className="animate-fade-in-up [animation-delay:60ms]">
      <CardHeader>
        <LoadingSkeleton className="h-6 w-40" />
        <LoadingSkeleton className="h-4 w-28" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <LoadingSkeleton className="h-12" />
          <LoadingSkeleton className="h-12" />
          <LoadingSkeleton className="h-12" />
        </div>
        <LoadingSkeleton className="h-9 w-full" />
      </CardContent>
    </Card>
  );
}

export function WeeklyPlanSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 5 }).map((_, index) => (
        <LoadingSkeleton
          key={index}
          className="h-28 animate-fade-in-up"
          style={{ animationDelay: `${index * 60}ms` }}
        />
      ))}
    </div>
  );
}

export function ExerciseListSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <LoadingSkeleton
          key={index}
          className="h-44 animate-fade-in-up"
          style={{ animationDelay: `${index * 60}ms` }}
        />
      ))}
    </div>
  );
}
