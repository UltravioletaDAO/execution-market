import { useCallback, useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'

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
      console.warn('[Metrics] API fetch failed, trying Supabase fallback:', err)
      // Fallback: query Supabase directly for basic counts
      try {
        const [executorsRes, tasksRes] = await Promise.all([
          supabase.from('executors').select('id', { count: 'exact', head: true }),
          supabase.from('tasks').select('status, executor_id, agent_id').limit(10000),
        ])

        const taskRows = tasksRes.data || []
        const completed = taskRows.filter((t: { status: string }) => t.status === 'completed').length
        const published = taskRows.filter((t: { status: string }) => t.status === 'published').length
        const activeWorkers = new Set(
          taskRows
            .filter((t: { status: string; executor_id?: string }) =>
              ['accepted', 'in_progress', 'submitted'].includes(t.status) && t.executor_id
            )
            .map((t: { executor_id?: string }) => t.executor_id)
        )
        const activeAgents = new Set(
          taskRows
            .filter((t: { status: string; agent_id?: string }) =>
              ['published', 'accepted', 'in_progress', 'submitted'].includes(t.status) && t.agent_id
            )
            .map((t: { agent_id?: string }) => t.agent_id)
        )

        const fallbackMetrics: PublicPlatformMetrics = {
          users: {
            registered_workers: executorsRes.count || 0,
            registered_agents: activeAgents.size,
            workers_with_tasks: activeWorkers.size,
            workers_active_now: activeWorkers.size,
            workers_completed: new Set(
              taskRows
                .filter((t: { status: string; executor_id?: string }) => t.status === 'completed' && t.executor_id)
                .map((t: { executor_id?: string }) => t.executor_id)
            ).size,
            agents_active_now: activeAgents.size,
          },
          tasks: {
            total: taskRows.length,
            published,
            accepted: taskRows.filter((t: { status: string }) => t.status === 'accepted').length,
            in_progress: taskRows.filter((t: { status: string }) => t.status === 'in_progress').length,
            submitted: taskRows.filter((t: { status: string }) => t.status === 'submitted').length,
            verifying: taskRows.filter((t: { status: string }) => t.status === 'verifying').length,
            completed,
            disputed: taskRows.filter((t: { status: string }) => t.status === 'disputed').length,
            cancelled: taskRows.filter((t: { status: string }) => t.status === 'cancelled').length,
            expired: taskRows.filter((t: { status: string }) => t.status === 'expired').length,
            live: taskRows.filter((t: { status: string }) =>
              ['published', 'accepted', 'in_progress', 'submitted'].includes(t.status)
            ).length,
          },
          activity: {
            workers_with_active_tasks: activeWorkers.size,
            workers_with_completed_tasks: new Set(
              taskRows
                .filter((t: { status: string; executor_id?: string }) => t.status === 'completed' && t.executor_id)
                .map((t: { executor_id?: string }) => t.executor_id)
            ).size,
            agents_with_live_tasks: activeAgents.size,
          },
          payments: { total_volume_usd: 0, total_fees_usd: 0 },
          generated_at: new Date().toISOString(),
        }
        console.log('[Metrics] Supabase fallback succeeded:', fallbackMetrics.users.registered_workers, 'workers')
        setMetrics(fallbackMetrics)
        return
      } catch (fallbackErr) {
        console.error('[Metrics] Supabase fallback also failed:', fallbackErr)
      }

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
