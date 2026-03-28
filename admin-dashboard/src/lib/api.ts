/**
 * Centralized Admin API client.
 * Uses X-Admin-Key header (NOT query params) for authentication.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

const DEFAULT_TIMEOUT_MS = 30_000

export { API_BASE }

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------

/** Base error for all admin API failures. */
export class AdminApiError extends Error {
  public readonly status: number | undefined
  public readonly detail: string | undefined

  constructor(message: string, status?: number, detail?: string) {
    super(message)
    this.name = 'AdminApiError'
    this.status = status
    this.detail = detail
  }
}

/** 401 or 403 — caller should redirect to login. */
export class AuthError extends AdminApiError {
  constructor(message: string, status: number, detail?: string) {
    super(message, status, detail)
    this.name = 'AuthError'
  }
}

/** 503 — server is in maintenance. */
export class MaintenanceError extends AdminApiError {
  constructor(message: string, detail?: string) {
    super(message, 503, detail)
    this.name = 'MaintenanceError'
  }
}

/** Network-level failure (timeout, DNS, offline, etc.). */
export class ConnectionError extends AdminApiError {
  constructor(message: string) {
    super(message, undefined, undefined)
    this.name = 'ConnectionError'
  }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Inspect the response and throw a typed error when appropriate.
 * Returns the response untouched when status is 2xx.
 */
async function handleResponseError(response: Response): Promise<Response> {
  if (response.ok) return response

  const body = await response.json().catch(() => ({}))
  const detail = body.detail || body.message || undefined
  const msg = detail || `Request failed: ${response.status}`

  if (response.status === 401 || response.status === 403) {
    throw new AuthError(msg, response.status, detail)
  }

  if (response.status === 503) {
    throw new MaintenanceError(msg, detail)
  }

  throw new AdminApiError(msg, response.status, detail)
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Make an authenticated admin API request.
 * Admin key is sent via X-Admin-Key header, never as a query param.
 * Includes a 30-second timeout by default.
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

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      signal: options.signal ?? controller.signal,
    })
    return response
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ConnectionError(`Request timed out after ${DEFAULT_TIMEOUT_MS / 1000}s`)
    }
    if (err instanceof TypeError) {
      // fetch throws TypeError for network failures (offline, DNS, CORS, etc.)
      throw new ConnectionError(err.message || 'Network error')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
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
  await handleResponseError(response)
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
  await handleResponseError(response)
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
  await handleResponseError(response)
  return response.json()
}

/**
 * DELETE request with optional JSON body and response.
 */
export async function adminDelete<T = any>(
  path: string,
  adminKey: string,
  body?: unknown,
): Promise<T> {
  const response = await adminFetch(path, adminKey, {
    method: 'DELETE',
    ...(body !== undefined && { body: JSON.stringify(body) }),
  })
  await handleResponseError(response)
  return response.json()
}
