/**
 * useTaskRatings: React Query hook for fetching task ratings.
 *
 * Mirrors em-mobile/hooks/api/useRatings.ts useTaskRatings().
 * Returns { agentRating, workerRating } for a completed task.
 * Use queryClient.invalidateQueries(["ratings","task",taskId]) after submission.
 */

import { useQuery } from '@tanstack/react-query'
import { supabase } from '../lib/supabase'

export interface RatingEntry {
  id: string
  executor_id: string
  task_id: string
  rater_id: string
  rater_type: 'agent' | 'worker'
  rating: number
  stars: number | null
  comment: string | null
  created_at: string
  reputation_tx: string | null
}

export function useTaskRatings(taskId: string | null) {
  return useQuery<{ agentRating: RatingEntry | null; workerRating: RatingEntry | null }>({
    queryKey: ['ratings', 'task', taskId],
    queryFn: async () => {
      if (!taskId) return { agentRating: null, workerRating: null }

      const [ratingsRes, feedbackRes] = await Promise.all([
        supabase
          .from('ratings')
          .select('id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at')
          .eq('task_id', taskId)
          .order('created_at', { ascending: true })
          .limit(10),
        supabase
          .from('feedback_documents')
          .select('feedback_type, reputation_tx')
          .eq('task_id', taskId)
          .not('reputation_tx', 'is', null)
          .limit(10),
      ])

      if (ratingsRes.error) {
        console.warn('[useTaskRatings] Supabase query failed:', ratingsRes.error.message)
        return { agentRating: null, workerRating: null }
      }

      // Map feedback_type → reputation_tx
      // feedback_type "agent_rating" = worker rated agent → rater_type "worker"
      // feedback_type "worker_rating" = agent rated worker → rater_type "agent"
      const feedbackTxMap: Record<string, string> = {}
      for (const fb of feedbackRes.data || []) {
        if (fb.reputation_tx) {
          const raterType = fb.feedback_type === 'agent_rating' ? 'worker' : 'agent'
          feedbackTxMap[raterType] = fb.reputation_tx
        }
      }

      const rows: RatingEntry[] = (ratingsRes.data || []).map((row: Record<string, unknown>) => ({
        id: row.id as string,
        executor_id: row.executor_id as string,
        task_id: row.task_id as string,
        rater_id: row.rater_id as string,
        rater_type: row.rater_type as 'agent' | 'worker',
        rating: row.rating as number,
        stars: (row.stars as number) ?? null,
        comment: (row.comment as string) ?? null,
        created_at: row.created_at as string,
        reputation_tx: feedbackTxMap[row.rater_type as string] || null,
      }))

      return {
        agentRating: rows.find((r) => r.rater_type === 'agent') || null,
        workerRating: rows.find((r) => r.rater_type === 'worker') || null,
      }
    },
    enabled: !!taskId,
    staleTime: 60_000,
  })
}
