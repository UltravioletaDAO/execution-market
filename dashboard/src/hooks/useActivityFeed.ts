/**
 * useActivityFeed Hook
 *
 * Fetches activity feed from the activity_feed table with a fallback
 * to synthesizing events from the tasks table when the activity_feed
 * table doesn't exist or is empty.
 *
 * Supports: limit, filter by event_type[], Supabase realtime subscription.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ActivityEventType =
  | 'task_created'
  | 'task_accepted'
  | 'task_in_progress'
  | 'task_submitted'
  | 'task_completed'
  | 'feedback_given'
  | 'worker_joined'
  | 'dispute_opened'
  | 'dispute_resolved'

export interface ActivityEvent {
  id: string
  event_type: ActivityEventType
  actor_wallet: string | null
  actor_name: string | null
  actor_type: string | null
  target_wallet: string | null
  target_name: string | null
  task_id: string | null
  task_title: string | null
  bounty_usd: number | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export type ActivityFilter = 'all' | 'tasks' | 'reputation' | 'workers'
export type ActivityFeedMode = 'public' | 'authenticated'

const FILTER_EVENT_MAP: Record<ActivityFilter, ActivityEventType[] | null> = {
  all: null,
  tasks: ['task_created', 'task_accepted', 'task_in_progress', 'task_submitted', 'task_completed'],
  reputation: ['feedback_given'],
  workers: ['worker_joined'],
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseActivityFeedOptions {
  limit?: number
  filter?: ActivityFilter
  realtime?: boolean
  mode?: ActivityFeedMode
}

interface UseActivityFeedResult {
  events: ActivityEvent[]
  loading: boolean
  error: string | null
  hasMore: boolean
  loadMore: () => void
  newEventCount: number
  clearNewEvents: () => void
}

const PAGE_SIZE = 20

export function useActivityFeed(
  options: UseActivityFeedOptions = {},
): UseActivityFeedResult {
  const { limit, filter = 'all', realtime = true, mode = 'public' } = options
  // In public mode, disable realtime to keep it lightweight
  const enableRealtime = realtime && mode === 'authenticated'
  const effectiveLimit = limit ?? PAGE_SIZE

  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [newEventCount, setNewEventCount] = useState(0)
  const [page, setPage] = useState(0)
  const [useFallback, setUseFallback] = useState(false)

  // Track whether initial fetch has completed
  const initialFetchDone = useRef(false)

  // ------------------------------------------------------------------
  // Fetch from activity_feed table
  // ------------------------------------------------------------------
  const fetchFromActivityFeed = useCallback(
    async (pageNum: number): Promise<{ data: ActivityEvent[]; fallback: boolean }> => {
      try {
        const eventTypes = FILTER_EVENT_MAP[filter]
        let query = supabase
          .from('activity_feed')
          .select('id, event_type, actor_wallet, actor_name, actor_type, target_wallet, target_name, task_id, metadata, created_at')
          .order('created_at', { ascending: false })
          .range(pageNum * effectiveLimit, (pageNum + 1) * effectiveLimit - 1)

        if (eventTypes) {
          query = query.in('event_type', eventTypes)
        }

        const { data, error: queryError } = await query

        // Table doesn't exist or returned error → fallback
        if (queryError) {
          console.warn('[ActivityFeed] activity_feed query failed, using fallback:', queryError.message)
          return { data: [], fallback: true }
        }

        // Empty table on first page → fallback
        if ((!data || data.length === 0) && pageNum === 0) {
          return { data: [], fallback: true }
        }

        return {
          data: (data || []).map((row: Record<string, unknown>) => ({
            ...row,
            task_title: (row.metadata as Record<string, unknown>)?.task_title as string | null ?? null,
            bounty_usd: (row.metadata as Record<string, unknown>)?.bounty_usd as number | null ?? null,
          })) as ActivityEvent[],
          fallback: false,
        }
      } catch {
        return { data: [], fallback: true }
      }
    },
    [filter, effectiveLimit],
  )

  // ------------------------------------------------------------------
  // Fallback: synthesize events from the tasks table
  // ------------------------------------------------------------------
  const fetchFromTasks = useCallback(
    async (pageNum: number): Promise<ActivityEvent[]> => {
      try {
        const { data, error: queryError } = await supabase
          .from('tasks')
          .select('id, title, status, bounty_usd, agent_id, updated_at, executor_id')
          .order('updated_at', { ascending: false })
          .range(pageNum * effectiveLimit, (pageNum + 1) * effectiveLimit - 1)

        if (queryError || !data) return []

        // Map task status to event type
        const statusToEvent: Record<string, ActivityEventType> = {
          published: 'task_created',
          accepted: 'task_accepted',
          in_progress: 'task_accepted',
          completed: 'task_completed',
          disputed: 'dispute_opened',
        }

        const eventTypes = FILTER_EVENT_MAP[filter]

        return (data as Array<{
          id: string
          title: string
          status: string
          bounty_usd: number | null
          agent_id: string | null
          updated_at: string
          executor_id: string | null
        }>)
          .map((task) => {
            const eventType = statusToEvent[task.status] || 'task_created'
            return {
              id: `task-${task.id}`,
              event_type: eventType,
              actor_wallet: task.executor_id || task.agent_id || null,
              actor_name: null,
              actor_type: task.executor_id ? 'worker' : 'agent',
              target_wallet: null,
              target_name: null,
              task_id: task.id,
              task_title: task.title,
              bounty_usd: task.bounty_usd,
              metadata: null,
              created_at: task.updated_at,
            } as ActivityEvent
          })
          .filter((e) => !eventTypes || eventTypes.includes(e.event_type))
      } catch {
        return []
      }
    },
    [filter, effectiveLimit],
  )

  // ------------------------------------------------------------------
  // Main fetch
  // ------------------------------------------------------------------
  const fetchEvents = useCallback(
    async (pageNum: number, append = false) => {
      if (pageNum === 0) setLoading(true)
      setError(null)

      try {
        let newEvents: ActivityEvent[]

        if (useFallback || (!initialFetchDone.current && pageNum === 0)) {
          if (!useFallback && pageNum === 0) {
            // First load: try activity_feed first
            const result = await fetchFromActivityFeed(0)
            if (result.fallback) {
              setUseFallback(true)
              newEvents = await fetchFromTasks(0)
            } else {
              newEvents = result.data
            }
          } else {
            newEvents = await fetchFromTasks(pageNum)
          }
        } else {
          const result = await fetchFromActivityFeed(pageNum)
          if (result.fallback) {
            setUseFallback(true)
            newEvents = await fetchFromTasks(pageNum)
          } else {
            newEvents = result.data
          }
        }

        initialFetchDone.current = true
        setHasMore(newEvents.length >= effectiveLimit)

        if (append) {
          setEvents((prev) => [...prev, ...newEvents])
        } else {
          setEvents(newEvents)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load activity feed')
      } finally {
        setLoading(false)
      }
    },
    [useFallback, fetchFromActivityFeed, fetchFromTasks, effectiveLimit],
  )

  // Initial fetch
  useEffect(() => {
    initialFetchDone.current = false
    setPage(0)
    setUseFallback(false)
    fetchEvents(0)
  }, [filter]) // eslint-disable-line react-hooks/exhaustive-deps

  // Load more
  const loadMore = useCallback(() => {
    const nextPage = page + 1
    setPage(nextPage)
    fetchEvents(nextPage, true)
  }, [page, fetchEvents])

  // Clear new event counter
  const clearNewEvents = useCallback(() => {
    setNewEventCount(0)
  }, [])

  // ------------------------------------------------------------------
  // Realtime subscription
  // ------------------------------------------------------------------
  useEffect(() => {
    if (!enableRealtime) return

    const channel = supabase
      .channel('activity_feed_realtime')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'activity_feed' },
        (payload: { new: Record<string, unknown> }) => {
          const row = payload.new
          const eventTypes = FILTER_EVENT_MAP[filter]
          if (eventTypes && !eventTypes.includes(row.event_type as ActivityEventType)) return

          const newEvent: ActivityEvent = {
            id: row.id as string,
            event_type: row.event_type as ActivityEventType,
            actor_wallet: row.actor_wallet as string | null,
            actor_name: row.actor_name as string | null,
            actor_type: row.actor_type as string | null,
            target_wallet: row.target_wallet as string | null,
            target_name: row.target_name as string | null,
            task_id: row.task_id as string | null,
            task_title: (row.metadata as Record<string, unknown>)?.task_title as string | null ?? null,
            bounty_usd: (row.metadata as Record<string, unknown>)?.bounty_usd as number | null ?? null,
            metadata: row.metadata as Record<string, unknown> | null,
            created_at: row.created_at as string,
          }

          setEvents((prev) => [newEvent, ...prev])
          setNewEventCount((c) => c + 1)
        },
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [enableRealtime, filter])

  return { events, loading, error, hasMore, loadMore, newEventCount, clearNewEvents }
}
