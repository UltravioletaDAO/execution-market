/**
 * TaskRatings: Bidirectional ratings display for a completed task.
 *
 * Shows agent->worker and worker->agent ratings with scores and comments.
 * "Rate Agent" button for workers who haven't rated yet.
 * Uses React Query (useTaskRatings) for caching + invalidation — same pattern as mobile.
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { useTaskRatings, type RatingEntry } from '../hooks/useTaskRatings'
import { getExplorerUrl, truncateHash } from '../utils/blockchain'
import { RateAgentModal } from './RateAgentModal'

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
  rating: RatingEntry
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

function NoRatingPlaceholder({ label }: { label: string }) {
  const { t } = useTranslation()
  return (
    <div className="bg-white rounded-lg border border-dashed border-slate-200 p-4">
      <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
        {label}
      </span>
      <p className="mt-1 text-sm text-slate-400">
        {t('ratings.noRatingYet', 'No rating yet')}
      </p>
    </div>
  )
}

export function TaskRatings({ taskId, executorId, paymentNetwork, taskTitle, agentId, agentName }: TaskRatingsProps) {
  const { t } = useTranslation()
  const { executor } = useAuth()
  const queryClient = useQueryClient()
  const [showRateModal, setShowRateModal] = useState(false)
  const [resolvedAgentId, setResolvedAgentId] = useState<number | undefined>(agentId)

  // Fetch ratings via React Query (same pattern as mobile useTaskRatings)
  const { data: taskRatings, isLoading } = useTaskRatings(taskId)

  // Resolve agent ID from API when not provided via props
  useEffect(() => {
    if (agentId) {
      setResolvedAgentId(agentId)
      return
    }
    const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'
    fetch(`${API_BASE}/api/v1/tasks/${taskId}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.erc8004_agent_id) {
          setResolvedAgentId(Number(data.erc8004_agent_id))
        }
      })
      .catch(() => {})
  }, [taskId, agentId])

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-20 bg-gray-200 rounded-lg" />
        <div className="h-20 bg-gray-200 rounded-lg" />
      </div>
    )
  }

  const agentToWorker = taskRatings?.agentRating ?? null
  const workerToAgent = taskRatings?.workerRating ?? null

  // Check if current user is the worker and hasn't rated yet
  const currentIsWorker = executor?.id && executorId && executor.id === executorId
  const canRateAgent = currentIsWorker && !workerToAgent

  // Show nothing only if no ratings exist AND user can't rate
  if (!agentToWorker && !workerToAgent && !canRateAgent) {
    return null
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-700">
        {t('ratings.taskRatings', 'Ratings')}
      </h3>

      {/* Agent rated Worker */}
      {agentToWorker ? (
        <RatingCard
          rating={agentToWorker}
          label={t('ratings.agentToWorker', 'Agent rated Worker')}
          network={paymentNetwork}
        />
      ) : currentIsWorker ? (
        <NoRatingPlaceholder label={t('ratings.agentToWorker', 'Agent rated Worker')} />
      ) : null}

      {/* Worker rated Agent */}
      {workerToAgent ? (
        <RatingCard
          rating={workerToAgent}
          label={t('ratings.workerToAgent', 'Worker rated Agent')}
          network={paymentNetwork}
        />
      ) : canRateAgent && resolvedAgentId ? (
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
      ) : null}

      {showRateModal && resolvedAgentId && (
        <RateAgentModal
          taskId={taskId}
          taskTitle={taskTitle || ''}
          agentId={resolvedAgentId}
          agentName={agentName}
          onClose={() => setShowRateModal(false)}
          onSuccess={() => {
            setShowRateModal(false)
            // Invalidate React Query cache → forces refetch from DB (same as mobile)
            queryClient.invalidateQueries({ queryKey: ['ratings', 'task', taskId] })
          }}
        />
      )}
    </div>
  )
}

export default TaskRatings
