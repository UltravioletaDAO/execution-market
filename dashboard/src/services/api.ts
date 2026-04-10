/**
 * Execution Market API Client
 *
 * Base API client using native fetch with authentication
 * and error handling middleware.
 *
 * Note: Most API operations use the Supabase client directly.
 * This API client is for custom REST endpoints if needed.
 */

import type { ApiError } from './types'

// ============== CONFIGURATION ==============

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'
const API_TIMEOUT = 30000 // 30 seconds

// ============== AUTH HELPERS ==============

/**
 * Get authentication token from storage
 */
function getAuthToken(): string | null {
  // Check for Supabase session token
  // Derive the Supabase project ref from the configured URL for the localStorage key
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
  const projectRef = new URL(supabaseUrl).hostname.split('.')[0] || 'localhost'
  const supabaseSession = localStorage.getItem(`sb-${projectRef}-auth-token`)
  if (supabaseSession) {
    try {
      const parsed = JSON.parse(supabaseSession)
      return parsed?.access_token || null
    } catch {
      // Invalid JSON, ignore
    }
  }

  // Check for custom JWT token
  return localStorage.getItem('em_auth_token')
}

/**
 * Set authentication token.
 *
 * SECURITY NOTE (FE-009): Auth tokens in localStorage are vulnerable to XSS
 * exfiltration. CSP script-src policy is the primary defense. Phase 4 should
 * migrate to httpOnly cookies set by the backend for token storage.
 */
export function setAuthToken(token: string): void {
  localStorage.setItem('em_auth_token', token)
}

/**
 * Clear authentication token
 */
export function clearAuthToken(): void {
  localStorage.removeItem('em_auth_token')
}

// ============== REQUEST HELPERS ==============

/**
 * Generate unique request ID
 */
function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

/**
 * Build URL with query parameters
 */
export function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`

  if (!params) return url

  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      if (Array.isArray(value)) {
        value.forEach((v) => searchParams.append(key, String(v)))
      } else {
        searchParams.append(key, String(value))
      }
    }
  })

  const queryString = searchParams.toString()
  return queryString ? `${url}?${queryString}` : url
}

/**
 * Get default headers for requests
 */
function getHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Client-Info': 'execution-market-dashboard',
    'X-Request-ID': generateRequestId(),
  }

  // Add API key if configured
  const apiKey = import.meta.env.VITE_API_KEY
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`
    headers['X-API-Key'] = apiKey
  }

  // Add JWT token if available and no API key is configured.
  // Agent mutation endpoints expect API-key bearer auth.
  const token = getAuthToken()
  if (token && !apiKey) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return headers
}

// ============== ERROR HANDLING ==============

/**
 * Get default error message for HTTP status
 */
function getDefaultErrorMessage(status: number): string {
  const messages: Record<number, string> = {
    400: 'Invalid request. Please check your input.',
    401: 'Authentication required. Please sign in.',
    403: 'You do not have permission to perform this action.',
    404: 'The requested resource was not found.',
    409: 'Conflict with existing data.',
    422: 'Validation error. Please check your input.',
    429: 'Too many requests. Please try again later.',
    500: 'Server error. Please try again later.',
    502: 'Service temporarily unavailable.',
    503: 'Service under maintenance. Please try again later.',
  }

  return messages[status] || `Error: ${status}`
}

/**
 * Handle API errors
 */
async function handleError(response: Response): Promise<never> {
  let apiError: ApiError

  try {
    const data = await response.json()
    apiError = {
      message: data?.message || getDefaultErrorMessage(response.status),
      code: data?.code || `HTTP_${response.status}`,
      status: response.status,
      details: data?.details,
    }
  } catch {
    apiError = {
      message: getDefaultErrorMessage(response.status),
      code: `HTTP_${response.status}`,
      status: response.status,
    }
  }

  // Handle specific status codes
  if (response.status === 401) {
    clearAuthToken()
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  } else if (response.status === 403) {
    window.dispatchEvent(new CustomEvent('auth:forbidden'))
  }

  console.error('[API] Error:', apiError)
  throw apiError
}

// ============== UTILITIES ==============

/**
 * Convert snake_case object keys to camelCase
 */
export function toCamelCase<T>(obj: unknown): T {
  if (obj === null || typeof obj !== 'object') {
    return obj as T
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => toCamelCase(item)) as T
  }

  const converted: Record<string, unknown> = {}

  Object.entries(obj as Record<string, unknown>).forEach(([key, value]) => {
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
    converted[camelKey] = toCamelCase(value)
  })

  return converted as T
}

/**
 * Convert camelCase object keys to snake_case
 */
export function toSnakeCase<T>(obj: unknown): T {
  if (obj === null || typeof obj !== 'object') {
    return obj as T
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => toSnakeCase(item)) as T
  }

  const converted: Record<string, unknown> = {}

  Object.entries(obj as Record<string, unknown>).forEach(([key, value]) => {
    const snakeKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
    converted[snakeKey] = toSnakeCase(value)
  })

  return converted as T
}

// ============== FETCH WITH TIMEOUT ==============

/**
 * Fetch with timeout support
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeout: number = API_TIMEOUT
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    return response
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw {
        message: 'Request timed out',
        code: 'TIMEOUT',
      } as ApiError
    }
    throw {
      message: error instanceof Error ? error.message : 'Network error',
      code: 'NETWORK_ERROR',
    } as ApiError
  } finally {
    clearTimeout(timeoutId)
  }
}

// ============== API METHODS ==============

/**
 * Make an API request
 */
async function request<T>(
  method: string,
  path: string,
  data?: unknown
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`

  const options: RequestInit = {
    method,
    headers: getHeaders(),
  }

  if (data && method !== 'GET') {
    options.body = JSON.stringify(toSnakeCase(data))
  }

  const response = await fetchWithTimeout(url, options)

  if (!response.ok) {
    await handleError(response)
  }

  // Handle empty responses
  const text = await response.text()
  if (!text) {
    return {} as T
  }

  try {
    return JSON.parse(text) as T
  } catch {
    return text as T
  }
}

/**
 * API client object for direct access
 */
export const api = {
  get: <T>(path: string, params?: Record<string, unknown>) =>
    request<T>('GET', buildUrl(path, params)),
  post: <T>(path: string, data?: unknown) =>
    request<T>('POST', path, data),
  put: <T>(path: string, data?: unknown) =>
    request<T>('PUT', path, data),
  patch: <T>(path: string, data?: unknown) =>
    request<T>('PATCH', path, data),
  delete: <T>(path: string) =>
    request<T>('DELETE', path),
}

/**
 * Type-safe GET request
 */
export async function get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  return api.get<T>(path, params)
}

/**
 * Type-safe POST request
 */
export async function post<T, D = unknown>(path: string, data?: D): Promise<T> {
  return api.post<T>(path, data)
}

/**
 * Type-safe PUT request
 */
export async function put<T, D = unknown>(path: string, data?: D): Promise<T> {
  return api.put<T>(path, data)
}

/**
 * Type-safe PATCH request
 */
export async function patch<T, D = unknown>(path: string, data?: D): Promise<T> {
  return api.patch<T>(path, data)
}

/**
 * Type-safe DELETE request
 */
export async function del<T>(path: string): Promise<T> {
  return api.delete<T>(path)
}
