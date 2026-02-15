/**
 * useAgentReputation - Fetch agent reputation from ERC-8004 on-chain registry
 *
 * Calls GET /api/v1/reputation/agents/{agentId} which queries the
 * ERC-8004 Reputation Registry via the Facilitator.
 */

import { useState, useEffect } from 'react'

export interface AgentReputation {
  agent_id: number
  count: number
  score: number
  network: string
}

/** Reputation tier derived from score */
export type ReputationTier = 'Bronce' | 'Plata' | 'Oro' | 'Diamante'

export function getReputationTier(score: number): ReputationTier {
  if (score >= 81) return 'Diamante'
  if (score >= 61) return 'Oro'
  if (score >= 31) return 'Plata'
  return 'Bronce'
}

export function getTierColor(tier: ReputationTier): string {
  switch (tier) {
    case 'Diamante': return 'text-purple-700 bg-purple-50 border-purple-200'
    case 'Oro': return 'text-yellow-700 bg-yellow-50 border-yellow-200'
    case 'Plata': return 'text-gray-600 bg-gray-50 border-gray-200'
    case 'Bronce': return 'text-orange-700 bg-orange-50 border-orange-200'
  }
}

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

// EM platform agent ID on Base ERC-8004
const EM_AGENT_ID = 2106

export function useAgentReputation(agentId?: number) {
  const [data, setData] = useState<AgentReputation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const resolvedId = agentId ?? EM_AGENT_ID

  useEffect(() => {
    let cancelled = false

    async function fetchReputation() {
      setLoading(true)
      setError(null)
      try {
        const resp = await fetch(`${API_BASE}/api/v1/reputation/agents/${resolvedId}`)
        if (!resp.ok) {
          if (resp.status === 404) {
            setData(null)
            return
          }
          throw new Error(`HTTP ${resp.status}`)
        }
        const json = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown error')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchReputation()
    return () => { cancelled = true }
  }, [resolvedId])

  return { data, loading, error }
}
