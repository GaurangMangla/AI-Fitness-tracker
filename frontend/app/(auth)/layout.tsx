"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { AuthBrandingPanel } from "@/components/auth/auth-branding-panel";
import { AmbientBackground } from "@/components/shared/ambient-background";

/**
 * Split-screen auth shell shared by /login and /register. The actual forms
 * (validation, mutations, API calls) live entirely inside each page's own
 * component — this layout only provides the surrounding chrome, so none of
 * the authentication logic itself is touched by this redesign.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative grid min-h-screen lg:grid-cols-2">
      <AmbientBackground />

      {/* Left: the actual form, passed in as `children` */}
      <main className="relative z-10 flex flex-col items-center justify-center gap-8 p-6">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <Link href="/" className="text-2xl font-bold tracking-tight">
            <span className="text-gradient-brand">Athlyt</span>
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm"
        >
          {children}
        </motion.div>
      </main>

      {/* Right: branding + benefits, hidden on mobile/tablet */}
      <AuthBrandingPanel />
    </div>
  );
}
