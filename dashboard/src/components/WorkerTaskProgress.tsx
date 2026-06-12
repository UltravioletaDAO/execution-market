// Worker-side lifecycle view: the same event timeline the publisher sees, plus
// a banner when the publisher asked for a revision or rejected the evidence —
// so the worker knows what happened and what to do next (resubmit / nothing).
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import type { Task, Submission } from '../types/database'
import { getMySubmissions } from '../services/submissions'
import { ratePublisher } from '../services/h2a'
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

  // Worker -> publisher rating (on-chain, gasless). One-way per task.
  const [rateScore, setRateScore] = useState(0)
  const [rated, setRated] = useState(false)
  const [ratingBusy, setRatingBusy] = useState(false)
  const [rateError, setRateError] = useState<string | null>(null)

  const submitPublisherRating = async () => {
    if (rateScore === 0) return
    setRatingBusy(true)
    setRateError(null)
    try {
      await ratePublisher(task.id, rateScore)
      setRated(true)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Error'
      if (/already|rated|duplicate/i.test(msg)) setRated(true)
      else setRateError(msg)
    } finally {
      setRatingBusy(false)
    }
  }

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
      {task.status === 'completed' && (
        <div className="rounded-lg border border-zinc-200 bg-white p-4">
          {rated ? (
            <p className="text-sm text-zinc-700">
              ★ {t('worker.publisherRated', 'Gracias — tu calificación del publicador quedó on-chain (ERC-8004).')}
            </p>
          ) : (
            <>
              <p className="text-sm font-semibold text-zinc-900 mb-1">
                {t('worker.ratePublisher', 'Califica al publicador')}
              </p>
              <p className="text-xs text-zinc-500 mb-2">
                {t('worker.ratePublisherHint', 'Tu calificación queda on-chain (ERC-8004) — es parte del trustless. Una sola vez por tarea.')}
              </p>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRateScore(star)}
                    disabled={ratingBusy}
                    aria-label={t('worker.ratePublisherStar', '{{n}} estrellas', { n: star })}
                    className="text-2xl leading-none transition-transform hover:scale-110 disabled:opacity-50"
                  >
                    <span className={star <= rateScore ? 'text-amber-500' : 'text-zinc-300'}>★</span>
                  </button>
                ))}
                <button
                  type="button"
                  onClick={submitPublisherRating}
                  disabled={ratingBusy || rateScore === 0}
                  className="ml-3 rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
                >
                  {ratingBusy ? t('worker.rating', 'Enviando…') : t('worker.rateSubmit', 'Calificar')}
                </button>
              </div>
              {rateError && <p className="mt-2 text-xs text-red-600">{rateError}</p>}
            </>
          )}
        </div>
      )}

      <TaskLifecycleTimeline task={task} submissions={submissions} />
    </div>
  )
}

export default WorkerTaskProgress
