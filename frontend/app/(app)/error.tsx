"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { AlertCircle } from "lucide-react";

import { PrimaryButton } from "@/components/shared/primary-button";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to error reporting service in production
    console.error(error);
  }, [error]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex min-h-[40vh] flex-col items-center justify-center gap-4 text-center"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertCircle className="h-6 w-6 text-destructive" />
      </div>
      <div>
        <h2 className="text-lg font-semibold">Something went wrong</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          An unexpected error occurred. Please try again.
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => window.location.href = "/dashboard"}>
          Go to dashboard
        </Button>
        <PrimaryButton onClick={reset}>Try again</PrimaryButton>
      </div>
    </motion.div>
  );
}
