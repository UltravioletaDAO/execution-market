// Execution Market: Task Hooks
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import type { Task, TaskStatus, TaskCategory } from '../types/database'

interface UseTasksOptions {
  status?: TaskStatus | TaskStatus[]
  category?: TaskCategory
  limit?: number
}

interface UseAvailableTasksOptions extends Omit<UseTasksOptions, 'status'> {
  includeExpiredFallback?: boolean
  executorId?: string
}

interface UseTasksResult {
  tasks: Task[]
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

interface UseAvailableTasksResult extends UseTasksResult {
  removeTask: (taskId: string) => void
}

const normalizeError = (err: unknown): Error => {
  if (err instanceof Error) return err
  if (err && typeof err === 'object') {
    const message = (err as { message?: string }).message
    const code = (err as { code?: string }).code
    if (message) {
      return new Error(code ? `${message} (${code})` : message)
    }
  }
  return new Error('Failed to fetch tasks')
}

export function useTasks(options: UseTasksOptions = {}): UseTasksResult {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      let query = supabase
        .from('tasks')
        .select('*')
        .order('created_at', { ascending: false })

      if (options.status) {
        if (Array.isArray(options.status)) {
          query = query.in('status', options.status)
        } else {
          query = query.eq('status', options.status)
        }
      }

      if (options.category) {
        query = query.eq('category', options.category)
      }

      if (options.limit) {
        query = query.limit(options.limit)
      }

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError
      setTasks(data || [])
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setLoading(false)
    }
  }, [options.status, options.category, options.limit])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // Subscribe to realtime updates
  useEffect(() => {
    const channel = supabase
      .channel('tasks-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tasks' },
        () => {
          fetchTasks()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [fetchTasks])

  return { tasks, loading, error, refetch: fetchTasks }
}

// Single task hook
interface UseTaskResult {
  task: Task | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useTask(taskId: string | undefined): UseTaskResult {
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchTask = useCallback(async () => {
    if (!taskId) {
      setTask(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data, error: fetchError } = await supabase
        .from('tasks')
        .select('*')
        .eq('id', taskId)
        .single()

      if (fetchError) throw fetchError
      setTask(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch task'))
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    fetchTask()
  }, [fetchTask])

  // Subscribe to realtime updates for this task
  useEffect(() => {
    if (!taskId) return

    const channel = supabase
      .channel(`task-${taskId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'tasks',
          filter: `id=eq.${taskId}`,
        },
        () => {
          fetchTask()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [taskId, fetchTask])

  return { task, loading, error, refetch: fetchTask }
}

// Available tasks for executors (published, not accepted)
export function useAvailableTasks(options: UseAvailableTasksOptions = {}): UseAvailableTasksResult {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const buildAvailableTasksUrl = useCallback((includeExpired: boolean): string => {
    const base = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
    const path = base.endsWith('/api') ? `${base}/v1/tasks/available` : `${base}/api/v1/tasks/available`
    const params = new URLSearchParams()

    if (options.category) {
      params.set('category', options.category)
    }
    if (options.limit) {
      params.set('limit', String(options.limit))
    } else {
      params.set('limit', '50')
    }
    if (options.executorId) {
      params.set('exclude_executor', options.executorId)
    }
    if (includeExpired) {
      params.set('include_expired', 'true')
    }

    return `${path}?${params.toString()}`
  }, [options.category, options.limit, options.executorId])

  const normalizeTask = useCallback((raw: Partial<Task> & { id: string; agent_id: string; category: TaskCategory; title: string; instructions: string; bounty_usd: number; deadline: string; created_at: string }): Task => {
    const normalizedStatus = (raw?.status || 'published') as TaskStatus
    return {
      ...raw,
      status: normalizedStatus,
      evidence_schema: raw?.evidence_schema || { required: [], optional: [] },
      required_roles: raw?.required_roles || [],
      payment_token: raw?.payment_token || 'USDC',
      payment_network: raw?.payment_network || 'base',
      min_reputation: raw?.min_reputation || 0,
      max_executors: raw?.max_executors || 1,
      updated_at: raw?.updated_at || raw?.created_at || new Date().toISOString(),
      location: raw?.location || null,
      location_radius_km: raw?.location_radius_km ?? null,
      location_hint: raw?.location_hint ?? null,
      assigned_at: raw?.assigned_at ?? null,
      chainwitness_proof: raw?.chainwitness_proof ?? null,
      completed_at: raw?.completed_at ?? null,
      refund_tx: raw?.refund_tx ?? null,
      executor_id: raw?.executor_id ?? null,
      escrow_tx: raw?.escrow_tx ?? null,
      escrow_id: raw?.escrow_id ?? null,
    } as Task
  }, [])

  const fetchAvailableTasks = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const primaryRes = await fetch(buildAvailableTasksUrl(false), {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      })

      if (!primaryRes.ok) {
        throw new Error(`Failed to fetch available tasks (${primaryRes.status})`)
      }

      const primaryData = await primaryRes.json() as { tasks?: Array<Partial<Task> & { id: string; agent_id: string; category: TaskCategory; title: string; instructions: string; bounty_usd: number; deadline: string; created_at: string }> }
      let incoming = (primaryData.tasks || []).map(normalizeTask)

      if (incoming.length === 0 && options.includeExpiredFallback) {
        const fallbackRes = await fetch(buildAvailableTasksUrl(true), {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        })

        if (fallbackRes.ok) {
          const fallbackData = await fallbackRes.json() as { tasks?: Array<Partial<Task> & { id: string; agent_id: string; category: TaskCategory; title: string; instructions: string; bounty_usd: number; deadline: string; created_at: string }> }
          incoming = (fallbackData.tasks || []).map(normalizeTask)
        }
      }

      setTasks(incoming)
    } catch (err) {
      setError(normalizeError(err))
      setTasks([])
    } finally {
      setLoading(false)
    }
  }, [buildAvailableTasksUrl, normalizeTask, options.includeExpiredFallback])

  useEffect(() => {
    fetchAvailableTasks()
  }, [fetchAvailableTasks])

  useEffect(() => {
    const intervalId = window.setInterval(fetchAvailableTasks, 30_000)
    return () => window.clearInterval(intervalId)
  }, [fetchAvailableTasks])

  const removeTask = useCallback((taskId: string) => {
    setTasks(prev => prev.filter(t => t.id !== taskId))
  }, [])

  return { tasks, loading, error, refetch: fetchAvailableTasks, removeTask }
}

// My tasks (for logged-in executor)
export function useMyTasks(executorId: string | undefined): UseTasksResult {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchTasks = useCallback(async () => {
    if (!executorId) {
      setTasks([])
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data, error: fetchError } = await supabase
        .from('tasks')
        .select('*')
        .eq('executor_id', executorId)
        .order('updated_at', { ascending: false })

      if (fetchError) throw fetchError
      setTasks(data || [])
    } catch (err) {
      setError(normalizeError(err))
    } finally {
      setLoading(false)
    }
  }, [executorId])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // Subscribe to realtime updates so accepted tasks appear immediately
  useEffect(() => {
    if (!executorId) return

    const channel = supabase
      .channel(`my-tasks-${executorId}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tasks' },
        (payload: { new?: { executor_id?: string }; old?: { executor_id?: string } }) => {
          // Refetch when any task change involves this executor
          const newRow = payload.new as { executor_id?: string } | undefined
          const oldRow = payload.old as { executor_id?: string } | undefined
          if (newRow?.executor_id === executorId || oldRow?.executor_id === executorId) {
            fetchTasks()
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [executorId, fetchTasks])

  return { tasks, loading, error, refetch: fetchTasks }
}
