/**
 * useIdentity -- ERC-8004 On-Chain Identity Hook
 *
 * Checks whether the worker's wallet is registered on the ERC-8004
 * Identity Registry (Base Mainnet) and provides methods to initiate
 * registration and confirm it after the tx is mined.
 *
 * Flow:
 *   1. On mount, calls GET /api/v1/executors/{id}/identity
 *   2. If not registered, worker clicks "Register" which calls
 *      POST /api/v1/executors/{id}/register-identity to get tx data
 *   3. Worker signs tx via Dynamic.xyz wallet
 *   4. After tx confirms, calls POST /api/v1/executors/{id}/confirm-identity
 */

import { useState, useEffect, useCallback } from 'react'

const API_BASE = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface IdentityStatus {
  status: 'registered' | 'not_registered' | 'error'
  agent_id: number | null
  wallet_address: string | null
  network: string
  chain_id: number
  registry_address: string | null
  error: string | null
}

export interface RegistrationTx {
  to: string
  data: string
  chain_id: number
  value: string
  agent_uri: string
  estimated_gas: number | null
}

export interface RegistrationResponse {
  status: string
  agent_id: number | null
  transaction: RegistrationTx | null
  message: string
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useIdentity(executorId: string | undefined) {
  const [identity, setIdentity] = useState<IdentityStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [registering, setRegistering] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ---- Fetch current identity status ----
  const fetchIdentity = useCallback(async () => {
    if (!executorId) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/executors/${executorId}/identity`,
      )

      if (!response.ok) {
        // 503 means identity service not available -- not a fatal error
        if (response.status === 503) {
          setIdentity(null)
          setLoading(false)
          return
        }
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || `HTTP ${response.status}`)
      }

      const data: IdentityStatus = await response.json()
      setIdentity(data)
    } catch (err) {
      console.error('[useIdentity] Failed to check identity:', err)
      setError(err instanceof Error ? err.message : 'Failed to check identity')
    } finally {
      setLoading(false)
    }
  }, [executorId])

  useEffect(() => {
    fetchIdentity()
  }, [fetchIdentity])

  // ---- Request registration tx data ----
  const prepareRegistration = useCallback(
    async (agentUri?: string): Promise<RegistrationResponse | null> => {
      if (!executorId) return null

      setRegistering(true)
      setError(null)

      try {
        const body: Record<string, string> = {}
        if (agentUri) body.agent_uri = agentUri

        const response = await fetch(
          `${API_BASE}/api/v1/executors/${executorId}/register-identity`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
        )

        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${response.status}`)
        }

        const data: RegistrationResponse = await response.json()

        // If already registered, update identity state
        if (data.status === 'registered') {
          setIdentity({
            status: 'registered',
            agent_id: data.agent_id,
            wallet_address: identity?.wallet_address || null,
            network: identity?.network || 'base',
            chain_id: identity?.chain_id || 8453,
            registry_address: identity?.registry_address || null,
            error: null,
          })
        }

        return data
      } catch (err) {
        console.error('[useIdentity] Failed to prepare registration:', err)
        setError(
          err instanceof Error ? err.message : 'Failed to prepare registration',
        )
        return null
      } finally {
        setRegistering(false)
      }
    },
    [executorId, identity],
  )

  // ---- Confirm registration after tx is mined ----
  const confirmRegistration = useCallback(
    async (txHash: string): Promise<IdentityStatus | null> => {
      if (!executorId) return null

      setConfirming(true)
      setError(null)

      try {
        const response = await fetch(
          `${API_BASE}/api/v1/executors/${executorId}/confirm-identity`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tx_hash: txHash }),
          },
        )

        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${response.status}`)
        }

        const data: IdentityStatus = await response.json()
        setIdentity(data)
        return data
      } catch (err) {
        console.error('[useIdentity] Failed to confirm registration:', err)
        setError(
          err instanceof Error
            ? err.message
            : 'Failed to confirm registration',
        )
        return null
      } finally {
        setConfirming(false)
      }
    },
    [executorId],
  )

  return {
    identity,
    loading,
    registering,
    confirming,
    error,
    isRegistered: identity?.status === 'registered',
    agentId: identity?.agent_id ?? null,
    refetch: fetchIdentity,
    prepareRegistration,
    confirmRegistration,
  }
}
