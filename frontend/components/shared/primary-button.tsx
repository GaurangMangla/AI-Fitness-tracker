import { forwardRef } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * The app's primary call-to-action button — same underlying shadcn `Button`
 * (so it inherits focus rings, disabled states, etc. for free) with the
 * brand's hover-lift + press-down micro-interaction baked in, so every
 * "main action" button in the app feels identical without each call site
 * repeating the same className.
 */
export const PrimaryButton = forwardRef<HTMLButtonElement, React.ComponentProps<typeof Button>>(
  ({ className, ...props }, ref) => (
    <Button
      ref={ref}
      className={cn(
        "shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:scale-[0.98]",
        className,
      )}
      {...props}
    />
  ),
);
PrimaryButton.displayName = "PrimaryButton";
