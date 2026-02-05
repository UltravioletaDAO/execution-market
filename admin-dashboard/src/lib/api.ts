/**
 * Centralized Admin API client.
 * Uses X-Admin-Key header (NOT query params) for authentication.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

export { API_BASE }

/**
 * Make an authenticated admin API request.
 * Admin key is sent via X-Admin-Key header, never as a query param.
 */
export async function adminFetch(
  path: string,
  adminKey: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers)
  headers.set('X-Admin-Key', adminKey)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })
}

/**
 * GET request with JSON response.
 */
export async function adminGet<T = any>(
  path: string,
  adminKey: string,
  params?: Record<string, string>,
): Promise<T> {
  const url = params
    ? `${path}?${new URLSearchParams(params)}`
    : path

  const response = await adminFetch(url, adminKey)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || error.message || `Request failed: ${response.status}`)
  }
  return response.json()
}

/**
 * PUT request with JSON body and response.
 */
export async function adminPut<T = any>(
  path: string,
  adminKey: string,
  body: unknown,
): Promise<T> {
  const response = await adminFetch(path, adminKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || error.message || `Request failed: ${response.status}`)
  }
  return response.json()
}

/**
 * POST request with JSON body and response.
 */
export async function adminPost<T = any>(
  path: string,
  adminKey: string,
  body: unknown,
): Promise<T> {
  const response = await adminFetch(path, adminKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || error.message || `Request failed: ${response.status}`)
  }
  return response.json()
}
