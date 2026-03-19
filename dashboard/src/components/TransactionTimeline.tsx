/**
 * TransactionTimeline - Shows chronological on-chain transaction history for a task
 *
 * Fetches from GET /api/v1/tasks/{taskId}/transactions (payment_events audit trail)
 * and displays each TX with explorer link, amount, status, and label.
 */

import { useTranslation } from 'react-i18next'
import { useTaskTransactions, type TransactionEvent } from '../hooks/useTaskTransactions'
import { TxHashLink } from './TxLink'

// Icons per event type category
function EventIcon({ eventType, status }: { eventType: string; status: string }) {
  const failed = status === 'failed'
  const baseClass = `w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
    failed ? 'bg-red-100' : 'bg-blue-50'
  }`

  if (eventType.includes('escrow_authorize') || eventType === 'balance_check') {
    return (
      <div className={baseClass}>
        <svg className={`w-4 h-4 ${failed ? 'text-red-500' : 'text-blue-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </div>
    )
  }

  if (eventType.includes('release') || eventType.includes('disburse_worker') || eventType.includes('settle')) {
    return (
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${failed ? 'bg-red-100' : 'bg-green-100'}`}>
        <svg className={`w-4 h-4 ${failed ? 'text-red-500' : 'text-green-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
    )
  }

  if (eventType.includes('refund')) {
    return (
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${failed ? 'bg-red-100' : 'bg-yellow-100'}`}>
        <svg className={`w-4 h-4 ${failed ? 'text-red-500' : 'text-yellow-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
        </svg>
      </div>
    )
  }

  if (eventType.includes('fee') || eventType.includes('disburse_fee')) {
    return (
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${failed ? 'bg-red-100' : 'bg-purple-100'}`}>
        <svg className={`w-4 h-4 ${failed ? 'text-red-500' : 'text-purple-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      </div>
    )
  }

  if (eventType.includes('reputation')) {
    return (
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${failed ? 'bg-red-100' : 'bg-amber-100'}`}>
        <svg className={`w-4 h-4 ${failed ? 'text-red-500' : 'text-amber-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
        </svg>
      </div>
    )
  }

  // Default
  return (
    <div className={baseClass}>
      <svg className={`w-4 h-4 ${failed ? 'text-red-500' : 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  const colors: Record<string, string> = {
    success: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    pending: 'bg-yellow-100 text-yellow-700',
  }
  const labels: Record<string, string> = {
    success: t('txTimeline.confirmed', 'Confirmed'),
    failed: t('txTimeline.failed', 'Failed'),
    pending: t('txTimeline.pending', 'Pending'),
  }
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
      {labels[status] || status}
    </span>
  )
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleString('es-CO', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return ts
  }
}

function TransactionRow({ tx, isLast }: { tx: TransactionEvent; isLast: boolean }) {
  return (
    <div className="flex gap-3">
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <EventIcon eventType={tx.event_type} status={tx.status} />
        {!isLast && <div className="w-px h-full bg-gray-200 my-1" />}
      </div>

      {/* Content */}
      <div className={`flex-1 pb-4 ${isLast ? '' : 'border-b border-gray-50'}`}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-gray-900">
                {tx.label || tx.event_type}
              </span>
              <StatusBadge status={tx.status} />
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {formatTimestamp(tx.timestamp)}
            </div>
          </div>
          {tx.amount_usdc != null && tx.amount_usdc > 0 && (
            <span className="text-sm font-mono font-medium text-gray-900 whitespace-nowrap">
              ${tx.amount_usdc.toFixed(6)}
            </span>
          )}
        </div>

        {/* TX Hash link */}
        {tx.tx_hash && (
          <div className="mt-1.5">
            <TxHashLink txHash={tx.tx_hash} network={tx.network || 'base'} />
          </div>
        )}

        {/* Addresses (collapsed) */}
        {(tx.from_address || tx.to_address) && (
          <div className="mt-1 text-xs text-gray-400 font-mono truncate">
            {tx.from_address && (
              <span>{tx.from_address.slice(0, 6)}...{tx.from_address.slice(-4)}</span>
            )}
            {tx.from_address && tx.to_address && <span className="mx-1">→</span>}
            {tx.to_address && (
              <span>{tx.to_address.slice(0, 6)}...{tx.to_address.slice(-4)}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface TransactionTimelineProps {
  taskId: string
}

export function TransactionTimeline({ taskId }: TransactionTimelineProps) {
  const { t } = useTranslation()
  const { data, loading, error } = useTaskTransactions(taskId)

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          {t('txTimeline.transactions', 'Transactions')}
        </h3>
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
          <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-600">{t('txTimeline.loading', 'Loading transactions...')}</span>
        </div>
      </div>
    )
  }

  if (error) {
    return null // Silently hide on error — payment section still works
  }

  if (!data || data.total_count === 0) {
    return null // Don't show section if no transactions
  }

  const { transactions, summary } = data

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        {t('txTimeline.onChainTransactions', 'On-Chain Transactions')}
        <span className="text-xs font-normal text-gray-400 ml-1">
          ({data.total_count})
        </span>
      </h3>

      {/* Summary bar */}
      <div className="flex flex-wrap gap-3 mb-4 p-2.5 bg-gray-50 rounded-lg text-xs">
        {summary.total_locked > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-gray-500">{t('txTimeline.locked', 'Locked')}:</span>
            <span className="font-mono font-medium text-gray-900">${summary.total_locked.toFixed(6)}</span>
          </div>
        )}
        {summary.total_released > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-gray-500">{t('txTimeline.paid', 'Paid')}:</span>
            <span className="font-mono font-medium text-green-700">${summary.total_released.toFixed(6)}</span>
          </div>
        )}
        {summary.fee_collected > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-gray-500">Fee:</span>
            <span className="font-mono font-medium text-purple-700">${summary.fee_collected.toFixed(6)}</span>
          </div>
        )}
        {summary.total_refunded > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-gray-500">{t('txTimeline.refunded', 'Refunded')}:</span>
            <span className="font-mono font-medium text-yellow-700">${summary.total_refunded.toFixed(6)}</span>
          </div>
        )}
      </div>

      {/* Timeline */}
      <div className="space-y-0">
        {transactions.map((tx, i) => (
          <TransactionRow key={tx.id} tx={tx} isLast={i === transactions.length - 1} />
        ))}
      </div>
    </div>
  )
}
