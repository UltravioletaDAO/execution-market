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
import { TxLink } from './TxLink'
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

function scoreToStars(score: number): number {
  return Math.max(1, Math.min(5, Math.round(score / 20)))
}

function StarDisplay({ score }: { score: number }) {
  const stars = scoreToStars(score)

  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <svg
          key={s}
          className={`w-4 h-4 ${s <= stars ? 'text-yellow-400' : 'text-gray-300'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="ml-1.5 text-sm font-medium text-slate-600">{score ?? 0}/100</span>
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
      <StarDisplay score={rating.rating} />
      {rating.comment && (
        <p className="mt-2 text-sm text-slate-600 italic">
          &quot;{rating.comment}&quot;
        </p>
      )}
      {rating.reputation_tx && (
        <div className="mt-2 flex items-center gap-1.5">
          <span className="text-xs text-slate-500">{t('ratings.onChain', 'On-chain')}:</span>
          <TxLink txHash={rating.reputation_tx} network={network} className="text-xs" />
        </div>
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
      const { data, error } = await supabase
        .from('ratings')
        .select('*')
        .eq('task_id', taskId)
        .order('created_at', { ascending: true })

      if (error) {
        console.error('[TaskRatings] Error fetching ratings:', error)
        return
      }
      setRatings(data || [])
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
