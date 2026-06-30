"use client";

import { motion, type Variants } from "framer-motion";
import { Bot, CheckCircle2, LineChart, ShieldCheck, Sparkles, UtensilsCrossed } from "lucide-react";

import { DashboardStatCard } from "@/components/shared/dashboard-stat-card";
import { TiltCard } from "@/components/shared/tilt-card";

/**
 * Quick-scan trust signals right under the hero — reuses the same
 * `DashboardStatCard` (with its built-in count-up animation) the real
 * authenticated dashboard uses, so a visitor gets a preview of the app's
 * actual visual language before ever signing in.
 */
const STATS = [
  { icon: Sparkles, label: "Personalized Plans", value: "1-on-1" },
  { icon: Bot, label: "AI Recommendations", value: "Built-in" },
  { icon: UtensilsCrossed, label: "Nutrition Planning", numericValue: undefined, value: "Included" },
  { icon: LineChart, label: "Progress Tracking", value: "Real-time" },
  { icon: CheckCircle2, label: "Automated Tests", numericValue: 220, suffix: "+" },
  { icon: ShieldCheck, label: "Secure Auth", value: "JWT" },
];

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

export function TrustSection() {
  return (
    <section className="px-6 py-16">
      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-10%" }}
        variants={container}
        className="mx-auto grid max-w-5xl grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
      >
        {STATS.map((stat) => (
          <motion.div key={stat.label} variants={item}>
            <TiltCard intensity={4}>
              <DashboardStatCard
                icon={stat.icon}
                label={stat.label}
                value={stat.value}
                numericValue={stat.numericValue}
                suffix={stat.suffix}
                className="bg-card"
              />
            </TiltCard>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
