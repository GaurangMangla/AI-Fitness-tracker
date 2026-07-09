"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import { getToken } from "@/lib/auth-token";
import type { UserResponse } from "@/types/user";

export const CURRENT_USER_QUERY_KEY = ["currentUser"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: () => apiFetch<UserResponse>("/users/me"),
    // No token, no point calling an endpoint that will 401 — `enabled` keeps
    // the query idle until one exists (e.g. right after login sets it).
    enabled: Boolean(getToken()),
  });
}
