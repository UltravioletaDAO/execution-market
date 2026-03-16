const API_URL = import.meta.env.VITE_API_URL || "https://api.execution.market";

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string>;
  headers?: Record<string, string>;
}

export async function apiRequest<T>(endpoint: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, headers = {} } = opts;

  let url = `${API_URL}${endpoint}`;
  if (params) {
    const qs = new URLSearchParams(params).toString();
    url += `?${qs}`;
  }

  const res = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// Convenience methods
export const api = {
  get: <T>(path: string, params?: Record<string, string>) =>
    apiRequest<T>(path, { params }),
  post: <T>(path: string, body: unknown) =>
    apiRequest<T>(path, { method: "POST", body }),
};
