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
import { Pill } from './ui/Pill'
import { Spinner } from './ui/Spinner'
import { StatusBadge } from './ui/StatusBadge'
import { Modal } from './ui/Modal'
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

  return (
    <Modal open onClose={onClose} size="lg" labelledBy="task-detail-title">
      <Modal.Header id="task-detail-title" onClose={onClose}>
        {t('tasks.details')}
      </Modal.Header>

      <Modal.Body className="space-y-5">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" className="text-zinc-700" label={t('common.loading')} />
              <span className="ml-3 text-zinc-500">{t('common.loading')}</span>
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
                  <StatusBadge status={task.status} size="sm" label={task.status} />
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
                      <Pill key={r} variant="default" size="sm" asSpan>
                        {r}
                      </Pill>
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
      </Modal.Body>

      <Modal.Footer className="justify-between">
        <p className="text-xs text-zinc-400">ID: {taskId.slice(0, 8)}...</p>
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-200 rounded-lg transition-colors"
        >
          {t('common.close')}
        </button>
      </Modal.Footer>
    </Modal>
  )
}
