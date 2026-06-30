"use client";

import { motion, type Variants } from "framer-motion";
import { Star } from "lucide-react";

import { SectionHeader } from "@/components/shared/section-header";
import { TiltCard } from "@/components/shared/tilt-card";
import { Card, CardContent } from "@/components/ui/card";

/**
 * PLACEHOLDER TESTIMONIALS — these are illustrative, not real user quotes.
 * Replace with actual testimonials once the app has real users willing to
 * be quoted. Each entry's `name`/`role` are generic placeholders too —
 * swap all three fields together when real testimonials are available.
 */
const TESTIMONIALS = [
  {
    name: "Aisha K.",
    role: "Beginner, 3 months in",
    quote:
      "I had no idea where to start with a gym routine. Athlyt built me a plan around the one dumbbell set I own and it's actually been doable.",
  },
  {
    name: "Marcus T.",
    role: "Intermediate lifter",
    quote:
      "The push/pull/legs split it recommended matched almost exactly what I'd have picked myself — just faster, and with the exercises already picked out.",
  },
  {
    name: "Priya N.",
    role: "Working parent",
    quote:
      "Being able to log a session in under a minute is what actually keeps me consistent. The streak tracker doesn't hurt either.",
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

export function TestimonialsSection() {
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
            title="What people are saying"
            description="Illustrative feedback — real testimonials coming as Athlyt gets real users."
            className="mb-10 flex-col items-start text-left"
          />
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-10%" }}
          variants={container}
          className="grid gap-4 sm:grid-cols-3"
        >
          {TESTIMONIALS.map((t) => (
            <motion.div key={t.name} variants={item}>
              <TiltCard intensity={4}>
                <Card className="h-full">
                  <CardContent className="flex h-full flex-col gap-3 pt-6">
                    <div className="flex gap-0.5 text-warning">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star key={i} className="size-3.5 fill-current" />
                      ))}
                    </div>
                    <p className="flex-1 text-sm text-muted-foreground">
                      &ldquo;{t.quote}&rdquo;
                    </p>
                    <div className="pt-2">
                      <p className="text-sm font-semibold">{t.name}</p>
                      <p className="text-xs text-muted-foreground">{t.role}</p>
                    </div>
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
