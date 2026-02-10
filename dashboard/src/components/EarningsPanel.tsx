/**
 * EarningsPanel - Panel completo de ganancias para ejecutores
 *
 * Incluye:
 * - Resumen de ganancias totales
 * - Pagos pendientes de aprobacion
 * - Seccion de retiro
 * - Historial de transacciones
 */

import { useState, useMemo } from 'react'
import { TX_EXPLORER_URLS } from '../utils/blockchain'

// ============================================================================
// TYPES
// ============================================================================

export type PaymentStatus = 'completed' | 'pending' | 'failed'

export type TransactionType = 'task_payment' | 'withdrawal' | 'bonus' | 'refund'

export interface EarningsSummary {
  total_earned_usdc: number
  this_month_usdc: number
  last_7_days_usdc: number
  available_balance_usdc: number
}

export interface PendingTask {
  id: string
  task_id: string
  task_title: string
  bounty_usd: number
  submitted_at: string
  expected_payout_date: string
  status: 'awaiting_review' | 'under_review' | 'approved_pending_payment'
}

export interface Transaction {
  id: string
  type: TransactionType
  amount_usdc: number
  status: PaymentStatus
  tx_hash: string | null
  network: string
  created_at: string
  task_title?: string
}

export interface EarningsPanelProps {
  summary: EarningsSummary | null
  pendingTasks: PendingTask[]
  transactions: Transaction[]
  loading?: boolean
  onWithdraw: () => void
  minWithdrawal?: number
}

// ============================================================================
// CONSTANTS
// ============================================================================

const STATUS_COLORS: Record<PaymentStatus, string> = {
  completed: 'bg-green-100 text-green-800',
  pending: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
}

const STATUS_LABELS: Record<PaymentStatus, string> = {
  completed: 'Completado',
  pending: 'Pendiente',
  failed: 'Fallido',
}

const PENDING_STATUS_LABELS: Record<PendingTask['status'], string> = {
  awaiting_review: 'Esperando revision',
  under_review: 'En revision',
  approved_pending_payment: 'Aprobado - Pago pendiente',
}

const TRANSACTION_TYPE_LABELS: Record<TransactionType, string> = {
  task_payment: 'Pago de tarea',
  withdrawal: 'Retiro',
  bonus: 'Bonificacion',
  refund: 'Reembolso',
}

// ============================================================================
// UTILITIES
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getExplorerUrl(network: string, txHash: string): string {
  return (TX_EXPLORER_URLS[network] || TX_EXPLORER_URLS.base) + txHash
}

function truncateHash(hash: string): string {
  return `${hash.slice(0, 8)}...${hash.slice(-6)}`
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Summary skeleton */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-10 bg-gray-200 rounded w-1/2 mb-6"></div>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-16 bg-gray-200 rounded"></div>
          <div className="h-16 bg-gray-200 rounded"></div>
        </div>
      </div>

      {/* Pending skeleton */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
        <div className="space-y-3">
          <div className="h-16 bg-gray-200 rounded"></div>
          <div className="h-16 bg-gray-200 rounded"></div>
        </div>
      </div>
    </div>
  )
}

function EarningsSummaryCard({ summary }: { summary: EarningsSummary }) {
  return (
    <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl shadow-lg p-6 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-green-100 text-sm font-medium uppercase tracking-wide">
          Ganancias Totales
        </h3>
        <div className="flex items-center gap-1 text-green-200">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-xs">USDC</span>
        </div>
      </div>

      {/* Total earned */}
      <div className="mb-6">
        <span className="text-4xl font-bold">
          {formatCurrency(summary.total_earned_usdc)}
        </span>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">Este mes</div>
          <div className="text-lg font-semibold">
            {formatCurrency(summary.this_month_usdc)}
          </div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">Ultimos 7 dias</div>
          <div className="text-lg font-semibold">
            {formatCurrency(summary.last_7_days_usdc)}
          </div>
        </div>
      </div>
    </div>
  )
}

function PendingPaymentsSection({ tasks }: { tasks: PendingTask[] }) {
  if (tasks.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Pagos Pendientes
        </h3>
        <div className="text-center py-6">
          <svg
            className="w-12 h-12 text-gray-300 mx-auto mb-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-gray-500 text-sm">
            No tienes tareas pendientes de aprobacion
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900">
          Pagos Pendientes
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {tasks.length} tarea{tasks.length !== 1 ? 's' : ''} esperando aprobacion
        </p>
      </div>

      <div className="divide-y divide-gray-100">
        {tasks.map((task) => (
          <div key={task.id} className="p-4 hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {task.task_title}
                </p>
                <p className="text-sm text-gray-500 mt-0.5">
                  Enviada: {formatDate(task.submitted_at)}
                </p>
                <div className="mt-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    {PENDING_STATUS_LABELS[task.status]}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-semibold text-green-600">
                  {formatCurrency(task.bounty_usd)}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Pago esperado: {formatDate(task.expected_payout_date)}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pending total */}
      <div className="p-4 bg-gray-50 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            Total pendiente
          </span>
          <span className="text-lg font-bold text-gray-900">
            {formatCurrency(tasks.reduce((sum, t) => sum + t.bounty_usd, 0))}
          </span>
        </div>
      </div>
    </div>
  )
}

function WithdrawalSection({
  balance,
  minWithdrawal,
  onWithdraw,
}: {
  balance: number
  minWithdrawal: number
  onWithdraw: () => void
}) {
  const canWithdraw = balance >= minWithdrawal

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Retirar Fondos</h3>

      {/* Available balance */}
      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        <div className="text-sm text-gray-600 mb-1">Saldo disponible</div>
        <div className="text-3xl font-bold text-gray-900">
          {formatCurrency(balance)}{' '}
          <span className="text-sm font-normal text-gray-500">USDC</span>
        </div>
      </div>

      {/* Withdraw button */}
      <button
        onClick={onWithdraw}
        disabled={!canWithdraw}
        className={`w-full py-3 rounded-lg font-medium transition-all ${
          canWithdraw
            ? 'bg-blue-600 text-white hover:bg-blue-700 active:scale-98'
            : 'bg-gray-100 text-gray-400 cursor-not-allowed'
        }`}
      >
        Retirar fondos
      </button>

      {/* Minimum notice */}
      <div className="mt-3 flex items-start gap-2 text-xs text-gray-500">
        <svg
          className="w-4 h-4 flex-shrink-0 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span>
          Retiro minimo: {formatCurrency(minWithdrawal)}. Los retiros se
          procesan en la red de tu tarea.
        </span>
      </div>
    </div>
  )
}

function TransactionTypeIcon({ type }: { type: TransactionType }) {
  const icons: Record<TransactionType, JSX.Element> = {
    task_payment: (
      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
        <svg
          className="w-5 h-5 text-green-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>
    ),
    withdrawal: (
      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
        <svg
          className="w-5 h-5 text-blue-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
    ),
    bonus: (
      <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
        <svg
          className="w-5 h-5 text-purple-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"
          />
        </svg>
      </div>
    ),
    refund: (
      <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
        <svg
          className="w-5 h-5 text-orange-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
          />
        </svg>
      </div>
    ),
  }

  return icons[type]
}

function PaymentHistorySection({
  transactions,
}: {
  transactions: Transaction[]
}) {
  const [showAll, setShowAll] = useState(false)
  const displayedTransactions = useMemo(
    () => (showAll ? transactions : transactions.slice(0, 5)),
    [transactions, showAll]
  )

  if (transactions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Historial de Pagos
        </h3>
        <div className="text-center py-6">
          <svg
            className="w-12 h-12 text-gray-300 mx-auto mb-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-gray-500 text-sm">No hay transacciones aun</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900">
          Historial de Pagos
        </h3>
      </div>

      <div className="divide-y divide-gray-100">
        {displayedTransactions.map((tx) => (
          <div
            key={tx.id}
            className="p-4 flex items-center gap-4 hover:bg-gray-50 transition-colors"
          >
            <TransactionTypeIcon type={tx.type} />

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-medium text-gray-900">
                  {TRANSACTION_TYPE_LABELS[tx.type]}
                </p>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[tx.status]}`}
                >
                  {STATUS_LABELS[tx.status]}
                </span>
              </div>
              {tx.task_title && (
                <p className="text-sm text-gray-500 truncate">{tx.task_title}</p>
              )}
              <p className="text-xs text-gray-400 mt-0.5">
                {formatDateTime(tx.created_at)}
              </p>
            </div>

            <div className="text-right">
              <p
                className={`font-semibold ${
                  tx.type === 'withdrawal' ? 'text-red-600' : 'text-green-600'
                }`}
              >
                {tx.type === 'withdrawal' ? '-' : '+'}
                {formatCurrency(tx.amount_usdc)}
              </p>
              {tx.tx_hash && (
                <a
                  href={getExplorerUrl(tx.network, tx.tx_hash)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 mt-1"
                >
                  <span className="font-mono">{truncateHash(tx.tx_hash)}</span>
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Show more/less */}
      {transactions.length > 5 && (
        <div className="p-4 text-center border-t border-gray-100">
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            {showAll
              ? 'Mostrar menos'
              : `Ver todas (${transactions.length} transacciones)`}
          </button>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function EarningsPanel({
  summary,
  pendingTasks,
  transactions,
  loading = false,
  onWithdraw,
  minWithdrawal = 5.0,
}: EarningsPanelProps) {
  if (loading) {
    return <LoadingSkeleton />
  }

  return (
    <div className="space-y-6">
      {/* Earnings Overview */}
      {summary && <EarningsSummaryCard summary={summary} />}

      {/* Pending Payments */}
      <PendingPaymentsSection tasks={pendingTasks} />

      {/* Withdrawal Section */}
      <WithdrawalSection
        balance={summary?.available_balance_usdc || 0}
        minWithdrawal={minWithdrawal}
        onWithdraw={onWithdraw}
      />

      {/* Payment History */}
      <PaymentHistorySection transactions={transactions} />
    </div>
  )
}

