"use client";

import { motion } from "framer-motion";
import { Activity, CheckCircle2, Flame, TrendingUp } from "lucide-react";

import { GlassCard } from "@/components/shared/glass-card";

const BENEFITS = [
  "Personalized workouts",
  "AI-powered recommendations",
  "Nutrition planning",
  "Progress analytics",
];

/**
 * The right-hand branding panel used by both the login and register
 * split-screen layouts — same content either way, since the pitch for
 * "why sign in" and "why sign up" is identical. Hidden below `lg` so the
 * form remains the sole focus on mobile, where there isn't room for both.
 */
export function AuthBrandingPanel() {
  return (
    <div className="relative hidden h-full flex-col items-center justify-center overflow-hidden bg-gradient-to-br from-primary/10 via-accent/5 to-transparent p-10 lg:flex">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 flex max-w-sm flex-col gap-6"
      >
        <h2 className="text-3xl font-bold tracking-tight">
          Your training,{" "}
          <span className="text-gradient-brand">personalized end to end</span>
        </h2>
        <p className="text-muted-foreground">
          One profile. A real weekly workout plan, a matching nutrition plan,
          and every session tracked automatically.
        </p>

        <ul className="flex flex-col gap-3">
          {BENEFITS.map((benefit, i) => (
            <motion.li
              key={benefit}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.15 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
              className="flex items-center gap-2.5 text-sm"
            >
              <CheckCircle2 className="size-4 shrink-0 text-success" />
              {benefit}
            </motion.li>
          ))}
        </ul>
      </motion.div>

      {/* Floating ambient stat cards — same decorative pattern as the hero */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute right-10 top-16"
      >
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        >
          <GlassCard className="flex items-center gap-2.5 px-4 py-3">
            <Flame className="size-4 text-warning" />
            <div className="text-left">
              <p className="text-xs text-muted-foreground">Calories</p>
              <p className="text-sm font-semibold">2,150 kcal</p>
            </div>
          </GlassCard>
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute bottom-24 left-10"
      >
        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
        >
          <GlassCard className="flex items-center gap-2.5 px-4 py-3">
            <TrendingUp className="size-4 text-success" />
            <div className="text-left">
              <p className="text-xs text-muted-foreground">Streak</p>
              <p className="text-sm font-semibold">12 days</p>
            </div>
          </GlassCard>
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute bottom-40 right-14"
      >
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
        >
          <GlassCard className="flex items-center gap-2.5 px-4 py-3">
            <Activity className="size-4 text-primary" />
            <div className="text-left">
              <p className="text-xs text-muted-foreground">BMI</p>
              <p className="text-sm font-semibold">23.4 · Normal</p>
            </div>
          </GlassCard>
        </motion.div>
      </motion.div>
    </div>
  );
}
