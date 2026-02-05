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

function getPublicMetricsUrl(): string {
  const base = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')

  if (base.endsWith('/api')) {
    return `${base}/v1/public/metrics`
  }

  return `${base}/api/v1/public/metrics`
}

export function usePublicMetrics(): UsePublicMetricsResult {
  const [metrics, setMetrics] = useState<PublicPlatformMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const endpoint = useMemo(() => getPublicMetricsUrl(), [])

  const refresh = useCallback(async () => {
    setError(null)

    try {
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Client-Info': 'execution-market-dashboard',
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to load platform metrics (${response.status})`)
      }

      const data = await response.json() as PublicPlatformMetrics
      setMetrics(data)
    } catch (err) {
      const normalized = err instanceof Error ? err : new Error('Failed to load platform metrics')
      setError(normalized)
    } finally {
      setLoading(false)
    }
  }, [endpoint])

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
