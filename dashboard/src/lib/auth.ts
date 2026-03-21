/**
 * Auth helpers for attaching Supabase session tokens to API requests.
 */
import { supabase } from './supabase'

/**
 * Get the current Supabase session access token.
 * Returns null if no active session exists.
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    const { data } = await supabase.auth.getSession()
    return data?.session?.access_token ?? null
  } catch {
    return null
  }
}

/**
 * Build headers that include the Supabase auth token (if available)
 * merged with any additional headers provided.
 */
export async function buildAuthHeaders(
  extra: Record<string, string> = {}
): Promise<Record<string, string>> {
  const headers: Record<string, string> = { ...extra }
  const token = await getAuthToken()
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}
