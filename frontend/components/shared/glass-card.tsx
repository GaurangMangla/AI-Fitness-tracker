import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * A translucent, blurred-backdrop surface — used for elevated or sticky
 * panels (sticky headers, hero sections) where a plain `Card` would look
 * flat against the page background. Deliberately not a replacement for
 * `Card` everywhere: overusing the glass effect would erase the visual
 * hierarchy it's meant to create.
 */
export function GlassCard({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("glass-card rounded-xl", className)}>{children}</div>;
}
