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
 * Rate an agent after task completion (worker -> agent).
 *
 * @deprecated Use prepareFeedback + confirmFeedback instead.
 * This legacy function calls the old endpoint which no longer submits on-chain.
 */
export interface RateAgentRequest {
  task_id: string
  score: number // 0-100
  comment?: string
}

export async function rateAgent(
  request: RateAgentRequest
): Promise<FeedbackResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Client-Info': 'execution-market-dashboard',
  }

  const response = await fetch(
    `${API_BASE_URL}/api/v1/reputation/agents/rate`,
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

// --------------------------------------------------------------------------
// Worker Direct Signing (prepare → sign → confirm)
// --------------------------------------------------------------------------

export interface PrepareFeedbackRequest {
  agent_id: number
  task_id: string
  score: number // 0-100
  comment?: string
  worker_address: string
}

export interface PrepareFeedbackResponse {
  prepare_id: string
  contract_address: string
  chain_id: number
  agent_id: number
  value: number
  value_decimals: number
  tag1: string
  tag2: string
  endpoint: string
  feedback_uri: string
  feedback_hash: string
  estimated_gas: number
}

export interface ConfirmFeedbackRequest {
  prepare_id: string
  tx_hash: string
  task_id: string
}

export interface ConfirmFeedbackResponse {
  success: boolean
  transaction_hash: string | null
  network: string
  error: string | null
}

/**
 * Prepare on-chain feedback parameters for worker direct signing.
 *
 * Returns the giveFeedback() call parameters that the worker's wallet
 * will use to submit the TX on-chain (msg.sender = worker).
 */
export async function prepareFeedback(
  request: PrepareFeedbackRequest
): Promise<PrepareFeedbackResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/reputation/prepare-feedback`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Info': 'execution-market-dashboard',
      },
      body: JSON.stringify(request),
    }
  )

  if (!response.ok) {
    const text = await response.text()
    let message = `Prepare feedback failed: ${response.status}`
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
 * Confirm that the worker signed and submitted the feedback TX.
 */
export async function confirmFeedback(
  request: ConfirmFeedbackRequest
): Promise<ConfirmFeedbackResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/reputation/confirm-feedback`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Info': 'execution-market-dashboard',
      },
      body: JSON.stringify(request),
    }
  )

  if (!response.ok) {
    const text = await response.text()
    let message = `Confirm feedback failed: ${response.status}`
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
 * Check identity registration status for a wallet address.
 * Returns null if the service is unavailable (404/503).
 */
export interface IdentityCheckResult {
  registered: boolean
  agent_id: number | null
  network: string
}

export async function checkIdentityStatus(
  walletAddress: string,
  network = 'base'
): Promise<IdentityCheckResult | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/reputation/check-identity?wallet=${encodeURIComponent(walletAddress)}&network=${encodeURIComponent(network)}`,
      {
        headers: {
          'X-Client-Info': 'execution-market-dashboard',
        },
      }
    )

    if (response.status === 404 || response.status === 503) {
      return null
    }

    if (!response.ok) {
      return null
    }

    return response.json()
  } catch {
    return null
  }
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
