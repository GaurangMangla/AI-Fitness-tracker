"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { AmbientBackground } from "@/components/shared/ambient-background";
import { PrimaryButton } from "@/components/shared/primary-button";

export default function NotFound() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <AmbientBackground />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 space-y-4"
      >
        <p className="text-7xl font-bold text-gradient-brand">404</p>
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <PrimaryButton asChild>
          <Link href="/dashboard">Back to dashboard</Link>
        </PrimaryButton>
      </motion.div>
    </main>
  );
}
