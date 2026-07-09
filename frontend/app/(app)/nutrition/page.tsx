"use client";

import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Apple, Droplets, Flame, Zap } from "lucide-react";
import { toast } from "sonner";

import { SectionHeader } from "@/components/shared/section-header";
import { TiltCard } from "@/components/shared/tilt-card";
import { DashboardStatCard } from "@/components/shared/dashboard-stat-card";
import { PrimaryButton } from "@/components/shared/primary-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useNutritionPlan,
  useGenerateNutritionPlan,
  useTodayNutritionLog,
  useNutritionWeeklySummary,
  useLogNutrition,
} from "@/hooks/use-dashboard-data";
import type { NutritionMeal } from "@/types/user";

const MEAL_COLORS: Record<string, string> = {
  breakfast: "#6366f1",
  lunch: "#22c55e",
  dinner: "#f59e0b",
  snack: "#ec4899",
};

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

export default function NutritionPage() {
  const { data: plan, isLoading: planLoading, refetch: refetchPlan } = useNutritionPlan();
  const { data: todayLog } = useTodayNutritionLog();
  const { data: weekly, isLoading: weeklyLoading } = useNutritionWeeklySummary();
  const generateMutation = useGenerateNutritionPlan();
  const logMutation = useLogNutrition();

  const [calories, setCalories] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [water, setWater] = useState("");

  function handleGenerate() {
    generateMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success("Meal plan generated!");
        refetchPlan();
      },
      onError: () => toast.error("Failed to generate plan."),
    });
  }

  function handleLog() {
    if (!calories || !protein || !carbs || !fat) {
      toast.error("Fill in all macro fields.");
      return;
    }
    logMutation.mutate(
      {
        calories_consumed: parseInt(calories),
        protein_g: parseFloat(protein),
        carbs_g: parseFloat(carbs),
        fat_g: parseFloat(fat),
        water_ml: water ? parseInt(water) : 0,
      },
      {
        onSuccess: () => {
          toast.success("Nutrition logged!");
          setCalories("");
          setProtein("");
          setCarbs("");
          setFat("");
          setWater("");
        },
        onError: () => toast.error("Failed to log nutrition."),
      },
    );
  }

  const macroData: Array<{ name: string; value: number; color: string }> = plan
    ? [
        { name: "Protein", value: plan.target_protein_g, color: "#6366f1" },
        { name: "Carbs", value: plan.target_carbs_g, color: "#22c55e" },
        { name: "Fat", value: plan.target_fat_g, color: "#f59e0b" },
      ]
    : [];

  return (
    <motion.div variants={container} initial="hidden" animate="visible" className="space-y-8">
      <motion.div variants={item}>
        <SectionHeader
          title="Nutrition"
          description="Meal plan and daily macro tracking"
          action={
            <PrimaryButton
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
              className="shrink-0"
            >
              {plan ? "Regenerate" : "Generate"} plan
            </PrimaryButton>
          }
        />
      </motion.div>

      {/* Weekly summary */}
      <motion.div variants={item} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {weeklyLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)
        ) : (
          <>
            <TiltCard>
              <DashboardStatCard
                icon={Flame}
                label="Avg calories"
                value={weekly?.avg_calories ? `${weekly.avg_calories} kcal` : "—"}
              />
            </TiltCard>
            <TiltCard>
              <DashboardStatCard
                icon={Zap}
                label="Avg protein"
                value={weekly?.avg_protein_g ? `${weekly.avg_protein_g}g` : "—"}
              />
            </TiltCard>
            <TiltCard>
              <DashboardStatCard
                icon={Apple}
                label="Avg carbs"
                value={weekly?.avg_carbs_g ? `${weekly.avg_carbs_g}g` : "—"}
              />
            </TiltCard>
            <TiltCard>
              <DashboardStatCard
                icon={Droplets}
                label="Days logged"
                numericValue={weekly?.days_logged}
              />
            </TiltCard>
          </>
        )}
      </motion.div>

      {/* Meal plan */}
      <motion.div variants={item}>
        <SectionHeader title="Your meal plan" />
        {planLoading ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-36 rounded-xl" />
            ))}
          </div>
        ) : !plan ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
              <Apple className="h-10 w-10 text-muted-foreground/40" />
              <div>
                <p className="font-medium">No meal plan yet</p>
                <p className="text-sm text-muted-foreground">
                  Generate a personalised plan based on your goals
                </p>
              </div>
              <PrimaryButton onClick={handleGenerate} disabled={generateMutation.isPending}>
                Generate meal plan
              </PrimaryButton>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            {/* Macro donut */}
            <TiltCard intensity={4}>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Daily targets</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-center">
                    <ResponsiveContainer width={160} height={160}>
                      <PieChart>
                        <Pie
                          data={macroData}
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={70}
                          dataKey="value"
                          strokeWidth={0}
                        >
                          {macroData.map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                          ))}
                        </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "var(--background)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    labelFormatter={(label) => `${label}g`}
                  />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Calories</span>
                      <span className="font-semibold">{plan.target_calories} kcal</span>
                    </div>
                    {macroData.map((m) => (
                      <div key={m.name} className="flex items-center justify-between">
                        <span className="flex items-center gap-1.5 text-muted-foreground">
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{ background: m.color }}
                            aria-hidden
                          />
                          {m.name}
                        </span>
                        <span className="font-semibold">{m.value}g</span>
                      </div>
                    ))}
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Water</span>
                      <span className="font-semibold">{plan.target_water_ml} ml</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TiltCard>

            {/* Meal cards */}
            {plan.meals?.map((meal: NutritionMeal) => (
              <TiltCard key={meal.id} intensity={4}>
                <Card>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm capitalize">{meal.meal_type}</CardTitle>
                      <Badge
                        style={{
                          background: `${MEAL_COLORS[meal.meal_type]}20`,
                          color: MEAL_COLORS[meal.meal_type],
                          border: `1px solid ${MEAL_COLORS[meal.meal_type]}40`,
                        }}
                      >
                        {meal.calories} kcal
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <p className="text-sm font-medium">{meal.name}</p>
                    {meal.description && (
                      <p className="line-clamp-2 text-xs text-muted-foreground">
                        {meal.description}
                      </p>
                    )}
                    <div className="flex gap-3 pt-1 text-xs text-muted-foreground">
                      <span>P: {meal.protein_g}g</span>
                      <span>C: {meal.carbs_g}g</span>
                      <span>F: {meal.fat_g}g</span>
                    </div>
                  </CardContent>
                </Card>
              </TiltCard>
            ))}
          </div>
        )}
      </motion.div>

      {/* Log today */}
      <motion.div variants={item}>
        <SectionHeader
          title="Log today's intake"
          description={
            todayLog
              ? `Today: ${todayLog.calories_consumed} kcal logged`
              : "Nothing logged today yet"
          }
        />
        <Card>
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {[
                { id: "cal", label: "Calories (kcal)", value: calories, set: setCalories, placeholder: "1800" },
                { id: "prot", label: "Protein (g)", value: protein, set: setProtein, placeholder: "140" },
                { id: "carb", label: "Carbs (g)", value: carbs, set: setCarbs, placeholder: "180" },
                { id: "fat-g", label: "Fat (g)", value: fat, set: setFat, placeholder: "60" },
                { id: "water", label: "Water (ml)", value: water, set: setWater, placeholder: "2500" },
              ].map((f) => (
                <div key={f.id} className="space-y-1.5">
                  <Label htmlFor={f.id} className="text-xs">
                    {f.label}
                  </Label>
                  <Input
                    id={f.id}
                    type="number"
                    placeholder={f.placeholder}
                    value={f.value}
                    onChange={(e) => f.set(e.target.value)}
                    min="0"
                  />
                </div>
              ))}
            </div>
            <PrimaryButton
              onClick={handleLog}
              disabled={logMutation.isPending}
              className="w-full sm:w-auto"
            >
              {logMutation.isPending ? "Saving…" : "Log nutrition"}
            </PrimaryButton>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
