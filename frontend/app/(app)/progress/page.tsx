"use client";

import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Scale, TrendingDown, TrendingUp, Moon, Download, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { DashboardStatCard } from "@/components/shared/dashboard-stat-card";
import { SectionHeader } from "@/components/shared/section-header";
import { TiltCard } from "@/components/shared/tilt-card";
import { PrimaryButton } from "@/components/shared/primary-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useProgressSummary,
  useProgressLogs,
  useLogProgress,
  useExportReport,
} from "@/hooks/use-dashboard-data";
import type { ProgressLog } from "@/types/user";

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

export default function ProgressPage() {
  const { data: summary, isLoading: summaryLoading } = useProgressSummary();
  const { data: logs, isLoading: logsLoading } = useProgressLogs();
  const logMutation = useLogProgress();
  const exportMutation = useExportReport();

  function handleExport(format: "csv" | "pdf") {
    exportMutation.mutate(format, {
      onError: () => toast.error("Failed to export report."),
    });
  }

  const [weight, setWeight] = useState("");
  const [sleep, setSleep] = useState("");
  const [bodyFat, setBodyFat] = useState("");

  function handleLog() {
    const body: { weight_kg?: number; body_fat_pct?: number; sleep_hours?: number } = {};
    if (weight) body.weight_kg = parseFloat(weight);
    if (sleep) body.sleep_hours = parseFloat(sleep);
    if (bodyFat) body.body_fat_pct = parseFloat(bodyFat);
    if (!Object.keys(body).length) {
      toast.error("Enter at least one value.");
      return;
    }
    logMutation.mutate(body, {
      onSuccess: () => {
        toast.success("Progress logged!");
        setWeight("");
        setSleep("");
        setBodyFat("");
      },
      onError: () => toast.error("Failed to log progress."),
    });
  }

  const chartData =
    logs
      ?.filter((l: ProgressLog) => l.weight_kg != null)
      .slice(0, 30)
      .reverse()
      .map((l: ProgressLog) => ({ date: l.log_date.slice(5), weight: l.weight_kg })) ?? [];

  const weightChange = summary?.weight_change_30d_kg;

  return (
    <motion.div variants={container} initial="hidden" animate="visible" className="space-y-8">
      <motion.div variants={item}>
        <SectionHeader title="Progress" description="Track your weight, measurements and sleep" />
      </motion.div>

      {/* Summary cards */}
      <motion.div variants={item} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)
        ) : (
          <>
            <TiltCard>
              <DashboardStatCard
                icon={Scale}
                label="Current weight"
                value={summary?.current_weight_kg ? `${summary.current_weight_kg} kg` : "—"}
              />
            </TiltCard>
            <TiltCard>
              <DashboardStatCard
                icon={Scale}
                label="Body fat"
                value={summary?.current_body_fat_pct ? `${summary.current_body_fat_pct}%` : "—"}
              />
            </TiltCard>
            <TiltCard>
              <DashboardStatCard
                icon={weightChange != null && weightChange < 0 ? TrendingDown : TrendingUp}
                label="30d change"
                value={
                  weightChange != null
                    ? `${weightChange > 0 ? "+" : ""}${weightChange} kg`
                    : "—"
                }
              />
            </TiltCard>
            <TiltCard>
              <DashboardStatCard
                icon={Moon}
                label="Sleep (last)"
                value={summary?.last_sleep_hours ? `${summary.last_sleep_hours}h` : "—"}
              />
            </TiltCard>
          </>
        )}
      </motion.div>

      {/* Weight chart */}
      <motion.div variants={item}>
        <SectionHeader title="Weight trend" />
        <Card>
          <CardContent className="pt-4">
            {logsLoading ? (
              <Skeleton className="h-48 w-full rounded-lg" />
            ) : chartData.length < 2 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                Log at least 2 weight entries to see your trend.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="currentColor" opacity={0.08} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--background)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                    }}
                    labelStyle={{ fontSize: 12 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="weight"
                    stroke="var(--color-primary)"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Log form */}
      <motion.div variants={item}>
        <SectionHeader title="Log today's stats" />
        <Card>
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="weight">Weight (kg)</Label>
                <Input
                  id="weight"
                  type="number"
                  placeholder="e.g. 80.5"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  step="0.1"
                  min="20"
                  max="300"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="body-fat">Body fat (%)</Label>
                <Input
                  id="body-fat"
                  type="number"
                  placeholder="e.g. 18.0"
                  value={bodyFat}
                  onChange={(e) => setBodyFat(e.target.value)}
                  step="0.1"
                  min="1"
                  max="70"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sleep">Sleep (hours)</Label>
                <Input
                  id="sleep"
                  type="number"
                  placeholder="e.g. 7.5"
                  value={sleep}
                  onChange={(e) => setSleep(e.target.value)}
                  step="0.5"
                  min="0"
                  max="24"
                />
              </div>
            </div>
            <PrimaryButton
              onClick={handleLog}
              disabled={logMutation.isPending}
              className="w-full sm:w-auto"
            >
              {logMutation.isPending ? "Saving…" : "Log progress"}
            </PrimaryButton>
          </CardContent>
        </Card>
      </motion.div>

      {/* History table */}
      <motion.div variants={item}>
        <SectionHeader
          title="Recent logs"
          action={
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport("csv")}
                disabled={exportMutation.isPending}
              >
                {exportMutation.isPending && exportMutation.variables === "csv" ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Download />
                )}
                CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport("pdf")}
                disabled={exportMutation.isPending}
              >
                {exportMutation.isPending && exportMutation.variables === "pdf" ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Download />
                )}
                PDF
              </Button>
            </div>
          }
        />
        {logsLoading ? (
          <Skeleton className="h-40 rounded-xl" />
        ) : !logs?.length ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No progress logs yet. Log your first entry above!
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 pr-4 font-medium">Date</th>
                      <th className="pb-2 pr-4 font-medium">Weight</th>
                      <th className="pb-2 pr-4 font-medium">Body fat</th>
                      <th className="pb-2 font-medium">Sleep</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.slice(0, 15).map((log: ProgressLog) => (
                      <tr
                        key={log.id}
                        className="border-b last:border-0 transition-colors hover:bg-muted/30"
                      >
                        <td className="py-2 pr-4">{log.log_date}</td>
                        <td className="py-2 pr-4">
                          {log.weight_kg != null ? `${log.weight_kg} kg` : "—"}
                        </td>
                        <td className="py-2 pr-4">
                          {log.body_fat_pct != null ? `${log.body_fat_pct}%` : "—"}
                        </td>
                        <td className="py-2">
                          {log.sleep_hours != null ? `${log.sleep_hours}h` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </motion.div>
    </motion.div>
  );
}
