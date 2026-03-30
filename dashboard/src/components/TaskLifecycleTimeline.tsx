/**
 * TaskLifecycleTimeline - Unified vertical timeline showing task progression + payment
 *
 * Displays the lifecycle steps of a task:
 *   Published -> Assigned -> Evidence Submitted -> Completed & Paid
 *
 * Each step shows:
 * - Green circle (completed), blue circle (current), gray circle (pending)
 * - Red circle for cancelled/expired terminal states
 * - Step title + subtitle with date/time
 * - TX hash links for escrow and payment transactions
 * - Inline payment details (network, token, amount, status) at relevant steps
 */

import { useTranslation } from 'react-i18next'
import type { Task, Submission } from '../types/database'
import { TxHashLink } from './TxLink'
import { NetworkBadge } from './ui/NetworkBadge'
import type { PaymentData } from './PaymentStatus'

interface TaskLifecycleTimelineProps {
  task: Task
  submissions?: Submission[]
  payment?: PaymentData | null
  paymentLoading?: boolean
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
  extraTx?: { hash: string; label: string } | null
  /** Inline payment/network details to show below this step */
  inlineDetails?: InlineDetail[]
}

interface InlineDetail {
  type: 'network-badge' | 'text' | 'status-badge'
  label: string
  network?: string
  token?: string
  value?: string
  colorClass?: string
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

function formatPaymentAmount(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency === 'USDC' ? 'USD' : currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  }).format(amount)
}

function getPaymentStatusColor(status: string): string {
  switch (status) {
    case 'completed': return 'text-green-700 bg-green-100'
    case 'escrowed': return 'text-blue-700 bg-blue-100'
    case 'refunded': return 'text-gray-700 bg-gray-100'
    case 'disputed': return 'text-red-700 bg-red-100'
    case 'pending': return 'text-yellow-700 bg-yellow-100'
    case 'charged': return 'text-emerald-700 bg-emerald-100'
    default: return 'text-gray-700 bg-gray-100'
  }
}

function getPaymentStatusLabel(status: string, t: (key: string, fallback: string) => string): string {
  switch (status) {
    case 'completed': return t('paymentStatus.completed', 'Completed')
    case 'escrowed': return t('paymentStatus.escrowed', 'In Escrow')
    case 'refunded': return t('paymentStatus.refunded', 'Refunded')
    case 'disputed': return t('paymentStatus.disputed', 'In Dispute')
    case 'pending': return t('paymentStatus.pending', 'Pending')
    case 'charged': return t('paymentStatus.charged', 'Direct Payment')
    case 'partial_released': return t('paymentStatus.partialReleased', 'Partial Payment')
    default: return status
  }
}

function buildSteps(task: Task, submissions?: Submission[], payment?: PaymentData | null): TimelineStep[] {
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

  // Inline details for the "Assigned" step (network badge already in header, not repeated)
  const assignedDetails: InlineDetail[] = []

  // Build inline details for the "Completed" step: payment amount + status
  const completedDetails: InlineDetail[] = []
  if (isCompleted && payment) {
    const displayAmount = task.bounty_usd ?? payment.total_amount
    completedDetails.push({
      type: 'text',
      label: 'Amount',
      value: formatPaymentAmount(displayAmount, payment.currency),
      colorClass: 'text-green-700 font-semibold',
    })
    completedDetails.push({
      type: 'status-badge',
      label: 'Payment',
      value: payment.status,
    })
  }

  // For terminal states (cancelled/expired) show refund info
  const terminalDetails: InlineDetail[] = []
  if (isTerminal && payment) {
    if (payment.status === 'refunded') {
      terminalDetails.push({
        type: 'status-badge',
        label: 'Payment',
        value: 'refunded',
      })
    }
  }

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
      inlineDetails: assignedDetails.length > 0 ? assignedDetails : undefined,
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
      extraTx: task.refund_tx ? { hash: task.refund_tx, label: 'Refund TX' } : null,
      inlineDetails: isTerminal
        ? (terminalDetails.length > 0 ? terminalDetails : undefined)
        : (completedDetails.length > 0 ? completedDetails : undefined),
    },
  ]

  return steps
}

export function TaskLifecycleTimeline({ task, submissions, payment, paymentLoading }: TaskLifecycleTimelineProps) {
  const { t } = useTranslation()
  const steps = buildSteps(task, submissions, payment)

  return (
    <section>
      <div className="flex items-center gap-3 mb-3">
        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
          {t('taskLifecycle.title', 'Task Lifecycle')}
        </h2>
        {task.skill_version && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono bg-indigo-50 text-indigo-700 border border-indigo-200">
            skill v{task.skill_version}
          </span>
        )}
      </div>
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
                  {step.extraTx && (
                    <div className="mt-1 flex items-center gap-1.5">
                      <span className="text-xs text-gray-400">{step.extraTx.label}:</span>
                      <TxHashLink
                        txHash={step.extraTx.hash}
                        network={task.payment_network || 'base'}
                      />
                    </div>
                  )}
                  {/* Inline payment/network details */}
                  {step.inlineDetails && step.inlineDetails.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap items-center gap-2">
                      {step.inlineDetails.map((detail, di) => {
                        if (detail.type === 'network-badge') {
                          return (
                            <NetworkBadge
                              key={di}
                              network={detail.network!}
                              token={detail.token}
                              size="sm"
                            />
                          )
                        }
                        if (detail.type === 'status-badge') {
                          return (
                            <span
                              key={di}
                              className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${getPaymentStatusColor(detail.value || '')}`}
                            >
                              {getPaymentStatusLabel(detail.value || '', t)}
                            </span>
                          )
                        }
                        // text type
                        return (
                          <span key={di} className={`text-xs ${detail.colorClass || 'text-gray-600'}`}>
                            {detail.value}
                          </span>
                        )
                      })}
                    </div>
                  )}
                  {/* Payment loading indicator at the completed step */}
                  {step.key === 'completed' && paymentLoading && (
                    <div className="mt-1.5 flex items-center gap-2">
                      <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                      <span className="text-xs text-gray-400">{t('taskDetail.loadingPayment', 'Loading payment status...')}</span>
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
