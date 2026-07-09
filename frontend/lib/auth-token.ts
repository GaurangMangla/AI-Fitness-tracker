/**
 * Access token storage.
 *
 * Design decision: `localStorage`, not an httpOnly cookie. A cookie-based
 * session is the more security-hardened pattern (immune to XSS reading the
 * token directly), but it requires the Next.js server to participate in
 * auth (setting/reading cookies, a middleware-level redirect for protected
 * routes) — real, valid architecture, but more than a one-week, client-only
 * SPA-style app needs. The token is a single 7-day JWT (see the backend's
 * `core/config.py`), not a long-lived refresh token, which caps the damage
 * window of this tradeoff.
 *
 * Kept behind these three functions (not `localStorage.getItem` calls
 * scattered through the app) so the storage mechanism is a one-file change
 * later if this ever needs to move to cookies.
 */

const TOKEN_KEY = "athlyt_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}
