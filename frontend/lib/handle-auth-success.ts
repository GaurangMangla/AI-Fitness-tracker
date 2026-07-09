import type { QueryClient } from "@tanstack/react-query";

import { CURRENT_USER_QUERY_KEY } from "@/hooks/use-current-user";
import { setToken } from "@/lib/auth-token";
import type { AuthResponse } from "@/types/user";

interface MinimalRouter {
  push: (href: string) => void;
}

/**
 * Stores the token, seeds the `currentUser` query cache directly from the
 * response we already have (cheaper and more immediate than letting
 * `useCurrentUser` refetch from scratch), and routes to onboarding or the
 * dashboard depending on whether a profile already exists.
 */
export function handleAuthSuccess(
  data: AuthResponse,
  queryClient: QueryClient,
  router: MinimalRouter,
): void {
  setToken(data.access_token);
  queryClient.setQueryData(CURRENT_USER_QUERY_KEY, data.user);
  router.push(data.user.profile ? "/dashboard" : "/onboarding");
}
