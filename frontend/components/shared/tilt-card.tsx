"use client";

import { useRef, type ReactNode } from "react";

/**
 * TiltCard — wraps any card in a 3D perspective tilt + inner spotlight that
 * follows the cursor within the card bounds. Zero JS on mobile (touch devices
 * get plain hover). The effect is entirely CSS-transform + JS style mutation,
 * so React never re-renders from the animation loop.
 *
 * Usage: wrap any Card or surface you want to feel interactive.
 *   <TiltCard><Card>...</Card></TiltCard>
 */
export function TiltCard({
  children,
  className = "",
  intensity = 8,
}: {
  children: ReactNode;
  className?: string;
  /** Max tilt angle in degrees. Default 8 feels subtle; 14 is dramatic. */
  intensity?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);

  function onMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();

    // Normalised coords: -1 → +1 across the card
    const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
    const y = ((e.clientY - rect.top) / rect.height - 0.5) * 2;

    el.style.transform = `perspective(800px) rotateY(${x * intensity}deg) rotateX(${-y * intensity}deg) scale(1.015)`;

    // Move inner spotlight to follow cursor
    const glow = glowRef.current;
    if (glow) {
      const px = ((e.clientX - rect.left) / rect.width) * 100;
      const py = ((e.clientY - rect.top) / rect.height) * 100;
      glow.style.background = `radial-gradient(circle at ${px}% ${py}%, color-mix(in oklch, var(--color-primary) 10%, transparent) 0%, transparent 65%)`;
      glow.style.opacity = "1";
    }
  }

  function onMouseLeave() {
    const el = ref.current;
    if (el) {
      el.style.transform =
        "perspective(800px) rotateY(0deg) rotateX(0deg) scale(1)";
    }
    if (glowRef.current) glowRef.current.style.opacity = "0";
  }

  return (
    <div
      ref={ref}
      className={`relative ${className}`}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{
        transition: "transform 0.15s ease, box-shadow 0.15s ease",
        willChange: "transform",
        transformStyle: "preserve-3d",
      }}
    >
      {/* Inner glow that follows the cursor */}
      <div
        ref={glowRef}
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10 rounded-[inherit] opacity-0"
        style={{ transition: "opacity 0.2s ease" }}
      />
      {children}
    </div>
  );
}
