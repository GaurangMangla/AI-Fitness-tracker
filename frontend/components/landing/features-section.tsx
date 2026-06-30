"use client";

import { motion, type Variants } from "framer-motion";
import {
  BarChart3,
  Bot,
  Dumbbell,
  Moon,
  TrendingUp,
  UtensilsCrossed,
} from "lucide-react";

import { SectionHeader } from "@/components/shared/section-header";
import { TiltCard } from "@/components/shared/tilt-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Dumbbell,
    title: "Personalized Workout Plans",
    description:
      "A full weekly training split built around your goal, experience level, and whatever equipment you actually have — not a generic template.",
  },
  {
    icon: Bot,
    title: "AI-Powered Recommendations",
    description:
      "A rule-driven recommendation engine picks the right split for you today, with a machine-learning model designed to take over as more training data comes in.",
  },
  {
    icon: TrendingUp,
    title: "Progress Tracking",
    description:
      "Start, pause, and finish real workout sessions. Every set logged, every streak counted, every session saved to your history.",
  },
  {
    icon: UtensilsCrossed,
    title: "Nutrition Management",
    description:
      "Daily calorie and macro targets generated from your body and goals, with a full meal plan and intake logging to match.",
  },
  {
    icon: BarChart3,
    title: "Analytics Dashboard",
    description:
      "Weight trend, workout streaks, personal records, and a full activity heatmap — your progress, visualized.",
  },
  {
    icon: Moon,
    title: "Dark Mode",
    description:
      "A carefully tuned dark theme, not just an inverted color scheme — built in from day one, not bolted on after.",
  },
];

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

export function FeaturesSection() {
  return (
    <section id="features" className="px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <SectionHeader
            title="Everything you need to actually train smarter"
            description="Not just a workout log — a full coaching loop, from plan to plate to progress."
            className="mb-10 flex-col items-start text-left sm:mb-12"
          />
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-10%" }}
          variants={container}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {FEATURES.map((feature) => (
            <motion.div key={feature.title} variants={item}>
              <TiltCard intensity={6}>
                <Card className="h-full transition-shadow duration-200 hover:shadow-lg hover:shadow-primary/10">
                  <CardHeader>
                    <div className="mb-2 flex size-11 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform duration-200 group-hover:scale-110">
                      <feature.icon className="size-5" />
                    </div>
                    <CardTitle className="text-base">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
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
