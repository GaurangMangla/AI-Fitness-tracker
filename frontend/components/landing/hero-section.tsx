"use client";

import { motion, type Variants } from "framer-motion";
import { Activity, Flame, TrendingUp } from "lucide-react";
import Link from "next/link";

import { GlassCard } from "@/components/shared/glass-card";
import { PrimaryButton } from "@/components/shared/primary-button";
import { Button } from "@/components/ui/button";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

/**
 * The first thing a visitor sees. Headline + supporting copy + two CTAs,
 * with a handful of small floating stat cards around the edges purely as
 * ambient decoration (not real data — see the two "real feature" sections
 * below the fold for that).
 */
export function HeroSection() {
  return (
    <section className="relative flex min-h-[92vh] flex-col items-center justify-center gap-8 px-6 pt-24 text-center">
      <motion.div
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
        className="flex max-w-3xl flex-col items-center gap-6"
      >
        <motion.span
          variants={fadeUp}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="glass-card rounded-full px-4 py-1.5 text-xs font-medium text-muted-foreground"
        >
          AI-powered fitness coaching, built for real training
        </motion.span>

        <motion.h1
          variants={fadeUp}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-4xl font-bold tracking-tight sm:text-6xl"
        >
          Train Smarter.{" "}
          <span className="text-gradient-brand">Get Personalized Workouts</span>{" "}
          Powered by AI.
        </motion.h1>

        <motion.p
          variants={fadeUp}
          transition={{ duration: 0.6, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-xl text-balance text-base text-muted-foreground sm:text-lg"
        >
          Athlyt builds your workout plan around your body, your goals, and your
          equipment — then adapts your nutrition and tracks every rep, so progress
          is something you can actually see.
        </motion.p>

        <motion.div
          variants={fadeUp}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <PrimaryButton asChild size="lg" className="animate-pulse-glow">
            <Link href="/register">Get Started</Link>
          </PrimaryButton>
          <Button asChild size="lg" variant="outline">
            <a href="#features">Explore Features</a>
          </Button>
        </motion.div>
      </motion.div>

      {/* Floating ambient stat cards — decorative, hidden on small screens
          where there isn't room for them without crowding the headline. */}
      <motion.div
        initial={{ opacity: 0, x: -20, y: -10 }}
        animate={{ opacity: 1, x: 0, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute left-[6%] top-[28%] hidden lg:block"
      >
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        >
          <GlassCard className="flex items-center gap-2.5 px-4 py-3">
            <Flame className="size-4 text-warning" />
            <div className="text-left">
              <p className="text-xs text-muted-foreground">Calories today</p>
              <p className="text-sm font-semibold">2,150 kcal</p>
            </div>
          </GlassCard>
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 20, y: -10 }}
        animate={{ opacity: 1, x: 0, y: 0 }}
        transition={{ duration: 0.6, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute right-[6%] top-[22%] hidden lg:block"
      >
        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
        >
          <GlassCard className="flex items-center gap-2.5 px-4 py-3">
            <TrendingUp className="size-4 text-success" />
            <div className="text-left">
              <p className="text-xs text-muted-foreground">Workout streak</p>
              <p className="text-sm font-semibold">12 days</p>
            </div>
          </GlassCard>
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 20, y: 10 }}
        animate={{ opacity: 1, x: 0, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute bottom-[18%] right-[10%] hidden lg:block"
      >
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        >
          <GlassCard className="flex items-center gap-2.5 px-4 py-3">
            <Activity className="size-4 text-primary" />
            <div className="text-left">
              <p className="text-xs text-muted-foreground">This week</p>
              <p className="text-sm font-semibold">5 / 5 workouts</p>
            </div>
          </GlassCard>
        </motion.div>
      </motion.div>
    </section>
  );
}
