/**
 * Hook to fetch public platform configuration from /api/v1/config.
 *
 * Fetches once and caches for the lifetime of the app.
 * Replaces build-time VITE_REQUIRE_AGENT_API_KEY with runtime config.
 */

import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface PlatformConfig {
  min_bounty_usd: number
  max_bounty_usd: number
  supported_networks: string[]
  supported_tokens: string[]
  preferred_network: string
  require_api_key: boolean
  worldid_min_bounty_for_orb_usd: number
}

interface UsePlatformConfigReturn {
  config: PlatformConfig | null
  requireApiKey: boolean
  worldIdBountyThreshold: number
  loading: boolean
  error: string | null
}

// Module-level cache so we only fetch once across all component instances
let cachedConfig: PlatformConfig | null = null
let fetchPromise: Promise<PlatformConfig> | null = null

async function fetchConfig(): Promise<PlatformConfig> {
  const resp = await fetch(`${API_BASE}/api/v1/config`)
  if (!resp.ok) throw new Error(`Config fetch failed: ${resp.status}`)
  return resp.json()
}

/**
 * Non-hook accessor for services that can't use React hooks.
 * Returns the cached require_api_key value (defaults to true if not yet fetched).
 * Call ensurePlatformConfig() early in app boot to prime the cache.
 */
export function getRequireApiKey(): boolean {
  return cachedConfig?.require_api_key ?? true
}

/**
 * Non-hook accessor for World ID bounty threshold.
 * Returns cached value or default (500) if not yet fetched.
 */
export function getWorldIdBountyThreshold(): number {
  return cachedConfig?.worldid_min_bounty_for_orb_usd ?? 500
}

/**
 * Prime the config cache. Call once at app startup (e.g. in main.tsx).
 * Safe to call multiple times — deduplicates automatically.
 */
export function ensurePlatformConfig(): Promise<PlatformConfig | null> {
  if (cachedConfig) return Promise.resolve(cachedConfig)
  if (!fetchPromise) {
    fetchPromise = fetchConfig()
  }
  return fetchPromise
    .then((data) => {
      cachedConfig = data
      return data
    })
    .catch(() => null)
    .finally(() => {
      fetchPromise = null
    })
}

export function usePlatformConfig(): UsePlatformConfigReturn {
  const [config, setConfig] = useState<PlatformConfig | null>(cachedConfig)
  const [loading, setLoading] = useState(!cachedConfig)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (cachedConfig) {
      setConfig(cachedConfig)
      setLoading(false)
      return
    }

    // Deduplicate concurrent fetches
    if (!fetchPromise) {
      fetchPromise = fetchConfig()
    }

    fetchPromise
      .then((data) => {
        cachedConfig = data
        setConfig(data)
      })
      .catch((err) => {
        setError(err.message)
      })
      .finally(() => {
        setLoading(false)
        fetchPromise = null
      })
  }, [])

  return {
    config,
    requireApiKey: config?.require_api_key ?? true,
    worldIdBountyThreshold: config?.worldid_min_bounty_for_orb_usd ?? 500,
    loading,
    error,
  }
}
