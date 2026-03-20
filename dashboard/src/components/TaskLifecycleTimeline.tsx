/**
 * TaskLifecycleTimeline - Visual vertical timeline showing task progression
 *
 * Displays the lifecycle steps of a task:
 *   Published -> Assigned -> Evidence Submitted -> Completed & Paid
 *
 * Each step shows:
 * - Green circle (completed), blue circle (current), gray circle (pending)
 * - Red circle for cancelled/expired terminal states
 * - Step title + subtitle with date/time
 * - TX hash links for escrow and payment transactions
 */

import { useTranslation } from 'react-i18next'
import type { Task, Submission } from '../types/database'
import { TxHashLink } from './TxLink'

interface TaskLifecycleTimelineProps {
  task: Task
  submissions?: Submission[]
}

type StepStatus = 'completed' | 'current' | 'pending' | 'error'

interface TimelineStep {
  key: string
  titleKey: string
  titleFallback: string
  status: StepStatus
  date?: string | null
  txHash?: string | null
  txLabel?: string
}

function formatStepDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getStepCircleClasses(status: StepStatus): string {
  switch (status) {
    case 'completed':
      return 'bg-green-500 border-green-500'
    case 'current':
      return 'bg-blue-500 border-blue-500'
    case 'error':
      return 'bg-red-500 border-red-500'
    case 'pending':
    default:
      return 'bg-gray-300 border-gray-300'
  }
}

function getStepLineClasses(status: StepStatus): string {
  switch (status) {
    case 'completed':
      return 'bg-green-300'
    case 'current':
      return 'bg-blue-200'
    case 'error':
      return 'bg-red-200'
    case 'pending':
    default:
      return 'bg-gray-200'
  }
}

function getStepTextClasses(status: StepStatus): string {
  switch (status) {
    case 'completed':
      return 'text-gray-900'
    case 'current':
      return 'text-blue-700'
    case 'error':
      return 'text-red-700'
    case 'pending':
    default:
      return 'text-gray-400'
  }
}

function getCheckIcon(): JSX.Element {
  return (
    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

function getErrorIcon(): JSX.Element {
  return (
    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

function buildSteps(task: Task, submissions?: Submission[]): TimelineStep[] {
  const status = task.status
  const isTerminal = status === 'cancelled' || status === 'expired'
  const isCompleted = status === 'completed'
  const isSubmitted = ['submitted', 'verifying', 'completed'].includes(status)
  const isAssigned = Boolean(task.executor_id) || ['accepted', 'in_progress', 'submitted', 'verifying', 'completed', 'disputed'].includes(status)

  // Find the earliest submission date
  const submissionDate = submissions && submissions.length > 0
    ? submissions.reduce((earliest, sub) => {
        if (!earliest) return sub.submitted_at
        return new Date(sub.submitted_at) < new Date(earliest) ? sub.submitted_at : earliest
      }, '' as string)
    : null

  // Find payment TX from submissions
  const paymentTx = submissions?.find(s => s.payment_tx)?.payment_tx || null

  const steps: TimelineStep[] = [
    {
      key: 'published',
      titleKey: 'taskLifecycle.published',
      titleFallback: 'Published',
      status: 'completed',
      date: task.created_at,
    },
    {
      key: 'assigned',
      titleKey: 'taskLifecycle.assigned',
      titleFallback: 'Assigned',
      status: isAssigned
        ? (isSubmitted || isCompleted ? 'completed' : 'current')
        : (isTerminal ? 'error' : 'pending'),
      date: task.assigned_at,
      txHash: task.escrow_tx,
      txLabel: 'Escrow TX',
    },
    {
      key: 'submitted',
      titleKey: 'taskLifecycle.evidenceSubmitted',
      titleFallback: 'Evidence Submitted',
      status: isSubmitted
        ? (isCompleted ? 'completed' : 'current')
        : (isTerminal ? 'error' : 'pending'),
      date: submissionDate,
    },
    {
      key: 'completed',
      titleKey: isTerminal
        ? (status === 'cancelled' ? 'taskLifecycle.cancelled' : 'taskLifecycle.expired')
        : 'taskLifecycle.completedPaid',
      titleFallback: isTerminal
        ? (status === 'cancelled' ? 'Cancelled' : 'Expired')
        : 'Completed & Paid',
      status: isCompleted
        ? 'completed'
        : isTerminal
          ? 'error'
          : 'pending',
      date: isCompleted ? task.completed_at : null,
      txHash: paymentTx,
      txLabel: 'Payment TX',
    },
  ]

  return steps
}

export function TaskLifecycleTimeline({ task, submissions }: TaskLifecycleTimelineProps) {
  const { t } = useTranslation()
  const steps = buildSteps(task, submissions)

  return (
    <section>
      <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
        {t('taskLifecycle.title', 'Task Lifecycle')}
      </h2>
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="relative">
          {steps.map((step, index) => {
            const isLast = index === steps.length - 1

            return (
              <div key={step.key} className="relative flex gap-3">
                {/* Vertical line + circle column */}
                <div className="flex flex-col items-center">
                  {/* Circle */}
                  <div
                    className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${getStepCircleClasses(step.status)}`}
                  >
                    {step.status === 'completed' && getCheckIcon()}
                    {step.status === 'error' && getErrorIcon()}
                    {step.status === 'current' && (
                      <div className="w-2 h-2 bg-white rounded-full" />
                    )}
                  </div>
                  {/* Connecting line */}
                  {!isLast && (
                    <div
                      className={`w-0.5 flex-1 min-h-[24px] ${getStepLineClasses(step.status)}`}
                    />
                  )}
                </div>

                {/* Content */}
                <div className={`pb-4 ${isLast ? 'pb-0' : ''}`}>
                  <p className={`text-sm font-medium ${getStepTextClasses(step.status)}`}>
                    {t(step.titleKey, step.titleFallback)}
                  </p>
                  {step.date && (
                    <p className="text-xs text-gray-500 mt-0.5">
                      {formatStepDate(step.date)}
                    </p>
                  )}
                  {step.txHash && (
                    <div className="mt-1 flex items-center gap-1.5">
                      <span className="text-xs text-gray-400">{step.txLabel}:</span>
                      <TxHashLink
                        txHash={step.txHash}
                        network={task.payment_network || 'base'}
                      />
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default TaskLifecycleTimeline
