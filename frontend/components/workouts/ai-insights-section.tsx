"use client";

import { motion, type Variants } from "framer-motion";
import { CheckCircle2 } from "lucide-react";

import { SectionHeader } from "@/components/shared/section-header";
import { Card, CardContent } from "@/components/ui/card";
import type { GeneratedWorkoutPlanResponse } from "@/types/user";

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
};
const item: Variants = {
  hidden: { opacity: 0, x: -12 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

/**
 * Builds 4-6 insight sentences entirely from the actual profile data and
 * recommendation returned by the backend — no split name, goal, or any
 * other value is ever hardcoded here. Every sentence is a template filled
 * in with real fields from `plan.explanation` / `plan.split_name`, so this
 * produces sensible copy for *any* split or profile combination the
 * backend could ever return, including future splits that don't exist yet.
 *
 * Works identically whether `plan.engine` is "ml" or "rule" — the insights
 * describe the *profile reasoning*, not which engine produced the result,
 * so the Rule Engine fallback gets the exact same quality of explanation.
 */
function buildInsights(plan: GeneratedWorkoutPlanResponse): string[] {
  const explanation = plan.explanation;
  if (!explanation) return [];

  const { goal, experience, days_per_week, equipment } = explanation;
  const splitName = plan.split_name;
  const insights: string[] = [];

  insights.push(
    `Your primary goal is ${goal}, so ${splitName} was chosen to support that specific outcome.`
  );

  insights.push(
    `Training ${days_per_week} day${days_per_week === 1 ? "" : "s"} per week provides a schedule that fits well with a ${splitName} routine.`
  );

  const experienceLower = experience.toLowerCase();
  if (experienceLower === "beginner") {
    insights.push(
      `As a Beginner, this plan favors fundamental movements and manageable volume so you can build a solid base safely.`
    );
  } else if (experienceLower === "intermediate") {
    insights.push(
      `Your Intermediate experience level indicates you can safely handle higher training volume and more varied exercise selection.`
    );
  } else {
    insights.push(
      `Your Advanced experience level means this plan can push higher intensity and volume than a beginner or intermediate routine would.`
    );
  }

  const equipmentLower = equipment.toLowerCase();
  if (equipmentLower.includes("gym")) {
    insights.push(
      `Since you have access to a full gym, the plan includes a wider variety of compound and isolation exercises.`
    );
  } else if (equipmentLower.includes("no equipment")) {
    insights.push(
      `With no equipment required, every exercise in this plan uses bodyweight movements you can do anywhere.`
    );
  } else {
    insights.push(
      `Based on your available equipment (${equipment}), exercises were selected to make the most of what you have.`
    );
  }

  insights.push(
    `${splitName} balances muscle group recovery with a consistent weekly training frequency, matching your ${days_per_week}-day schedule.`
  );

  if (plan.engine === "ml" && plan.confidence !== null) {
    insights.push(
      `Our recommendation model matched your profile to ${splitName} with ${Math.round(plan.confidence * 100)}% confidence, based on patterns learned from real training data.`
    );
  }

  // Cap at 6, per spec — the goal/days/equipment/experience/split-summary
  // insights above are the fixed core (5), with the ML-confidence insight
  // as an optional 6th only when a genuine ML prediction produced this plan.
  return insights.slice(0, 6);
}

export function AIInsightsSection({ plan }: { plan: GeneratedWorkoutPlanResponse }) {
  const insights = buildInsights(plan);

  if (insights.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10%" }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <SectionHeader title="🧠 Why this workout split?" />

      <Card>
        <CardContent className="py-2">
          <motion.ul
            variants={container}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-10%" }}
            className="divide-y divide-border"
          >
            {insights.map((insight) => (
              <motion.li
                key={insight}
                variants={item}
                className="flex items-start gap-3 py-3 first:pt-4 last:pb-4"
              >
                <CheckCircle2
                  className="mt-0.5 size-4 shrink-0 text-success sm:size-5"
                  aria-hidden
                />
                <span className="text-sm text-foreground/90 sm:text-base">{insight}</span>
              </motion.li>
            ))}
          </motion.ul>
        </CardContent>
      </Card>
    </motion.div>
  );
}
