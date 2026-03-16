import { supabase } from "./supabase";

const API_URL = process.env.EXPO_PUBLIC_API_URL || "https://api.execution.market";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  token?: string;
}

/**
 * Get the current Supabase session access token.
 * Returns null if no active session exists.
 */
async function getAuthToken(): Promise<string | null> {
  try {
    const { data } = await supabase.auth.getSession();
    return data?.session?.access_token ?? null;
  } catch {
    return null;
  }
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, token } = options;

  const requestHeaders: Record<string, string> = {
    ...headers,
  };

  if (body) {
    requestHeaders["Content-Type"] = "application/json";
  }

  // Explicit token takes priority; otherwise auto-attach Supabase session token
  if (token) {
    requestHeaders["Authorization"] = `Bearer ${token}`;
  } else if (!requestHeaders["Authorization"]) {
    const sessionToken = await getAuthToken();
    if (sessionToken) {
      requestHeaders["Authorization"] = `Bearer ${sessionToken}`;
    }
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    const msg = error.detail || error.message || `API error: ${response.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }

  return response.json();
}
