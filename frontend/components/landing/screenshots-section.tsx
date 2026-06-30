"use client";

import { motion, type Variants } from "framer-motion";
import { BarChart3, Dumbbell, LayoutDashboard, UtensilsCrossed } from "lucide-react";
import Image from "next/image";

import { SectionHeader } from "@/components/shared/section-header";
import { TiltCard } from "@/components/shared/tilt-card";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Real screenshots for all four cards: Dashboard, Workout Planner,
 * Nutrition, and Analytics (Analytics uses the Progress page screenshot —
 * weight trend, streaks, personal records — which is what "Analytics"
 * refers to here).
 */
const SCREENSHOTS: Array<{
  icon: typeof LayoutDashboard;
  title: string;
  description: string;
  imageSrc?: string;
}> = [
  {
    icon: LayoutDashboard,
    title: "Dashboard",
    description: "Today's workout, weekly plan, and your key stats at a glance.",
    imageSrc: "/screenshots/dashboard.png",
  },
  {
    icon: Dumbbell,
    title: "Workout Planner",
    description: "A full weekly split with real exercises, sets, and reps.",
    imageSrc: "/screenshots/workouts.png",
  },
  {
    icon: UtensilsCrossed,
    title: "Nutrition",
    description: "Daily macro targets and a complete generated meal plan.",
    imageSrc: "/screenshots/nutrition.png",
  },
  {
    icon: BarChart3,
    title: "Analytics",
    description: "Weight trend, streaks, personal records, and activity heatmap.",
    imageSrc: "/screenshots/analytics.png",
  },
];

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] },
  },
};

export function ScreenshotsSection() {
  return (
    <section className="px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <SectionHeader
            title="See Athlyt in action"
            description="A quick look at the actual product."
            className="mb-10 flex-col items-start text-left"
          />
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-10%" }}
          variants={container}
          className="grid gap-4 sm:grid-cols-2"
        >
          {SCREENSHOTS.map((shot) => (
            <motion.div key={shot.title} variants={item}>
              <TiltCard intensity={5}>
                <Card className="overflow-hidden">
                  {shot.imageSrc ? (
                    <div className="relative aspect-video w-full">
                      <Image
                        src={shot.imageSrc}
                        alt={`${shot.title} screenshot`}
                        fill
                        className="object-cover object-top"
                        sizes="(max-width: 640px) 100vw, 50vw"
                      />
                    </div>
                  ) : (
                    <div className="flex aspect-video w-full items-center justify-center bg-gradient-to-br from-primary/10 via-accent/10 to-transparent">
                      <shot.icon className="size-12 text-muted-foreground/40" />
                    </div>
                  )}
                  <CardContent className="pt-4">
                    <h3 className="font-semibold">{shot.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{shot.description}</p>
                  </CardContent>
                </Card>
              </TiltCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
