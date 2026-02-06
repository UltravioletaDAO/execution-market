import { useCallback, useEffect, useMemo, useState } from 'react'

export interface PublicPlatformMetrics {
  users: {
    registered_workers: number
    registered_agents: number
    workers_with_tasks: number
    workers_active_now: number
    workers_completed: number
    agents_active_now: number
  }
  tasks: {
    total: number
    published: number
    accepted: number
    in_progress: number
    submitted: number
    verifying: number
    completed: number
    disputed: number
    cancelled: number
    expired: number
    live: number
  }
  activity: {
    workers_with_active_tasks: number
    workers_with_completed_tasks: number
    agents_with_live_tasks: number
  }
  payments: {
    total_volume_usd: number
    total_fees_usd: number
  }
  generated_at: string
}

interface UsePublicMetricsResult {
  metrics: PublicPlatformMetrics | null
  loading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

const REFRESH_INTERVAL_MS = 60_000

function buildMetricsUrl(base: string): string {
  const normalized = (base || '').replace(/\/+$/, '')
  if (!normalized) return '/api/v1/public/metrics'

  if (normalized.endsWith('/api')) {
    return `${normalized}/v1/public/metrics`
  }

  return `${normalized}/api/v1/public/metrics`
}

function getPublicMetricsUrls(): string[] {
  const base = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
  const urls = [
    buildMetricsUrl(base),
    'https://api.execution.market/api/v1/public/metrics',
    '/api/v1/public/metrics',
  ]

  const deduped: string[] = []
  for (const candidate of urls) {
    if (!candidate) continue
    if (!deduped.includes(candidate)) {
      deduped.push(candidate)
    }
  }
  return deduped
}

export function usePublicMetrics(): UsePublicMetricsResult {
  const [metrics, setMetrics] = useState<PublicPlatformMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const endpoints = useMemo(() => getPublicMetricsUrls(), [])

  const refresh = useCallback(async () => {
    setError(null)

    try {
      let lastError: Error | null = null

      for (const endpoint of endpoints) {
        try {
          const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'X-Client-Info': 'execution-market-dashboard',
            },
          })

          if (!response.ok) {
            lastError = new Error(`Failed to load platform metrics (${response.status})`)
            continue
          }

          const data = await response.json() as PublicPlatformMetrics
          setMetrics(data)
          return
        } catch (endpointErr) {
          lastError = endpointErr instanceof Error ? endpointErr : new Error('Failed to load platform metrics')
        }
      }

      throw lastError ?? new Error('Failed to load platform metrics')
    } catch (err) {
      const normalized = err instanceof Error ? err : new Error('Failed to load platform metrics')
      setError(normalized)
    } finally {
      setLoading(false)
    }
  }, [endpoints])

  useEffect(() => {
    let mounted = true

    const load = async () => {
      if (!mounted) return
      await refresh()
    }

    load()
    const intervalId = window.setInterval(load, REFRESH_INTERVAL_MS)

    return () => {
      mounted = false
      window.clearInterval(intervalId)
    }
  }, [refresh])

  return { metrics, loading, error, refresh }
}
