import { cn } from "@/lib/utils";

/**
 * The base shimmer block every feature-specific skeleton (workout cards,
 * future diet/progress cards) composes. Distinct from the plain `Skeleton`
 * primitive in `components/ui/skeleton.tsx` (a flat pulse, shadcn's
 * default) — this one sweeps a highlight across the block, used for
 * busier loading screens where a livelier loading state earns its keep.
 */
export function LoadingSkeleton({
  className,
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return <div className={cn("animate-shimmer rounded-md", className)} style={style} />;
}
