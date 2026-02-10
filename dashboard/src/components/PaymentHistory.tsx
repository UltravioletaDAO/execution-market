/**
 * PaymentHistory - Payment transaction history for executors
 *
 * Features:
 * - Transaction list with filtering
 * - Export to CSV
 * - Transaction details
 * - Network explorer links
 */

import { useState, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { TX_EXPLORER_URLS } from '../utils/blockchain'

// Types
interface Payment {
  id: string
  type: 'task_payment' | 'withdrawal' | 'bonus' | 'refund'
  status: 'pending' | 'confirmed' | 'failed'
  amount: number
  currency: string
  task_id?: string
  task_title?: string
  tx_hash?: string
  network: string
  created_at: string
  confirmed_at?: string
}

interface PaymentHistoryProps {
  payments: Payment[]
  loading?: boolean
  onLoadMore?: () => void
  hasMore?: boolean
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

// Get explorer URL
function getExplorerUrl(network: string, txHash: string): string {
  return (TX_EXPLORER_URLS[network] || TX_EXPLORER_URLS.base) + txHash
}

// Status badge component
function StatusBadge({ status }: { status: Payment['status'] }) {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    confirmed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }

  const labels = {
    pending: 'Pendiente',
    confirmed: 'Confirmado',
    failed: 'Fallido',
  }

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colors[status]}`}>
      {labels[status]}
    </span>
  )
}

// Type icon component
function TypeIcon({ type }: { type: Payment['type'] }) {
  const icons = {
    task_payment: (
      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
        <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
    ),
    withdrawal: (
      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
        <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    ),
    bonus: (
      <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
        <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
        </svg>
      </div>
    ),
    refund: (
      <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
        <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
        </svg>
      </div>
    ),
  }

  return icons[type]
}

export function PaymentHistory({
  payments,
  loading = false,
  onLoadMore,
  hasMore = false,
}: PaymentHistoryProps) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<Payment['type'] | 'all'>('all')
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null)

  // Filter payments
  const filteredPayments = useMemo(() => {
    if (filter === 'all') return payments
    return payments.filter((p) => p.type === filter)
  }, [payments, filter])

  // Calculate totals
  const totals = useMemo(() => {
    const result = {
      earned: 0,
      withdrawn: 0,
      pending: 0,
    }

    payments.forEach((p) => {
      if (p.status === 'confirmed') {
        if (p.type === 'task_payment' || p.type === 'bonus') {
          result.earned += p.amount
        } else if (p.type === 'withdrawal') {
          result.withdrawn += p.amount
        }
      } else if (p.status === 'pending') {
        result.pending += p.amount
      }
    })

    return result
  }, [payments])

  // Export to CSV
  const exportToCSV = useCallback(() => {
    const headers = ['Fecha', 'Tipo', 'Estado', 'Monto', 'Moneda', 'Tarea', 'TX Hash', 'Red']
    const rows = filteredPayments.map((p) => [
      formatDate(p.created_at),
      p.type,
      p.status,
      p.amount.toString(),
      p.currency,
      p.task_title || '',
      p.tx_hash || '',
      p.network,
    ])

    const csv = [headers, ...rows].map((row) => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `execution-market-payments-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [filteredPayments])

  // Get type label
  const getTypeLabel = (type: Payment['type']) => {
    const labels = {
      task_payment: t('payments.taskPayment', 'Pago de tarea'),
      withdrawal: t('payments.withdrawal', 'Retiro'),
      bonus: t('payments.bonus', 'Bonificacion'),
      refund: t('payments.refund', 'Reembolso'),
    }
    return labels[type]
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {t('payments.history', 'Historial de pagos')}
          </h2>
          <button
            onClick={exportToCSV}
            className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {t('common.export', 'Exportar')}
          </button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="p-3 bg-green-50 rounded-lg">
            <p className="text-xs text-green-600 font-medium uppercase">
              {t('payments.totalEarned', 'Ganado')}
            </p>
            <p className="text-lg font-semibold text-green-700">
              {formatCurrency(totals.earned, 'USDC')}
            </p>
          </div>
          <div className="p-3 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-600 font-medium uppercase">
              {t('payments.totalWithdrawn', 'Retirado')}
            </p>
            <p className="text-lg font-semibold text-blue-700">
              {formatCurrency(totals.withdrawn, 'USDC')}
            </p>
          </div>
          <div className="p-3 bg-yellow-50 rounded-lg">
            <p className="text-xs text-yellow-600 font-medium uppercase">
              {t('payments.pending', 'Pendiente')}
            </p>
            <p className="text-lg font-semibold text-yellow-700">
              {formatCurrency(totals.pending, 'USDC')}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 overflow-x-auto scrollbar-hide">
          {(['all', 'task_payment', 'withdrawal', 'bonus', 'refund'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
                filter === type
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {type === 'all'
                ? t('common.all', 'Todos')
                : getTypeLabel(type)}
            </button>
          ))}
        </div>
      </div>

      {/* Payment list */}
      <div className="divide-y divide-gray-100">
        {loading && filteredPayments.length === 0 ? (
          // Loading skeletons
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="p-4 flex items-center gap-4">
              <div className="skeleton w-10 h-10 rounded-full" />
              <div className="flex-1">
                <div className="skeleton h-4 w-32 rounded mb-2" />
                <div className="skeleton h-3 w-24 rounded" />
              </div>
              <div className="skeleton h-5 w-16 rounded" />
            </div>
          ))
        ) : filteredPayments.length === 0 ? (
          // Empty state
          <div className="p-8 text-center">
            <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-gray-500">
              {t('payments.noPayments', 'No hay pagos aun')}
            </p>
          </div>
        ) : (
          <>
            {filteredPayments.map((payment) => (
              <button
                key={payment.id}
                onClick={() => setSelectedPayment(payment)}
                className="w-full p-4 flex items-center gap-4 hover:bg-gray-50 transition-colors text-left"
              >
                <TypeIcon type={payment.type} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900">
                      {getTypeLabel(payment.type)}
                    </p>
                    <StatusBadge status={payment.status} />
                  </div>
                  {payment.task_title && (
                    <p className="text-sm text-gray-500 truncate">
                      {payment.task_title}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-0.5">
                    {formatDate(payment.created_at)}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`font-semibold ${
                    payment.type === 'withdrawal' ? 'text-red-600' : 'text-green-600'
                  }`}>
                    {payment.type === 'withdrawal' ? '-' : '+'}
                    {formatCurrency(payment.amount, payment.currency)}
                  </p>
                  <p className="text-xs text-gray-400">{payment.currency}</p>
                </div>
              </button>
            ))}

            {/* Load more */}
            {hasMore && (
              <div className="p-4 text-center">
                <button
                  onClick={onLoadMore}
                  disabled={loading}
                  className="text-blue-600 hover:text-blue-700 text-sm font-medium disabled:opacity-50"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      {t('common.loading', 'Cargando...')}
                    </span>
                  ) : (
                    t('common.loadMore', 'Cargar mas')
                  )}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Payment detail modal */}
      {selectedPayment && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg w-full max-w-md overflow-hidden animate-scale-in">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                {t('payments.details', 'Detalles del pago')}
              </h3>
              <button
                onClick={() => setSelectedPayment(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4">
              {/* Amount */}
              <div className="text-center mb-6">
                <div className="mb-2">
                  <TypeIcon type={selectedPayment.type} />
                </div>
                <p className={`text-3xl font-bold ${
                  selectedPayment.type === 'withdrawal' ? 'text-red-600' : 'text-green-600'
                }`}>
                  {selectedPayment.type === 'withdrawal' ? '-' : '+'}
                  {formatCurrency(selectedPayment.amount, selectedPayment.currency)}
                </p>
                <p className="text-gray-500">{selectedPayment.currency}</p>
              </div>

              {/* Details */}
              <dl className="space-y-3">
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('payments.type', 'Tipo')}</dt>
                  <dd className="font-medium text-gray-900">
                    {getTypeLabel(selectedPayment.type)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('payments.status', 'Estado')}</dt>
                  <dd><StatusBadge status={selectedPayment.status} /></dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('payments.date', 'Fecha')}</dt>
                  <dd className="font-medium text-gray-900">
                    {formatDate(selectedPayment.created_at)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">{t('payments.network', 'Red')}</dt>
                  <dd className="font-medium text-gray-900 capitalize">
                    {selectedPayment.network}
                  </dd>
                </div>
                {selectedPayment.task_title && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">{t('payments.task', 'Tarea')}</dt>
                    <dd className="font-medium text-gray-900 truncate max-w-[60%]">
                      {selectedPayment.task_title}
                    </dd>
                  </div>
                )}
                {selectedPayment.tx_hash && (
                  <div className="flex justify-between items-center">
                    <dt className="text-gray-500">{t('payments.transaction', 'Transaccion')}</dt>
                    <dd>
                      <a
                        href={getExplorerUrl(selectedPayment.network, selectedPayment.tx_hash)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-blue-600 hover:text-blue-700"
                      >
                        <span className="font-mono text-sm">
                          {selectedPayment.tx_hash.slice(0, 8)}...{selectedPayment.tx_hash.slice(-6)}
                        </span>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            <div className="p-4 bg-gray-50">
              <button
                onClick={() => setSelectedPayment(null)}
                className="w-full py-2 text-gray-600 font-medium rounded-lg hover:bg-gray-100 transition-colors"
              >
                {t('common.close', 'Cerrar')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export type { Payment }
export default PaymentHistory
