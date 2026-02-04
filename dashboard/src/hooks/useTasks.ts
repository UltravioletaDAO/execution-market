// Execution Market: Task Hooks
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import type { Task, TaskStatus, TaskCategory } from '../types/database'

interface UseTasksOptions {
  status?: TaskStatus | TaskStatus[]
  category?: TaskCategory
  limit?: number
}

interface UseTasksResult {
  tasks: Task[]
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useTasks(options: UseTasksOptions = {}): UseTasksResult {
  console.log('[useTasks] Hook called with options:', options)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchTasks = useCallback(async () => {
    console.log('[useTasks] fetchTasks called')
    setLoading(true)
    setError(null)

    try {
      console.log('[useTasks] Building query...')
      let query = supabase
        .from('tasks')
        .select('*')
        .order('created_at', { ascending: false })
      console.log('[useTasks] Query built, about to execute...')

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

      console.log('[useTasks] Executing query NOW...')
      const { data, error: fetchError } = await query
      console.log('[useTasks] Query returned!')

      console.log('Tasks query result:', { data, error: fetchError })

      if (fetchError) throw fetchError
      setTasks(data || [])
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch tasks'))
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
export function useAvailableTasks(options: Omit<UseTasksOptions, 'status'> = {}): UseTasksResult {
  return useTasks({ ...options, status: 'published' })
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
      setError(err instanceof Error ? err : new Error('Failed to fetch tasks'))
    } finally {
      setLoading(false)
    }
  }, [executorId])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  return { tasks, loading, error, refetch: fetchTasks }
}
