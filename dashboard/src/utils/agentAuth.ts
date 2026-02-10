/**
 * Agent Authentication Utilities
 *
 * Helper functions for managing agent session state.
 * Separated from AgentLogin component to avoid react-refresh warnings.
 */

import { setAuthToken } from '../services/api'

// --------------------------------------------------------------------------
// Constants
// --------------------------------------------------------------------------

const AGENT_JWT_KEY = 'em_agent_jwt'
const AGENT_ID_KEY = 'em_agent_id'
const AGENT_TIER_KEY = 'em_agent_tier'

// --------------------------------------------------------------------------
// Public API
// --------------------------------------------------------------------------

/** Get the stored agent JWT, or null if not present */
export function getAgentToken(): string | null {
  return localStorage.getItem(AGENT_JWT_KEY)
}

/** Check if an agent is currently logged in (has a non-expired JWT) */
export function isAgentLoggedIn(): boolean {
  const token = getAgentToken()
  if (!token) return false

  // Basic JWT expiration check (decode payload without verification)
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const exp = payload.exp
    if (exp && Date.now() / 1000 > exp) {
      // Token expired — clean up
      clearAgentSession()
      return false
    }
    return true
  } catch {
    return false
  }
}

/** Store agent session data after successful login */
export function setAgentSession(token: string, agentId: string, tier: string): void {
  localStorage.setItem(AGENT_JWT_KEY, token)
  localStorage.setItem(AGENT_ID_KEY, agentId)
  localStorage.setItem(AGENT_TIER_KEY, tier)
  // Also set the general auth token so API client picks it up
  setAuthToken(token)
}

/** Clear agent session data on logout */
export function clearAgentSession(): void {
  localStorage.removeItem(AGENT_JWT_KEY)
  localStorage.removeItem(AGENT_ID_KEY)
  localStorage.removeItem(AGENT_TIER_KEY)
}

/** Get the stored agent ID */
export function getAgentId(): string | null {
  return localStorage.getItem(AGENT_ID_KEY)
}
