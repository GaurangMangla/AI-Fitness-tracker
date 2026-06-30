"use client";

import { motion } from "framer-motion";
import { ClipboardList, Rocket, TrendingUp, UserPlus } from "lucide-react";
import { Fragment } from "react";

import { SectionHeader } from "@/components/shared/section-header";

const STEPS = [
  {
    icon: UserPlus,
    title: "Create Account",
    description: "Sign up in seconds — just an email and password to get started.",
  },
  {
    icon: ClipboardList,
    title: "Complete Fitness Profile",
    description: "Tell us your goal, experience, equipment, and schedule.",
  },
  {
    icon: Rocket,
    title: "Receive Personalized Plan",
    description: "Get a full weekly workout split and nutrition plan, generated for you.",
  },
  {
    icon: TrendingUp,
    title: "Track Progress",
    description: "Log every session and watch your streaks, weight, and stats add up.",
  },
];

export function HowItWorksSection() {
  return (
    <section className="px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="text-center"
        >
          <SectionHeader
            title="How it works"
            description="From sign-up to your first tracked workout, in four steps."
            className="mb-12 flex-col items-center text-center"
          />
        </motion.div>

        <div className="flex flex-col items-stretch gap-0 lg:flex-row lg:items-start">
          {STEPS.map((step, index) => (
            <Fragment key={step.title}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-10%" }}
                transition={{ duration: 0.5, delay: index * 0.12, ease: [0.16, 1, 0.3, 1] }}
                className="flex flex-1 flex-col items-center gap-3 px-4 text-center"
              >
                <div className="relative flex size-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <step.icon className="size-6" />
                  <span className="absolute -right-1 -top-1 flex size-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                    {index + 1}
                  </span>
                </div>
                <h3 className="font-semibold">{step.title}</h3>
                <p className="max-w-[200px] text-sm text-muted-foreground">{step.description}</p>
              </motion.div>

              {/* Animated connector — vertical line on mobile, horizontal on desktop */}
              {index < STEPS.length - 1 && (
                <motion.div
                  initial={{ scaleY: 0, scaleX: 0 }}
                  whileInView={{ scaleY: 1, scaleX: 1 }}
                  viewport={{ once: true, margin: "-10%" }}
                  transition={{ duration: 0.4, delay: index * 0.12 + 0.2, ease: "easeOut" }}
                  className="mx-auto my-2 h-8 w-px shrink-0 origin-top bg-gradient-to-b from-primary/40 to-primary/0 lg:my-6 lg:h-px lg:w-8 lg:origin-left lg:bg-gradient-to-r"
                  aria-hidden
                />
              )}
            </Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}
