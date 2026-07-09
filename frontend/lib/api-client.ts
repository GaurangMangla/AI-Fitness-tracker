/**
 * Minimal typed fetch wrapper for calling the Athlyt backend.
 *
 * Deliberately stays a pure HTTP layer — it attaches the auth header and
 * extracts a clean error message, but it never redirects or clears the
 * stored token itself on a 401. That decision belongs to whatever called it
 * (e.g. `useCurrentUser` redirecting to `/login`), not to this shared
 * low-level client — keeping navigation side effects out of here is what
 * keeps this module reusable from anywhere, including outside React.
 */

import { getToken } from "@/lib/auth-token";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * The backend returns errors in one of two shapes (see the backend's
 * `core/exception_handlers.py` and FastAPI's own validation error format):
 * - `{"detail": "Some message"}` — our own AppException handler
 * - `{"detail": [{"msg": "...", "loc": [...]}, ...]}` — FastAPI's built-in
 *   request validation errors (422s Pydantic catches before our code runs)
 */
function extractErrorMessage(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return fallback;
  }
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (typeof first.msg === "string") return first.msg;
  }
  return fallback;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const fallback = `Request to ${path} failed with ${response.status}`;
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, extractErrorMessage(body, fallback));
  }

  return response.json() as Promise<T>;
}

/**
 * Like `apiFetch`, but for endpoints that return a raw file (e.g. the
 * progress report export) instead of JSON — a `Content-Type: application/json`
 * request header would be meaningless here, and the response body is read as
 * a `Blob`, not parsed. Filename is read off `Content-Disposition` so the
 * caller doesn't have to duplicate the backend's naming convention.
 */
export async function apiFetchBlob(
  path: string,
  init?: RequestInit,
): Promise<{ blob: Blob; filename: string | null }> {
  const token = getToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const fallback = `Request to ${path} failed with ${response.status}`;
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, extractErrorMessage(body, fallback));
  }

  const disposition = response.headers.get("content-disposition");
  const filenameMatch = disposition?.match(/filename="?([^"]+)"?/);

  return { blob: await response.blob(), filename: filenameMatch?.[1] ?? null };
}
