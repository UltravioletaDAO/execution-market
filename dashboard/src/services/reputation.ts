/**
 * Execution Market: Reputation Service
 *
 * Client for the ERC-8004 reputation API endpoints.
 * Used by the agent dashboard to rate workers after task completion.
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

export interface RateWorkerRequest {
  task_id: string
  score: number // 0-100
  comment?: string
  proof_tx?: string
  worker_address?: string
}

export interface FeedbackResponse {
  success: boolean
  transaction_hash: string | null
  feedback_index: number | null
  network: string
  error: string | null
}

export interface ReputationInfo {
  agent_id: number
  count: number
  score: number
  network: string
}

// --------------------------------------------------------------------------
// API Functions
// --------------------------------------------------------------------------

/**
 * Rate a worker after task completion (agent -> worker).
 *
 * The backend expects a score in the 0-100 range.
 * Requires an API key configured via VITE_API_KEY.
 */
export async function rateWorker(
  request: RateWorkerRequest
): Promise<FeedbackResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Client-Info': 'execution-market-dashboard',
  }

  const apiKey = import.meta.env.VITE_API_KEY
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`
    headers['X-API-Key'] = apiKey
  }

  const response = await fetch(
    `${API_BASE_URL}/api/v1/reputation/workers/rate`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    }
  )

  if (!response.ok) {
    const text = await response.text()
    let message = `Rating failed: ${response.status}`
    try {
      const data = JSON.parse(text)
      message = data.detail || data.message || message
    } catch {
      // Use default message
    }
    throw new Error(message)
  }

  return response.json()
}

/**
 * Get Execution Market's platform reputation.
 */
export async function getEMReputation(): Promise<ReputationInfo> {
  const response = await fetch(`${API_BASE_URL}/api/v1/reputation/em`, {
    headers: {
      'X-Client-Info': 'execution-market-dashboard',
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch EM reputation: ${response.status}`)
  }

  return response.json()
}

/**
 * Get reputation for a specific agent by ERC-8004 token ID.
 */
export async function getAgentReputation(
  agentId: number
): Promise<ReputationInfo> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/reputation/agents/${agentId}`,
    {
      headers: {
        'X-Client-Info': 'execution-market-dashboard',
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch agent reputation: ${response.status}`)
  }

  return response.json()
}

/**
 * Convert a 1-5 star rating to the 0-100 scale used by the API.
 *
 * Mapping:
 *   1 star  -> 20
 *   2 stars -> 40
 *   3 stars -> 60
 *   4 stars -> 80
 *   5 stars -> 100
 */
export function starsToScore(stars: number): number {
  return Math.max(0, Math.min(100, stars * 20))
}
