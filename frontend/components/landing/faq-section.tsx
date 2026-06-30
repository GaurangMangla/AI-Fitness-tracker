"use client";

import { motion } from "framer-motion";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { SectionHeader } from "@/components/shared/section-header";

const FAQS = [
  {
    question: "How does Athlyt decide my workout split?",
    answer:
      "A rule-based recommendation engine looks at your goal, experience level, available equipment, and how many days a week you want to train, then picks the split (like Push/Pull/Legs, Upper/Lower, or a bodyweight-only plan) that actually fits. It's designed so a machine-learning model can take over the same decision later without changing anything else about how your plan is built.",
  },
  {
    question: "Does Athlyt create a diet plan too?",
    answer:
      "Yes — once your profile is set up, Athlyt calculates a daily calorie and macro target based on your body and goal, then generates a full meal plan (breakfast, lunch, dinner, and a snack) with real meals matching your diet preference, whether that's vegetarian, vegan, or non-vegetarian.",
  },
  {
    question: "Is my data kept private?",
    answer:
      "Your account is protected with JWT-based authentication and industry-standard password hashing. Your workout history, nutrition logs, and profile information are only ever visible to you through your own authenticated session.",
  },
  {
    question: "Is the AI actually a real model, or just marketing?",
    answer:
      "Today's recommendation engine is a transparent, rule-based system — every decision can be explained. A real machine-learning model has already been trained on 100,000 synthetic profiles and is being evaluated for integration, following the exact same architecture the rule engine uses today, so switching over won't change anything else about how the app works.",
  },
  {
    question: "How much does Athlyt cost?",
    answer:
      "Athlyt is currently a portfolio project, not a commercial product — there's no pricing or paid tier. It's built to demonstrate full production-quality engineering: real authentication, a real database, tested APIs, and a deployed live app.",
  },
];

export function FAQSection() {
  return (
    <section className="px-6 py-20">
      <div className="mx-auto max-w-3xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <SectionHeader
            title="Frequently asked questions"
            className="mb-8 flex-col items-start text-left"
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="glass-card rounded-xl px-6"
        >
          <Accordion type="single" collapsible className="w-full">
            {FAQS.map((faq, i) => (
              <AccordionItem key={faq.question} value={`faq-${i}`}>
                <AccordionTrigger>{faq.question}</AccordionTrigger>
                <AccordionContent className="text-muted-foreground">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </motion.div>
      </div>
    </section>
  );
}
