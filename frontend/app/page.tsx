"use client";

import Link from "next/link";

import { AmbientBackground } from "@/components/shared/ambient-background";
import { PrimaryButton } from "@/components/shared/primary-button";
import { ThemeToggle } from "@/components/theme-toggle";
import { FAQSection } from "@/components/landing/faq-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { HeroSection } from "@/components/landing/hero-section";
import { HowItWorksSection } from "@/components/landing/how-it-works-section";
import { LandingFooter } from "@/components/landing/landing-footer";
import { ScreenshotsSection } from "@/components/landing/screenshots-section";
import { TestimonialsSection } from "@/components/landing/testimonials-section";
import { TrustSection } from "@/components/landing/trust-section";

/**
 * The public marketing landing page — everything a visitor sees before
 * signing up. Composed of independent section components under
 * `components/landing/` so each section can be edited or reordered without
 * touching the others. Authentication itself (the actual login/register
 * forms, validators, and API calls) lives entirely in `app/(auth)/` and is
 * untouched by this page.
 */
export default function Home() {
  return (
    <main className="relative overflow-hidden">
      <AmbientBackground />

      {/* Sticky top bar — brand + theme toggle + sign-in shortcut */}
      <header className="glass-card sticky top-0 z-20 flex items-center justify-between rounded-none border-x-0 border-t-0 px-6 py-3">
        <Link href="/" className="text-lg font-bold tracking-tight">
          <span className="text-gradient-brand">Athlyt</span>
        </Link>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <PrimaryButton asChild size="sm">
            <Link href="/login">Sign in</Link>
          </PrimaryButton>
        </div>
      </header>

      <div className="relative z-10">
        <HeroSection />
        <TrustSection />
        <FeaturesSection />
        <HowItWorksSection />
        <ScreenshotsSection />
        <TestimonialsSection />
        <FAQSection />
        <LandingFooter />
      </div>
    </main>
  );
}
