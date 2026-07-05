"use client";

import { useEffect, useRef, useState } from "react";

/**
 * CursorGlow — a soft radial spotlight that follows the mouse.
 * Moves via CSS custom properties on the element itself (not React state),
 * so re-renders are completely bypassed and it stays at 60fps even on heavy pages.
 * Disabled on touch devices and when prefers-reduced-motion is set.
 */
function CursorGlow() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Don't activate on touch-primary devices
    if (window.matchMedia("(pointer: coarse)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const el = ref.current;
    if (!el) return;

    let raf = 0;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    // Lerp factor — lower = more lag (dreamy), higher = snappier
    const LERP = 0.08;

    function tick() {
      currentX += (targetX - currentX) * LERP;
      currentY += (targetY - currentY) * LERP;
      el!.style.transform = `translate(${currentX}px, ${currentY}px) translate(-50%, -50%)`;
      raf = requestAnimationFrame(tick);
    }

    function onMove(e: MouseEvent) {
      targetX = e.clientX;
      targetY = e.clientY;
      setVisible(true);
    }

    function onLeave() {
      setVisible(false);
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mouseleave", onLeave);
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden
      className="pointer-events-none fixed left-0 top-0 z-0 h-[500px] w-[500px] rounded-full"
      style={{
        background:
          "radial-gradient(circle at center, color-mix(in oklch, var(--color-primary) 12%, transparent) 0%, transparent 70%)",
        opacity: visible ? 1 : 0,
        transition: "opacity 0.4s ease",
        willChange: "transform",
      }}
    />
  );
}

/**
 * AmbientBackground — three slow-drifting gradient orbs + a faint dot-grid
 * overlay + an interactive cursor glow. Renders behind page content via
 * `position:fixed` so it stays put during scroll without layout impact.
 *
 * Mount once inside AppLayout so it persists across route transitions
 * without flashing between pages.
 */
export function AmbientBackground() {
  return (
    <>
      <CursorGlow />
      <div
        className="pointer-events-none fixed inset-0 overflow-hidden"
        aria-hidden
      >
        {/* Orb 1 — primary (indigo), top-left */}
        <div className="animate-orb-1 absolute -left-[20%] -top-[20%] h-[65vh] w-[65vh] rounded-full bg-primary/10 blur-[130px] dark:bg-primary/18" />

        {/* Orb 2 — accent (emerald), bottom-right */}
        <div className="animate-orb-2 absolute -bottom-[15%] -right-[15%] h-[55vh] w-[55vh] rounded-full blur-[110px]"
          style={{ background: "color-mix(in oklch, var(--color-accent-foreground) 7%, transparent)" }}
        />

        {/* Orb 3 — indigo tint, center-right */}
        <div className="animate-orb-3 absolute right-[8%] top-[28%] h-[40vh] w-[40vh] rounded-full bg-primary/6 blur-[90px] dark:bg-primary/10" />

        {/* Orb 4 — warmish, bottom-left for balance */}
        <div
          className="animate-orb-1 absolute -bottom-[10%] left-[15%] h-[30vh] w-[30vh] rounded-full blur-[80px]"
          style={{
            background: "color-mix(in oklch, var(--color-warning) 5%, transparent)",
            animationDelay: "-9s",
            animationDuration: "22s",
          }}
        />

        {/* Dot-grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.025] dark:opacity-[0.045]"
          style={{
            backgroundImage:
              "radial-gradient(circle, currentColor 1px, transparent 1px)",
            backgroundSize: "32px 32px",
          }}
        />

        {/* Very subtle noise texture via SVG filter — adds film-grain premium feel */}
        <svg className="absolute inset-0 h-full w-full opacity-[0.015] dark:opacity-[0.03]" aria-hidden>
          <filter id="athlyt-noise">
            <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter="url(#athlyt-noise)" />
        </svg>
      </div>
    </>
  );
}
