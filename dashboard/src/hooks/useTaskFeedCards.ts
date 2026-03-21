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
import type { TaskFeedCardData, TaskFeedParticipant, FeedbackData } from '../components/feed/TaskFeedCard'
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
  in_progress: 'task_in_progress',
  submitted: 'task_submitted',
  verifying: 'task_submitted',
  completed: 'task_completed',
  disputed: 'dispute_opened',
  expired: 'task_created',
  cancelled: 'task_created',
}

const FILTER_EVENT_MAP: Record<ActivityFilter, ActivityEventType[] | null> = {
  all: null,
  tasks: ['task_created', 'task_accepted', 'task_in_progress', 'task_submitted', 'task_completed'],
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

    // Payment TX from submission
    const submissions = (task.submissions || []) as Array<Record<string, unknown>>
    const latestSubmission = submissions.length > 0 ? submissions[submissions.length - 1] : null
    const paymentTx = latestSubmission?.payment_tx as string | null ?? null

    // Bidirectional feedback from feedback_documents
    const feedbackDocs = (task.feedback_documents || []) as Array<Record<string, unknown>>

    // worker_rating = agent rated the worker
    const workerRatingDoc = feedbackDocs.find(d => d.feedback_type === 'worker_rating')
    // agent_rating = worker rated the agent
    const agentRatingDoc = feedbackDocs.find(d => d.feedback_type === 'agent_rating')

    const buildFeedback = (doc: Record<string, unknown> | undefined): FeedbackData | null => {
      if (!doc) {
        // If task is completed, show as pending
        if (status === 'completed') {
          return { score: null, reputation_tx: null, comment: null, status: 'pending' }
        }
        return null
      }
      const score = doc.score as number
      const docJson = doc.document_json as Record<string, unknown> | null
      return {
        score,
        reputation_tx: doc.reputation_tx as string | null,
        comment: docJson?.comment as string | null ?? docJson?.notes as string | null ?? null,
        status: 'completed',
      }
    }

    const agentToWorkerFeedback = buildFeedback(workerRatingDoc)
    const workerToAgentFeedback = buildFeedback(agentRatingDoc)

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
      agent_to_worker_feedback: agentToWorkerFeedback,
      worker_to_agent_feedback: workerToAgentFeedback,
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
        .select('id, title, status, category, bounty_usd, payment_token, payment_network, agent_id, executor_id, escrow_tx, escrow_id, refund_tx, created_at, updated_at, completed_at, submissions(payment_tx, reputation_tx), feedback_documents(feedback_type, score, reputation_tx, document_json)')
        .order('updated_at', { ascending: false })
        .range(pageNum * effectiveLimit, (pageNum + 1) * effectiveLimit - 1)

      // Handle 'workers' filter: query executors table for recently joined workers
      if (filter === 'workers') {
        try {
          const { data: executors, error: execError } = await supabase
            .from('executors')
            .select('id, wallet_address, display_name, agent_type, avatar_url, reputation_score, tasks_completed, created_at')
            .order('created_at', { ascending: false })
            .range(pageNum * effectiveLimit, (pageNum + 1) * effectiveLimit - 1)

          if (execError || !executors || executors.length === 0) {
            if (!append) setCards([])
            setHasMore(false)
            return
          }

          const workerCards: TaskFeedCardData[] = executors.map((exec: Record<string, unknown>) => ({
            id: `worker-${exec.id}`,
            event_type: 'worker_joined' as ActivityEventType,
            agent: {
              wallet: exec.wallet_address as string,
              name: exec.display_name as string | null,
              type: (exec.agent_type as string) || 'human',
              reputation_score: exec.reputation_score as number | null,
              tasks_completed: exec.tasks_completed as number | null,
              avatar_url: exec.avatar_url as string | null,
            },
            worker: null,
            task_id: null,
            task_title: null,
            task_category: null,
            bounty_usd: null,
            payment_token: null,
            payment_network: null,
            created_at: exec.created_at as string,
            completed_at: null,
            time_taken_seconds: null,
            escrow_tx: null,
            payment_tx: null,
            refund_tx: null,
            agent_to_worker_feedback: null,
            worker_to_agent_feedback: null,
          }))

          setHasMore(workerCards.length >= effectiveLimit)
          if (append) {
            setCards((prev) => [...prev, ...workerCards])
          } else {
            setCards(workerCards)
          }
          return
        } catch {
          if (!append) setCards([])
          setHasMore(false)
          return
        }
      }

      // Handle 'reputation' filter: query completed tasks (which have feedback)
      if (filter === 'reputation') {
        query = query.in('status', ['completed', 'disputed'])
      } else {
        // Apply filter — map event types back to task statuses
        const eventTypes = FILTER_EVENT_MAP[filter]
        if (eventTypes) {
          const statuses: string[] = []
          if (eventTypes.includes('task_created')) statuses.push('published')
          if (eventTypes.includes('task_accepted')) statuses.push('accepted', 'in_progress', 'submitted', 'verifying')
          if (eventTypes.includes('task_completed')) statuses.push('completed')
          if (eventTypes.includes('dispute_opened')) statuses.push('disputed')
          if (statuses.length > 0) query = query.in('status', statuses)
        }
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
      let newCards = await Promise.all(
        tasks.map((task: Record<string, unknown>) => buildCard(task))
      )

      // For reputation filter, only show cards that actually have feedback
      if (filter === 'reputation') {
        newCards = newCards
          .filter((c) => c.agent_to_worker_feedback?.status === 'completed' || c.worker_to_agent_feedback?.status === 'completed')
          .map((c) => ({ ...c, event_type: 'feedback_given' as ActivityEventType }))
      }

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
