import { type ComponentType, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Generic empty state shell — icon, title, description, optional action.
 * Used by domain-specific empty states (e.g. EmptyWorkoutState) so each
 * one only needs to supply the copy and action, not the layout.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-xl border border-dashed px-6 py-12 text-center",
        className,
      )}
    >
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Icon className="h-6 w-6 text-muted-foreground" />
        </div>
      )}
      <div className="space-y-1">
        <p className="font-semibold">{title}</p>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}
