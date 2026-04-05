/**
 * TaskDetailModal: Modal for viewing task details, submissions, and status.
 *
 * Used when agents click "View Task" from the dashboard or task management.
 * Shows task info, evidence requirements, submissions list, and payment status.
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import { getWorldIdBountyThreshold } from '../hooks/usePlatformConfig'
import { TxHashLink } from './TxLink'
import { TaskRatings } from './TaskRatings'
import type { Task, Submission } from '../types/database'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface TaskDetailModalProps {
  taskId: string
  onClose: () => void
  onReviewSubmission?: (submissionId: string) => void
}

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------

export function TaskDetailModal({ taskId, onClose, onReviewSubmission }: TaskDetailModalProps) {
  const { t } = useTranslation()
  const [task, setTask] = useState<Task | null>(null)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        setError(null)

        const [taskRes, subsRes] = await Promise.all([
          supabase.from('tasks').select('*').eq('id', taskId).single(),
          supabase.from('submissions')
            .select('*, executor:executors(id, display_name, reputation_score)')
            .eq('task_id', taskId)
            .order('submitted_at', { ascending: false }),
        ])

        if (!cancelled) {
          if (taskRes.error || !taskRes.data) {
            setError('Task not found')
          } else {
            setTask(taskRes.data)
            setSubmissions(subsRes.data || [])
          }
        }
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load task')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [taskId])

  // Auto-refresh on task status changes (avoids stale "reviewing" state)
  useEffect(() => {
    const channel = supabase
      .channel(`task-updates-${taskId}`)
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'tasks', filter: `id=eq.${taskId}` },
        (payload: { new: Record<string, unknown> }) => {
          setTask((prev) => prev ? { ...prev, ...payload.new } as Task : prev)
        }
      )
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [taskId])

  // Auto-refresh submissions on any change
  useEffect(() => {
    const channel = supabase
      .channel(`submissions-${taskId}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'submissions', filter: `task_id=eq.${taskId}` },
        () => {
          supabase.from('submissions')
            .select('*, executor:executors(id, display_name, reputation_score)')
            .eq('task_id', taskId)
            .order('submitted_at', { ascending: false })
            .then(({ data }: { data: Submission[] | null }) => { if (data) setSubmissions(data) })
        }
      )
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [taskId])

  const statusColors: Record<string, string> = {
    published: 'bg-green-100 text-green-700',
    accepted: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-yellow-100 text-yellow-700',
    submitted: 'bg-purple-100 text-purple-700',
    verifying: 'bg-purple-100 text-purple-700',
    completed: 'bg-emerald-100 text-emerald-700',
    cancelled: 'bg-red-100 text-red-700',
    expired: 'bg-gray-100 text-gray-700',
    disputed: 'bg-orange-100 text-orange-700',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-xl z-10">
          <h2 className="text-lg font-semibold text-gray-900">{t('tasks.details')}</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-4 space-y-5">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <svg className="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="ml-3 text-gray-500">{t('common.loading')}</span>
            </div>
          )}

          {error && !loading && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {task && !loading && (
            <>
              {/* Task header */}
              <div>
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-lg font-medium text-gray-900">{task.title}</h3>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap ${statusColors[task.status] || 'bg-gray-100 text-gray-700'}`}>
                    {task.status}
                  </span>
                </div>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span>${task.bounty_usd?.toFixed(2)} USDC</span>
                  <span>{task.category}</span>
                  <span>{task.payment_network || 'base'}</span>
                </div>
              </div>

              {/* World ID required banner for high-value tasks */}
              {task.bounty_usd >= getWorldIdBountyThreshold() && (
                <div className="flex items-center gap-2 px-4 py-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-800 dark:text-green-300">
                  <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{t('worldId.requiredExplainer', 'This task requires World ID verification to apply.')}</span>
                </div>
              )}

              {/* Instructions */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">{t('tasks.instructions')}</h4>
                <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">
                  {task.instructions || 'No instructions provided'}
                </p>
              </div>

              {/* Evidence requirements */}
              {task.evidence_schema && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">{t('tasks.evidence')}</h4>
                  <div className="flex flex-wrap gap-2">
                    {(task.evidence_schema?.required || []).map((r: string) => (
                      <span key={r} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500 text-xs">{t('taskMgmt.created', 'Created')}</p>
                  <p className="text-gray-900">{new Date(task.created_at).toLocaleString()}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500 text-xs">Deadline</p>
                  <p className="text-gray-900">{task.deadline ? new Date(task.deadline).toLocaleString() : 'N/A'}</p>
                </div>
                {task.location_hint && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500 text-xs">{t('tasks.location')}</p>
                    <p className="text-gray-900">{task.location_hint}</p>
                  </div>
                )}
                {task.escrow_tx && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500 text-xs">Escrow</p>
                    <TxHashLink txHash={task.escrow_tx} network={(task as unknown as Record<string, unknown>).payment_network as string || 'base'} />
                  </div>
                )}
              </div>

              {/* Submissions */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  {t('taskDetail.submissions', 'Submissions')} ({submissions.length})
                </h4>
                {submissions.length === 0 ? (
                  <p className="text-sm text-gray-400 italic">{t('taskDetail.noSubmissions', 'No submissions yet')}</p>
                ) : (
                  <div className="space-y-2">
                    {submissions.map((sub: Submission) => (
                      <div
                        key={sub.id}
                        className="border border-gray-200 rounded-lg p-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                      >
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {sub.executor?.display_name || 'Worker'}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(sub.submitted_at).toLocaleString()}
                            {sub.agent_verdict && (
                              <span className={`ml-2 ${
                                sub.agent_verdict === 'accepted' ? 'text-green-600' :
                                sub.agent_verdict === 'disputed' ? 'text-red-600' : 'text-yellow-600'
                              }`}>
                                {sub.agent_verdict}
                              </span>
                            )}
                          </p>
                        </div>
                        {onReviewSubmission && !sub.agent_verdict && (
                          <button
                            onClick={() => onReviewSubmission(sub.id)}
                            className="px-3 py-1.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-lg hover:bg-purple-200 transition-colors"
                          >
                            {t('taskMgmt.review', 'Review')}
                          </button>
                        )}
                        {sub.payment_tx && (
                          <TxHashLink txHash={sub.payment_tx} network={(task as unknown as Record<string, unknown>).payment_network as string || 'base'} className="text-xs" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Ratings (shown for completed tasks) */}
              {task.status === 'completed' && (
                <TaskRatings
                  taskId={task.id}
                  executorId={task.executor_id ?? undefined}
                  paymentNetwork={task.payment_network}
                  taskTitle={task.title}
                  agentId={task.erc8004_agent_id ? Number(task.erc8004_agent_id) : undefined}
                  agentName={task.agent_name ?? undefined}
                />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-3 rounded-b-xl">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-400">ID: {taskId.slice(0, 8)}...</p>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
            >
              {t('common.close')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
