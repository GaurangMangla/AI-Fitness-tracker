import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Consistent section heading used across the dashboard (and any future
 * page) — gives every section title the same size/weight/spacing instead of
 * each page hand-rolling its own `<h2 className="...">`. `action` is for a
 * right-aligned control (e.g. a "View all" link) without callers needing to
 * build the flex row themselves.
 */
export function SectionHeader({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-end justify-between gap-4", className)}>
      <div>
        <h2 className="text-lg font-semibold tracking-tight sm:text-xl">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
