"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api-client";
import type { HealthStatus } from "@/types/health";

type ConnectionState = "checking" | "connected" | "offline";

/**
 * Pings `GET /api/v1/health` on mount and renders the result.
 *
 * This exists in Project Setup specifically to prove the frontend and backend
 * are actually wired together — base URL, CORS, and the API contract all
 * working — rather than just trusting that two independently-scaffolded apps
 * will work together later.
 */
export function BackendStatus() {
  const [state, setState] = useState<ConnectionState>("checking");
  const [details, setDetails] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let cancelled = false;

    apiFetch<{ status: string; version: string; database: string }>("/health")
      .then((data) => {
        if (cancelled) return;
        setDetails(data as HealthStatus);
        setState("connected");
      })
      .catch(() => {
        if (cancelled) return;
        setState("offline");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "checking") {
    return <Badge variant="secondary">Checking backend…</Badge>;
  }

  if (state === "offline") {
    return <Badge variant="destructive">Backend offline</Badge>;
  }

  return (
    <Badge variant="default">
      Backend connected · v{details?.version} · DB {details?.database}
    </Badge>
  );
}
