"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

/**
 * Thin wrapper around next-themes' provider.
 *
 * It's a separate client component (rather than using next-themes directly in
 * `app/layout.tsx`) only because `layout.tsx` is a server component — wrapping
 * the client-only provider here keeps that boundary clean and is the pattern
 * next-themes' own docs recommend for the App Router.
 */
export function ThemeProvider({
  children,
  ...props
}: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
