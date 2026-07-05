"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/**
 * One `QueryClient` per browser session, created inside `useState` (not at
 * module scope) so it isn't shared across requests during server rendering —
 * the standard pattern from TanStack Query's own Next.js App Router docs.
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // A 401 means "not logged in", not "transient network blip" —
            // retrying it just delays the redirect to /login for no benefit.
            retry: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
