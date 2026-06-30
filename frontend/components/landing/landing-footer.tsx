import { Code2 } from "lucide-react";
import Link from "next/link";

const APP_VERSION = "0.1.0";

export function LandingFooter() {
  return (
    <footer className="border-t px-6 py-10">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-6 sm:flex-row sm:justify-between">
        <div className="flex flex-col items-center gap-1 sm:items-start">
          <span className="text-lg font-bold tracking-tight">
            <span className="text-gradient-brand">Athlyt</span>
          </span>
          <p className="text-xs text-muted-foreground">
            Train smarter. Progress faster. &middot; v{APP_VERSION}
          </p>
        </div>

        <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
          <a
            href="https://github.com/GaurangMangla/AI-Fitness-tracker"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 transition-colors hover:text-foreground"
          >
            <Code2 className="size-4" />
            GitHub
          </a>
          <a
            href="https://github.com/GaurangMangla/AI-Fitness-tracker#readme"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-foreground"
          >
            Documentation
          </a>
          <Link href="/privacy" className="transition-colors hover:text-foreground">
            Privacy
          </Link>
          <a
            href="mailto:hello@athlyt.dev"
            className="transition-colors hover:text-foreground"
          >
            Contact
          </a>
        </nav>
      </div>

      <p className="mt-8 text-center text-xs text-muted-foreground">
        &copy; {new Date().getFullYear()} Athlyt. All rights reserved.
      </p>
    </footer>
  );
}
