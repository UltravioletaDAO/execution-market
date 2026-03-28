/**
 * PaymentStatus - Payment/escrow status display for tasks
 *
 * Shows workers and agents the current status of payments:
 * - Status badge (pending, escrowed, partial_released, completed, refunded)
 * - Amount display in USDC
 * - Progress bar for partial releases
 * - Transaction hash links (to BaseScan)
 * - Timeline of payment events
 *
 * NOW-030: Payment status component
 */

import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { TX_EXPLORER_URLS, ADDRESS_EXPLORER_URLS } from '../utils/blockchain'

// Types
export type PaymentStatusType =
  | 'pending'           // Esperando deposito del agente
  | 'escrowed'          // Fondos en escrow, tarea activa
  | 'partial_released'  // Pago parcial liberado
  | 'completed'         // Pago completo liberado
  | 'refunded'          // Reembolsado al agente
  | 'disputed'          // Disputa abierta, fondos retenidos
  | 'charged'           // Pago instantaneo (CHARGE, sin escrow)

export interface PaymentEvent {
  id: string
  type: 'escrow_created' | 'escrow_funded' | 'partial_release' | 'final_release' | 'refund' | 'dispute_hold' | 'instant_charge' | 'dispute_resolved'
  amount?: number
  tx_hash?: string
  network: string
  timestamp: string
  actor: 'agent' | 'executor' | 'system' | 'arbitrator'
  note?: string
}

export interface PaymentData {
  task_id: string
  status: PaymentStatusType
  total_amount: number
  released_amount: number
  currency: string
  escrow_tx?: string
  escrow_contract?: string
  network: string
  events: PaymentEvent[]
  created_at: string
  updated_at: string
}

interface PaymentStatusProps {
  payment: PaymentData
  compact?: boolean
  showTimeline?: boolean
  bountyAmount?: number
}

// Get explorer URL for transaction
function getExplorerUrl(network: string, txHash: string): string {
  return (TX_EXPLORER_URLS[network] || TX_EXPLORER_URLS.base) + txHash
}

// Get contract explorer URL
function getContractUrl(network: string, address: string): string {
  return (ADDRESS_EXPLORER_URLS[network] || ADDRESS_EXPLORER_URLS.base) + address
}

// Format currency
function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency === 'USDC' ? 'USD' : currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  }).format(amount)
}

// Format date
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Format relative time
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} min ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(dateStr)
}

// Truncate hash for display
function truncateHash(hash: string): string {
  return `${hash.slice(0, 8)}...${hash.slice(-6)}`
}

// Status badge component
function StatusBadge({ status }: { status: PaymentStatusType }) {
  const { t } = useTranslation()
  const colors: Record<PaymentStatusType, string> = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    escrowed: 'bg-blue-100 text-blue-800 border-blue-200',
    partial_released: 'bg-purple-100 text-purple-800 border-purple-200',
    completed: 'bg-green-100 text-green-800 border-green-200',
    refunded: 'bg-gray-100 text-gray-800 border-gray-200',
    disputed: 'bg-red-100 text-red-800 border-red-200',
    charged: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  }

  const labels: Record<PaymentStatusType, string> = {
    pending: t('paymentStatus.pending', 'Pending'),
    escrowed: t('paymentStatus.escrowed', 'In Escrow'),
    partial_released: t('paymentStatus.partialReleased', 'Partial Payment'),
    completed: t('paymentStatus.completed', 'Completed'),
    refunded: t('paymentStatus.refunded', 'Refunded'),
    disputed: t('paymentStatus.disputed', 'In Dispute'),
    charged: t('paymentStatus.charged', 'Direct Payment'),
  }

  const icons: Record<PaymentStatusType, JSX.Element> = {
    pending: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    escrowed: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    partial_released: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    completed: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    refunded: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
      </svg>
    ),
    disputed: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    charged: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${colors[status]}`}>
      {icons[status]}
      {labels[status]}
    </span>
  )
}

// Progress bar component for partial releases
function PaymentProgress({
  released,
  total,
  currency,
}: {
  released: number
  total: number
  currency: string
}) {
  const { t } = useTranslation()
  const percentage = total > 0 ? Math.round((released / total) * 100) : 0

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600">{t('paymentStatus.progress', 'Payment progress')}</span>
        <span className="font-medium text-gray-900">{percentage}%</span>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            percentage === 100
              ? 'bg-green-500'
              : percentage > 0
              ? 'bg-blue-500'
              : 'bg-gray-300'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{t('paymentStatus.released', 'Released')}: {formatCurrency(released, currency)}</span>
        <span>{t('paymentStatus.total', 'Total')}: {formatCurrency(total, currency)}</span>
      </div>
    </div>
  )
}

// Timeline event component
function TimelineEvent({ event, network, bountyAmount }: { event: PaymentEvent; network: string; bountyAmount?: number }) {
  const { t } = useTranslation()

  const eventLabels: Record<PaymentEvent['type'], string> = {
    escrow_created: t('paymentStatus.event.escrowCreated', 'Escrow created'),
    escrow_funded: t('paymentStatus.event.escrowFunded', 'Escrow funded'),
    partial_release: t('paymentStatus.event.partialRelease', 'Partial payment'),
    final_release: t('paymentStatus.event.finalRelease', 'Final payment'),
    refund: t('paymentStatus.event.refund', 'Refund'),
    dispute_hold: t('paymentStatus.event.disputeHold', 'Held for dispute'),
    instant_charge: t('paymentStatus.event.instantCharge', 'Instant payment'),
    dispute_resolved: t('paymentStatus.event.disputeResolved', 'Dispute resolved'),
  }

  const eventIcons: Record<PaymentEvent['type'], { bg: string; icon: JSX.Element }> = {
    escrow_created: {
      bg: 'bg-blue-100',
      icon: (
        <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      ),
    },
    escrow_funded: {
      bg: 'bg-green-100',
      icon: (
        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      ),
    },
    partial_release: {
      bg: 'bg-purple-100',
      icon: (
        <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      ),
    },
    final_release: {
      bg: 'bg-green-100',
      icon: (
        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    refund: {
      bg: 'bg-orange-100',
      icon: (
        <svg className="w-4 h-4 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
        </svg>
      ),
    },
    dispute_hold: {
      bg: 'bg-red-100',
      icon: (
        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
    instant_charge: {
      bg: 'bg-emerald-100',
      icon: (
        <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
    },
    dispute_resolved: {
      bg: 'bg-indigo-100',
      icon: (
        <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
        </svg>
      ),
    },
  }

  const actorLabels: Record<PaymentEvent['actor'], string> = {
    agent: t('paymentStatus.actor.agent', 'Agent'),
    executor: t('paymentStatus.actor.executor', 'Executor'),
    system: t('paymentStatus.actor.system', 'System'),
    arbitrator: t('paymentStatus.actor.arbitrator', 'Arbitrator'),
  }

  const { bg, icon } = eventIcons[event.type]

  return (
    <div className="relative flex gap-3 pb-6 last:pb-0">
      {/* Timeline line */}
      <div className="absolute top-6 left-4 bottom-0 w-0.5 bg-gray-200 last:hidden" />

      {/* Icon */}
      <div className={`relative flex-shrink-0 w-8 h-8 rounded-full ${bg} flex items-center justify-center`}>
        {icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-gray-900">
              {eventLabels[event.type]}
            </p>
            <p className="text-xs text-gray-500">
              {actorLabels[event.actor]} - {formatRelativeTime(event.timestamp)}
            </p>
          </div>
          {event.amount !== undefined && event.amount > 0 && (
            <span className={`text-sm font-semibold ${
              event.type === 'refund' ? 'text-orange-600' : 'text-green-600'
            }`}>
              {event.type === 'refund' ? '-' : '+'}
              {formatCurrency(
                event.type === 'escrow_created' && bountyAmount ? bountyAmount : event.amount,
                'USDC'
              )}
            </span>
          )}
        </div>

        {/* Note */}
        {event.note && (
          <p className="mt-1 text-xs text-gray-600">{event.note}</p>
        )}

        {/* Transaction hash */}
        {event.tx_hash && (
          <a
            href={getExplorerUrl(event.network || network, event.tx_hash)}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1.5 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 transition-colors"
          >
            <span className="font-mono">{truncateHash(event.tx_hash)}</span>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        )}
      </div>
    </div>
  )
}

// Payment timeline component
function PaymentTimeline({ events, network, bountyAmount }: { events: PaymentEvent[]; network: string; bountyAmount?: number }) {
  const { t } = useTranslation()

  // Sort events by timestamp (oldest first — chronological timeline)
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
  }, [events])

  if (events.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        {t('payment.noEvents', 'No hay eventos de pago aun')}
      </div>
    )
  }

  return (
    <div className="p-4">
      {sortedEvents.map((event) => (
        <TimelineEvent key={event.id} event={event} network={network} bountyAmount={bountyAmount} />
      ))}
    </div>
  )
}

// Main PaymentStatus component
export function PaymentStatus({
  payment,
  compact = false,
  showTimeline = true,
  bountyAmount,
}: PaymentStatusProps) {
  const { t } = useTranslation()

  // Use bountyAmount (task.bounty_usd) when available — total_amount from payment_events
  // can include fees and rounding that shouldn't be shown as the bounty
  const displayAmount = bountyAmount ?? payment.total_amount

  const hasPartialRelease = payment.released_amount > 0 && payment.released_amount < payment.total_amount
  const isComplete = payment.status === 'completed' || payment.released_amount >= payment.total_amount

  // Compact view for inline display
  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <StatusBadge status={payment.status} />
        <div className="text-sm">
          <span className="font-semibold text-gray-900">
            {formatCurrency(displayAmount, payment.currency)}
          </span>
          {hasPartialRelease && (
            <span className="text-gray-500 ml-1">
              ({Math.round((payment.released_amount / displayAmount) * 100)}% liberado)
            </span>
          )}
        </div>
        {payment.escrow_tx && (
          <a
            href={getExplorerUrl(payment.network, payment.escrow_tx)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700"
            title={`Ver en explorer (${payment.network})`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        )}
      </div>
    )
  }

  // Full view
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-1">
              {t('payment.status', 'Estado del Pago')}
            </h3>
            <StatusBadge status={payment.status} />
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(displayAmount, payment.currency)}
            </p>
            <p className="text-xs text-gray-500">{payment.currency}</p>
          </div>
        </div>

        {/* Progress bar for partial releases */}
        {(hasPartialRelease || payment.status === 'partial_released') && (
          <PaymentProgress
            released={payment.released_amount}
            total={displayAmount}
            currency={payment.currency}
          />
        )}
      </div>

      {/* Details */}
      <div className="p-4 border-b border-gray-100 bg-gray-50">
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500">{t('payment.network', 'Red')}</dt>
            <dd className="font-medium text-gray-900 capitalize">{payment.network.replace('-', ' ')}</dd>
          </div>
          <div>
            <dt className="text-gray-500">{t('payment.updated', 'Actualizado')}</dt>
            <dd className="font-medium text-gray-900">{formatRelativeTime(payment.updated_at)}</dd>
          </div>
          {/* Escrow TX is already shown in the timeline below — removed from details to avoid duplication */}
          {payment.escrow_contract && (
            <div className="col-span-2">
              <dt className="text-gray-500 mb-1">{t('payment.escrowContract', 'Contrato de Escrow')}</dt>
              <dd>
                <a
                  href={getContractUrl(payment.network, payment.escrow_contract)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-mono text-sm text-blue-600 hover:text-blue-700 transition-colors"
                >
                  {truncateHash(payment.escrow_contract)}
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </dd>
            </div>
          )}
        </dl>
      </div>

      {/* Timeline */}
      {showTimeline && (
        <div>
          <div className="px-4 py-3 border-b border-gray-100">
            <h4 className="text-sm font-medium text-gray-700">
              {t('payment.timeline', 'Historial de Pagos')}
            </h4>
          </div>
          <PaymentTimeline events={payment.events} network={payment.network} bountyAmount={bountyAmount} />
        </div>
      )}

      {/* Status message */}
      {payment.status === 'pending' && (
        <div className="p-4 bg-yellow-50 border-t border-yellow-100">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-yellow-800">
                {t('payment.awaitingEscrow', 'Esperando deposito en escrow')}
              </p>
              <p className="text-xs text-yellow-700 mt-0.5">
                {t('payment.awaitingEscrowDesc', 'El agente debe depositar los fondos antes de que puedas comenzar la tarea.')}
              </p>
            </div>
          </div>
        </div>
      )}

      {payment.status === 'escrowed' && (
        <div className="p-4 bg-blue-50 border-t border-blue-100">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-blue-800">
                {t('payment.fundsSecured', 'Fondos asegurados')}
              </p>
              <p className="text-xs text-blue-700 mt-0.5">
                {t('payment.fundsSecuredDesc', 'Los fondos estan en escrow y seran liberados cuando completes la tarea.')}
              </p>
            </div>
          </div>
        </div>
      )}

      {isComplete && (
        <div className="p-4 bg-green-50 border-t border-green-100">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-green-800">
                {t('payment.complete', 'Pago completado')}
              </p>
              <p className="text-xs text-green-700 mt-0.5">
                {t('payment.completeDesc', 'Todos los fondos han sido liberados a tu wallet.')}
              </p>
            </div>
          </div>
        </div>
      )}

      {payment.status === 'disputed' && (
        <div className="p-4 bg-red-50 border-t border-red-100">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-red-800">
                {t('payment.disputed', 'Disputa abierta')}
              </p>
              <p className="text-xs text-red-700 mt-0.5">
                {t('payment.disputedDesc', 'Los fondos estan retenidos mientras el panel de arbitraje revisa la evidencia.')}
              </p>
            </div>
          </div>
        </div>
      )}

      {payment.status === 'charged' && (
        <div className="p-4 bg-emerald-50 border-t border-emerald-100">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.381z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-emerald-800">
                {t('payment.charged', 'Pago instantaneo completado')}
              </p>
              <p className="text-xs text-emerald-700 mt-0.5">
                {t('payment.chargedDesc', 'Pago directo (CHARGE) sin escrow. Fondos enviados directamente.')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Export sub-components for flexibility
export { PaymentTimeline, StatusBadge as PaymentStatusBadge, PaymentProgress }

export default PaymentStatus
