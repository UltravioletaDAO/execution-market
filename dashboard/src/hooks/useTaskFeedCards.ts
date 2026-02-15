/**
 * useTaskFeedCards Hook
 *
 * Enriches activity feed events with full task data (both participants,
 * transactions, timing) for the rich TaskFeedCard display.
 *
 * Queries tasks + executors to build TaskFeedCardData objects.
 * Falls back gracefully when data is missing.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { TaskFeedCardData, TaskFeedParticipant } from '../components/feed/TaskFeedCard'
import type { ActivityEventType, ActivityFilter, ActivityFeedMode } from './useActivityFeed'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UseTaskFeedCardsOptions {
  limit?: number
  filter?: ActivityFilter
  mode?: ActivityFeedMode
  realtime?: boolean
}

interface UseTaskFeedCardsResult {
  cards: TaskFeedCardData[]
  loading: boolean
  error: string | null
  hasMore: boolean
  loadMore: () => void
  newCardCount: number
  clearNewCards: () => void
}

// ---------------------------------------------------------------------------
// Status → event type mapping
// ---------------------------------------------------------------------------

const STATUS_TO_EVENT: Record<string, ActivityEventType> = {
  published: 'task_created',
  accepted: 'task_accepted',
  in_progress: 'task_accepted',
  submitted: 'task_accepted',
  verifying: 'task_accepted',
  completed: 'task_completed',
  disputed: 'dispute_opened',
  expired: 'task_created',
  cancelled: 'task_created',
}

const FILTER_EVENT_MAP: Record<ActivityFilter, ActivityEventType[] | null> = {
  all: null,
  tasks: ['task_created', 'task_accepted', 'task_completed'],
  reputation: ['feedback_given'],
  workers: ['worker_joined'],
}

// ---------------------------------------------------------------------------
// Executor cache
// ---------------------------------------------------------------------------

const executorCache = new Map<string, TaskFeedParticipant>()

async function fetchParticipant(walletOrId: string | null): Promise<TaskFeedParticipant | null> {
  if (!walletOrId) return null

  const cached = executorCache.get(walletOrId)
  if (cached) return cached

  try {
    const { data } = await supabase
      .from('executors')
      .select('wallet_address, display_name, agent_type, avatar_url, reputation_score, tasks_completed')
      .or(`wallet_address.eq.${walletOrId},id.eq.${walletOrId}`)
      .limit(1)
      .maybeSingle()

    if (!data) {
      // Return minimal participant with just the wallet
      const minimal: TaskFeedParticipant = {
        wallet: walletOrId,
        name: null,
        type: null,
        reputation_score: null,
        tasks_completed: null,
      }
      executorCache.set(walletOrId, minimal)
      return minimal
    }

    const participant: TaskFeedParticipant = {
      wallet: data.wallet_address,
      name: data.display_name,
      type: data.agent_type || 'human',
      reputation_score: data.reputation_score,
      tasks_completed: data.tasks_completed,
      avatar_url: data.avatar_url,
    }
    executorCache.set(walletOrId, participant)
    return participant
  } catch {
    return {
      wallet: walletOrId,
      name: null,
      type: null,
      reputation_score: null,
      tasks_completed: null,
    }
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

const PAGE_SIZE = 15

export function useTaskFeedCards(
  options: UseTaskFeedCardsOptions = {},
): UseTaskFeedCardsResult {
  const { limit, filter = 'all', mode = 'public', realtime = true } = options
  const effectiveLimit = limit ?? PAGE_SIZE
  const enableRealtime = realtime && mode === 'authenticated'

  const [cards, setCards] = useState<TaskFeedCardData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [newCardCount, setNewCardCount] = useState(0)
  const [page, setPage] = useState(0)
  const initialFetchDone = useRef(false)

  // ------------------------------------------------------------------
  // Build card from task row
  // ------------------------------------------------------------------
  const buildCard = useCallback(async (task: Record<string, unknown>): Promise<TaskFeedCardData> => {
    const agentId = task.agent_id as string | null
    const executorId = task.executor_id as string | null

    // Fetch both participants in parallel
    const [agent, worker] = await Promise.all([
      fetchParticipant(agentId),
      executorId ? fetchParticipant(executorId) : Promise.resolve(null),
    ])

    const status = task.status as string
    const eventType = STATUS_TO_EVENT[status] || 'task_created'

    const createdAt = task.created_at as string
    const updatedAt = task.updated_at as string
    const completedAt = task.completed_at as string | null
    let timeTaken: number | null = null
    if (status === 'completed' && createdAt && (completedAt || updatedAt)) {
      const endTime = completedAt || updatedAt
      timeTaken = Math.round((new Date(endTime).getTime() - new Date(createdAt).getTime()) / 1000)
    }

    // Extract transaction hashes from task + submission data
    const escrowTx = task.escrow_tx as string | null
    const refundTx = task.refund_tx as string | null

    // Payment and reputation TXs come from the submission
    const submissions = (task.submissions || []) as Array<Record<string, unknown>>
    const latestSubmission = submissions.length > 0 ? submissions[submissions.length - 1] : null
    const paymentTx = latestSubmission?.payment_tx as string | null ?? null
    const reputationTx = latestSubmission?.reputation_tx as string | null ?? null

    // For now, reputation_tx covers agent→worker. Worker→agent stored separately if available.
    const agentRepTx = reputationTx
    const workerRepTx: string | null = null

    return {
      id: task.id as string,
      event_type: eventType,
      agent: agent || { wallet: agentId, name: null, type: 'ai', reputation_score: null, tasks_completed: null },
      worker,
      task_id: task.id as string,
      task_title: task.title as string | null,
      task_category: task.category as string | null,
      bounty_usd: task.bounty_usd as number | null,
      payment_token: task.payment_token as string | null,
      payment_network: task.payment_network as string | null,
      created_at: updatedAt || createdAt,
      completed_at: status === 'completed' ? updatedAt : null,
      time_taken_seconds: timeTaken,
      escrow_tx: escrowTx,
      payment_tx: paymentTx,
      refund_tx: refundTx,
      agent_reputation_tx: agentRepTx,
      worker_reputation_tx: workerRepTx,
    }
  }, [])

  // ------------------------------------------------------------------
  // Fetch tasks and build cards
  // ------------------------------------------------------------------
  const fetchCards = useCallback(async (pageNum: number, append = false) => {
    if (pageNum === 0) setLoading(true)
    setError(null)

    try {
      // Build query
      let query = supabase
        .from('tasks')
        .select('id, title, status, category, bounty_usd, payment_token, payment_network, agent_id, executor_id, escrow_tx, escrow_id, refund_tx, created_at, updated_at, completed_at, submissions(payment_tx, reputation_tx)')
        .order('updated_at', { ascending: false })
        .range(pageNum * effectiveLimit, (pageNum + 1) * effectiveLimit - 1)

      // Apply filter
      const eventTypes = FILTER_EVENT_MAP[filter]
      if (eventTypes) {
        // Map event types back to task statuses
        const statuses: string[] = []
        if (eventTypes.includes('task_created')) statuses.push('published')
        if (eventTypes.includes('task_accepted')) statuses.push('accepted', 'in_progress', 'submitted', 'verifying')
        if (eventTypes.includes('task_completed')) statuses.push('completed')
        if (eventTypes.includes('dispute_opened')) statuses.push('disputed')
        if (statuses.length > 0) query = query.in('status', statuses)
      }

      const { data: tasks, error: queryError } = await query

      if (queryError) {
        throw new Error(queryError.message)
      }

      if (!tasks || tasks.length === 0) {
        if (!append) setCards([])
        setHasMore(false)
        return
      }

      // Build cards with participant data
      const newCards = await Promise.all(
        tasks.map((task: Record<string, unknown>) => buildCard(task))
      )

      setHasMore(newCards.length >= effectiveLimit)

      if (append) {
        setCards((prev) => [...prev, ...newCards])
      } else {
        setCards(newCards)
      }

      initialFetchDone.current = true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load feed')
    } finally {
      setLoading(false)
    }
  }, [filter, effectiveLimit, buildCard])

  // Initial fetch + refetch on filter change
  useEffect(() => {
    initialFetchDone.current = false
    setPage(0)
    fetchCards(0)
  }, [filter]) // eslint-disable-line react-hooks/exhaustive-deps

  // Load more
  const loadMore = useCallback(() => {
    const nextPage = page + 1
    setPage(nextPage)
    fetchCards(nextPage, true)
  }, [page, fetchCards])

  // Clear new card counter
  const clearNewCards = useCallback(() => setNewCardCount(0), [])

  // ------------------------------------------------------------------
  // Realtime subscription for new/updated tasks
  // ------------------------------------------------------------------
  useEffect(() => {
    if (!enableRealtime) return

    const channel = supabase
      .channel('task_feed_realtime')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tasks' },
        async (payload: { new: Record<string, unknown>; eventType: string }) => {
          if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
            try {
              const card = await buildCard(payload.new)
              const eventTypes = FILTER_EVENT_MAP[filter]
              if (eventTypes && !eventTypes.includes(card.event_type)) return

              setCards((prev) => {
                // Replace existing or prepend
                const idx = prev.findIndex((c) => c.task_id === card.task_id)
                if (idx >= 0) {
                  const updated = [...prev]
                  updated[idx] = card
                  return updated
                }
                return [card, ...prev]
              })
              setNewCardCount((c) => c + 1)
            } catch {
              // ignore realtime build errors
            }
          }
        },
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [enableRealtime, filter, buildCard])

  return { cards, loading, error, hasMore, loadMore, newCardCount, clearNewCards }
}
