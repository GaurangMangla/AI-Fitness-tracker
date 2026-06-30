import Link from "next/link";

import { AmbientBackground } from "@/components/shared/ambient-background";

export const metadata = {
  title: "Privacy — Athlyt",
};

export default function PrivacyPage() {
  return (
    <main className="relative min-h-screen px-6 py-16">
      <AmbientBackground />
      <div className="relative z-10 mx-auto max-w-2xl space-y-6">
        <Link href="/" className="text-lg font-bold tracking-tight">
          <span className="text-gradient-brand">Athlyt</span>
        </Link>

        <h1 className="text-3xl font-bold tracking-tight">Privacy</h1>

        <div className="space-y-4 text-sm text-muted-foreground">
          <p>
            Athlyt is a portfolio project, not a commercial product. Account
            data (email, hashed password, and the fitness profile you provide)
            is stored to power the app&apos;s features — generating your
            workout and nutrition plans, and tracking your logged progress.
          </p>
          <p>
            Authentication uses JWT tokens; passwords are never stored in
            plain text. Your data is not sold, shared with third parties, or
            used for anything beyond running the application for you.
          </p>
          <p>
            Since this is a portfolio project rather than a production
            business, there is no dedicated support team or formal data
            request process yet — for any question about your data, use the
            contact link in the footer.
          </p>
        </div>

        <Link
          href="/"
          className="inline-block text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          &larr; Back to home
        </Link>
      </div>
    </main>
  );
}
