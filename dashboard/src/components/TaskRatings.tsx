/**
 * TaskRatings: Bidirectional ratings display for a completed task.
 *
 * Shows agent->worker and worker->agent ratings with stars and comments.
 * "Rate Agent" button for workers who haven't rated yet.
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import { useAuth } from '../context/AuthContext'
import { getExplorerUrl, truncateHash } from '../utils/blockchain'
import { RateAgentModal } from './RateAgentModal'

interface Rating {
  id: string
  task_id: string
  executor_id: string
  rater_id: string
  rater_type: 'agent' | 'worker'
  rating: number // 0-100
  stars: number // 0-5
  comment: string | null
  created_at: string
  reputation_tx: string | null
}

interface TaskRatingsProps {
  taskId: string
  /** If provided, shows "Rate Agent" button for this executor */
  executorId?: string
  /** Payment network for block explorer links (default: "base") */
  paymentNetwork?: string
  /** Required for self-contained RateAgentModal */
  taskTitle?: string
  agentId?: number
  agentName?: string
}

function ScoreDisplay({ score }: { score: number }) {
  const color = score >= 80 ? '#16a34a' : score >= 50 ? '#ca8a04' : '#dc2626'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-gray-200 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="text-sm font-bold" style={{ color }}>{score}/100</span>
    </div>
  )
}

function RatingCard({
  rating,
  label,
  network = 'base',
}: {
  rating: Rating
  label: string
  network?: string
}) {
  const { t } = useTranslation()

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          {label}
        </span>
        <span className="text-xs text-slate-400">
          {new Date(rating.created_at).toLocaleDateString()}
        </span>
      </div>
      <ScoreDisplay score={rating.rating} />
      {rating.comment && (
        <p className="mt-2 text-sm text-slate-600 italic">
          &quot;{rating.comment}&quot;
        </p>
      )}
      {rating.reputation_tx && (
        <a
          href={getExplorerUrl(rating.reputation_tx, network)}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 flex items-center gap-1.5 text-xs hover:opacity-80 transition-opacity"
          style={{ color: '#2563eb' }}
        >
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.172 13.828a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.102 1.101" />
          </svg>
          <span>ERC-8004 Reputation: {truncateHash(rating.reputation_tx)}</span>
          <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      )}
    </div>
  )
}

export function TaskRatings({ taskId, executorId, paymentNetwork, taskTitle, agentId, agentName }: TaskRatingsProps) {
  const { t } = useTranslation()
  const { executor } = useAuth()
  const [ratings, setRatings] = useState<Rating[]>([])
  const [loading, setLoading] = useState(true)
  const [showRateModal, setShowRateModal] = useState(false)

  const fetchRatings = useCallback(async () => {
    try {
      // Fetch ratings + feedback_documents (for reputation_tx) in parallel
      const [ratingsRes, feedbackRes] = await Promise.all([
        supabase
          .from('ratings')
          .select('*')
          .eq('task_id', taskId)
          .order('created_at', { ascending: true }),
        supabase
          .from('feedback_documents')
          .select('feedback_type, reputation_tx')
          .eq('task_id', taskId)
          .not('reputation_tx', 'is', null)
          .limit(10),
      ])

      if (ratingsRes.error) {
        console.error('[TaskRatings] Error fetching ratings:', ratingsRes.error)
        return
      }

      // Map feedback_type → reputation_tx
      // feedback_type: "worker_rating" = agent rated the worker, "agent_rating" = worker rated the agent
      const txMap: Record<string, string> = {}
      for (const fb of feedbackRes.data || []) {
        if (fb.reputation_tx) {
          const raterType = fb.feedback_type === 'agent_rating' ? 'worker' : 'agent'
          txMap[raterType] = fb.reputation_tx
        }
      }

      // Merge reputation_tx into ratings
      const merged = (ratingsRes.data || []).map((r: Rating) => ({
        ...r,
        reputation_tx: r.reputation_tx || txMap[r.rater_type] || null,
      }))

      setRatings(merged)
    } catch (err) {
      console.error('[TaskRatings] Unexpected error:', err)
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    fetchRatings()
  }, [fetchRatings])

  if (loading) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-20 bg-gray-200 rounded-lg" />
        <div className="h-20 bg-gray-200 rounded-lg" />
      </div>
    )
  }

  const agentToWorker = ratings.find((r) => r.rater_type === 'agent')
  const workerToAgent = ratings.find((r) => r.rater_type === 'worker')

  // Check if current user is the worker and hasn't rated yet
  const currentIsWorker = executor?.id && executorId && executor.id === executorId
  const canRateAgent = currentIsWorker && !workerToAgent

  if (ratings.length === 0 && !canRateAgent) {
    return null
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-700">
        {t('ratings.taskRatings', 'Ratings')}
      </h3>

      {agentToWorker && (
        <RatingCard
          rating={agentToWorker}
          label={t('ratings.agentToWorker', 'Agent rated Worker')}
          network={paymentNetwork}
        />
      )}

      {workerToAgent && (
        <RatingCard
          rating={workerToAgent}
          label={t('ratings.workerToAgent', 'Worker rated Agent')}
          network={paymentNetwork}
        />
      )}

      {canRateAgent && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            e.preventDefault()
            setShowRateModal(true)
          }}
          className="w-full py-2.5 px-4 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          {t('ratings.rateAgent', 'Rate Agent')}
        </button>
      )}

      {showRateModal && (
        <RateAgentModal
          taskId={taskId}
          taskTitle={taskTitle || ''}
          agentId={agentId || 2106}
          agentName={agentName}
          onClose={() => setShowRateModal(false)}
          onSuccess={() => {
            setShowRateModal(false)
            fetchRatings()
          }}
        />
      )}
    </div>
  )
}

export default TaskRatings
