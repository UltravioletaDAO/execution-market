// Worker-side lifecycle view: the same event timeline the publisher sees, plus
// a banner when the publisher asked for a revision or rejected the evidence —
// so the worker knows what happened and what to do next (resubmit / nothing).
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import type { Task, Submission } from '../types/database'
import { getMySubmissions } from '../services/submissions'
import { isVerdictNeedsRevision, isVerdictRejected } from '../lib/verificationContract'
import { TaskLifecycleTimeline } from './TaskLifecycleTimeline'

export function WorkerTaskProgress({ task, executorId }: { task: Task; executorId: string }) {
  const { t } = useTranslation()
  const [submissions, setSubmissions] = useState<Submission[]>([])

  useEffect(() => {
    let cancelled = false
    getMySubmissions(executorId)
      .then((subs) => {
        if (cancelled) return
        // Only this task's submissions — getMySubmissions spans all of them.
        setSubmissions(subs.filter((s) => s.task_id === task.id) as Submission[])
      })
      .catch(() => {
        // Non-blocking: the timeline still renders from the task alone.
      })
    return () => {
      cancelled = true
    }
  }, [task.id, task.status, executorId])

  // The worker's most recent submission drives the review banner.
  const latest = submissions
    .slice()
    .sort((a, b) => new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime())[0]
  const needsRevision = latest != null && isVerdictNeedsRevision(latest.agent_verdict)
  const rejected = latest != null && isVerdictRejected(latest.agent_verdict)

  return (
    <div className="space-y-4">
      {needsRevision && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-900">
            {t('worker.revisionRequested', 'El publicador pidió cambios')}
          </p>
          {latest?.agent_notes && (
            <p className="mt-1 text-sm text-amber-800 whitespace-pre-wrap break-words">
              {latest.agent_notes}
            </p>
          )}
          <p className="mt-2 text-xs text-amber-700">
            {t(
              'worker.revisionHint',
              'Corrige la evidencia y vuelve a enviarla con el botón de abajo. El pago sigue retenido en el escrow para ti.',
            )}
          </p>
        </div>
      )}
      {rejected && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4">
          <p className="text-sm font-semibold text-red-900">
            {t('worker.submissionRejected', 'Tu evidencia fue rechazada')}
          </p>
          {latest?.agent_notes && (
            <p className="mt-1 text-sm text-red-800 whitespace-pre-wrap break-words">
              {latest.agent_notes}
            </p>
          )}
          <p className="mt-2 text-xs text-red-700">
            {t(
              'worker.rejectedHint',
              'El pago se devolvió al publicador y la tarea se cerró. No requiere ninguna acción de tu parte.',
            )}
          </p>
        </div>
      )}
      <TaskLifecycleTimeline task={task} submissions={submissions} />
    </div>
  )
}

export default WorkerTaskProgress
