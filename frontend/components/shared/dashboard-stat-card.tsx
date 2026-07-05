"use client";

import { type LucideIcon } from "lucide-react";
import { motion, useInView, animate } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * One stat tile: label + value, optionally with an icon and a numeric
 * count-up animation. Used anywhere the dashboard shows a single metric
 * (BMI, calories, exercise count, duration) so every stat in the app shares
 * one visual treatment instead of each card hand-rolling its own.
 *
 * `numericValue` + `suffix` enable the count-up; pass plain `value` instead
 * for non-numeric stats (e.g. a split name) where counting up makes no
 * sense.
 */
export function DashboardStatCard({
  label,
  value,
  numericValue,
  suffix = "",
  icon: Icon,
  className,
}: {
  label: string;
  value?: string;
  numericValue?: number;
  suffix?: string;
  icon?: LucideIcon;
  className?: string;
}) {
  const ref = useRef<HTMLParagraphElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-10% 0px" });
  const [displayValue, setDisplayValue] = useState(numericValue !== undefined ? 0 : null);

  useEffect(() => {
    if (numericValue === undefined || !isInView) return;
    const controls = animate(0, numericValue, {
      duration: 0.8,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => setDisplayValue(Math.round(latest)),
    });
    return () => controls.stop();
  }, [numericValue, isInView]);

  return (
    <div
      className={cn(
        "rounded-lg border bg-card/50 p-3 transition-colors hover:bg-accent/40",
        className,
      )}
    >
      <div className="flex items-center gap-1.5 text-muted-foreground">
        {Icon && <Icon className="size-3.5" />}
        <p className="text-xs">{label}</p>
      </div>
      <p ref={ref} className="mt-1 text-lg font-semibold">
        {numericValue !== undefined ? (
          <motion.span>
            {displayValue}
            {suffix}
          </motion.span>
        ) : (
          (value ?? "—")
        )}
      </p>
    </div>
  );
}
