/**
 * Earnings - Worker Earnings Page (read-only historical stats)
 *
 * Per ADR-001 (agent-signed escrow), funds flow directly agent -> worker wallet
 * on-chain. There is no custodial platform balance and no "withdraw" action.
 * For wallet actions (send/receive/export), users go to /profile > WalletSection.
 */

import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { TX_EXPLORER_URLS } from '../utils/blockchain'
import { TxLink } from '../components/TxLink'
import { EmptyState } from '../components/ui/EmptyState'

const COIN_ICON_PATH =
  'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
const ALERT_ICON_PATH =
  'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'

// ============================================================================
// TYPES
// ============================================================================

export type PaymentStatus = 'completed' | 'pending' | 'failed'
export type TransactionType = 'task_payment' | 'withdrawal' | 'bonus' | 'refund'
export type ChartPeriod = 'week' | 'month' | 'year'

export interface EarningsSummary {
  total_earned_usdc: number
  available_balance_usdc: number
  pending_usdc: number
  this_month_usdc: number
  last_month_usdc: number
  this_week_usdc: number
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
  task_id?: string
}

export interface PendingPayment {
  id: string
  task_id: string
  task_title: string
  bounty_usd: number
  submitted_at: string
  expected_payout_date: string
  status: 'awaiting_review' | 'under_review' | 'approved_pending_payment'
}

export interface ChartDataPoint {
  label: string
  value: number
}

export interface EarningsPageProps {
  summary: EarningsSummary | null
  transactions: Transaction[]
  pendingPayments: PendingPayment[]
  chartData: ChartDataPoint[]
  loading?: boolean
  error?: Error | null
  onChartPeriodChange: (period: ChartPeriod) => void
  chartPeriod: ChartPeriod
  onViewWallet?: () => void
}

// ============================================================================
// CONSTANTS
// ============================================================================

const STATUS_COLORS: Record<PaymentStatus, string> = {
  completed: 'bg-green-100 text-green-800',
  pending: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
}

const STATUS_I18N: Record<PaymentStatus, string> = {
  completed: 'earnings.status.completed',
  pending: 'earnings.status.pending',
  failed: 'earnings.status.failed',
}

const TX_TYPE_I18N: Record<TransactionType, string> = {
  task_payment: 'earnings.txType.taskPayment',
  withdrawal: 'earnings.txType.withdrawal',
  bonus: 'earnings.txType.bonus',
  refund: 'earnings.txType.refund',
}

const PENDING_STATUS_I18N: Record<PendingPayment['status'], string> = {
  awaiting_review: 'earnings.pendingStatus.awaitingReview',
  under_review: 'earnings.pendingStatus.underReview',
  approved_pending_payment: 'earnings.pendingStatus.approvedPending',
}

const CHART_PERIOD_I18N: { value: ChartPeriod; key: string }[] = [
  { value: 'week', key: 'earnings.period.week' },
  { value: 'month', key: 'earnings.period.month' },
  { value: 'year', key: 'earnings.period.year' },
]

// ============================================================================
// UTILITIES
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
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

function calculatePercentChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0
  return ((current - previous) / previous) * 100
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
        <div className="h-10 bg-gray-200 rounded w-1/2 mb-6" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-16 bg-gray-200 rounded" />
          <div className="h-16 bg-gray-200 rounded" />
        </div>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-4" />
        <div className="h-48 bg-gray-200 rounded" />
      </div>
    </div>
  )
}

function SummaryCard({ summary }: { summary: EarningsSummary }) {
  const { t } = useTranslation()
  const monthChange = calculatePercentChange(summary.this_month_usdc, summary.last_month_usdc)
  const isPositiveChange = monthChange >= 0

  return (
    <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl shadow-lg p-6 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-green-100 text-sm font-medium uppercase tracking-wide">
          {t('earnings.lifetimeEarnings', 'Lifetime Earnings')}
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

      {/* Main balance — lifetime total earned */}
      <div className="mb-6">
        <div className="text-4xl font-bold">{formatCurrency(summary.total_earned_usdc)}</div>
        {summary.pending_usdc > 0 && (
          <div className="text-green-200 text-sm mt-1">
            +{formatCurrency(summary.pending_usdc)} {t('earnings.pendingApproval', 'pending approval')}
          </div>
        )}
        <p className="text-green-200 text-xs mt-2">
          {t('earnings.directToWallet', 'Paid directly to your wallet on-chain.')}
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">{t('earnings.lastMonth', 'Last month')}</div>
          <div className="text-lg font-semibold">{formatCurrency(summary.last_month_usdc)}</div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">{t('earnings.thisMonth', 'This month')}</div>
          <div className="text-lg font-semibold">{formatCurrency(summary.this_month_usdc)}</div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-green-200 text-xs mb-1">{t('earnings.vsPrevMonth', 'vs previous month')}</div>
          <div className={`text-lg font-semibold flex items-center gap-1`}>
            {isPositiveChange ? (
              <svg className="w-4 h-4 text-green-300" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg className="w-4 h-4 text-red-300" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            <span>{Math.abs(monthChange).toFixed(0)}%</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function EarningsChart({
  data,
  period,
  onPeriodChange,
}: {
  data: ChartDataPoint[]
  period: ChartPeriod
  onPeriodChange: (period: ChartPeriod) => void
}) {
  const { t } = useTranslation()
  const maxValue = Math.max(...data.map((d) => d.value), 1)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">{t('earnings.earningsHistory', 'Earnings History')}</h3>
        <div className="flex gap-1 p-0.5 bg-gray-100 rounded-lg">
          {CHART_PERIOD_I18N.map((p) => (
            <button
              key={p.value}
              onClick={() => onPeriodChange(p.value)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                period === p.value
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {t(p.key)}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="p-4">
        {data.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-gray-400">
            {t('earnings.noData', 'No data to show')}
          </div>
        ) : (
          <div className="h-48 flex items-end justify-between gap-2">
            {data.map((point, index) => {
              const height = (point.value / maxValue) * 100
              return (
                <div key={index} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex flex-col items-center flex-1 justify-end">
                    {point.value > 0 && (
                      <div className="text-xs text-gray-500 mb-1">
                        {formatCurrency(point.value)}
                      </div>
                    )}
                    <div
                      className="w-full bg-green-500 rounded-t transition-all duration-300 min-h-[4px]"
                      style={{ height: `${Math.max(height, 2)}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 text-center truncate w-full">
                    {point.label}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function PendingPaymentsSection({ payments }: { payments: PendingPayment[] }) {
  const { t } = useTranslation()
  if (payments.length === 0) {
    return null
  }

  const total = payments.reduce((sum, p) => sum + p.bounty_usd, 0)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">{t('earnings.pendingPayments', 'Pending Payments')}</h3>
          <span className="text-sm text-gray-500">
            {payments.length} tarea{payments.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {payments.map((payment) => (
          <div key={payment.id} className="p-4 hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{payment.task_title}</p>
                <p className="text-sm text-gray-500 mt-0.5">
                  {t('earnings.submitted', 'Submitted')}: {formatDate(payment.submitted_at)}
                </p>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 mt-2">
                  {t(PENDING_STATUS_I18N[payment.status])}
                </span>
              </div>
              <div className="text-right">
                <p className="text-lg font-semibold text-green-600">
                  {formatCurrency(payment.bounty_usd)}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {t('earnings.expected', 'Expected')}: {formatDate(payment.expected_payout_date)}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Total */}
      <div className="p-4 bg-gray-50 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">{t('earnings.totalPending', 'Total pending')}</span>
          <span className="text-lg font-bold text-gray-900">{formatCurrency(total)}</span>
        </div>
      </div>
    </div>
  )
}

function WalletInfoBanner({ onViewWallet }: { onViewWallet?: () => void }) {
  const { t } = useTranslation()

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 flex items-start gap-3">
      <svg
        className="w-6 h-6 flex-shrink-0 text-blue-600 mt-0.5"
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
      <div className="flex-1">
        <h3 className="font-semibold text-gray-900 mb-1">
          {t('earnings.walletInfoTitle', 'Your funds are already in your wallet')}
        </h3>
        <p className="text-sm text-gray-700 mb-3">
          {t(
            'earnings.walletInfoBody',
            'Every task payment settles directly to your wallet on-chain. There is no platform balance to withdraw — you already own the funds.',
          )}
        </p>
        {onViewWallet && (
          <button
            onClick={onViewWallet}
            className="text-sm font-medium text-blue-700 hover:text-blue-900"
          >
            {t('earnings.viewMyWallet', 'View my wallet →')}
          </button>
        )}
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
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
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

function TransactionHistory({ transactions }: { transactions: Transaction[] }) {
  const { t } = useTranslation()
  const [showAll, setShowAll] = useState(false)
  const displayedTransactions = useMemo(
    () => (showAll ? transactions : transactions.slice(0, 10)),
    [transactions, showAll]
  )

  if (transactions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">{t('earnings.transactionHistory', 'Transaction History')}</h3>
        <EmptyState
          size="sm"
          iconPath={COIN_ICON_PATH}
          description={t('earnings.noTransactions', 'No transactions yet')}
        />
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">{t('earnings.transactionHistory', 'Transaction History')}</h3>
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
                  {t(TX_TYPE_I18N[tx.type])}
                </p>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[tx.status]}`}
                >
                  {t(STATUS_I18N[tx.status])}
                </span>
              </div>
              {tx.task_title && (
                <p className="text-sm text-gray-500 truncate">{tx.task_title}</p>
              )}
              <p className="text-xs text-gray-400 mt-0.5">{formatDateTime(tx.created_at)}</p>
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
                <TxLink txHash={tx.tx_hash} network={tx.network} showNetwork className="mt-1" />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Show more */}
      {transactions.length > 10 && (
        <div className="p-4 text-center border-t border-gray-100">
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            {showAll
              ? t('common.showLess')
              : t('earnings.viewAll', 'View all ({{count}} transactions)', { count: transactions.length })}
          </button>
        </div>
      )}
    </div>
  )
}

function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const { t } = useTranslation()
  return (
    <EmptyState
      iconPath={ALERT_ICON_PATH}
      variant="danger"
      title={t('earnings.loadError', 'Error loading earnings')}
      description={error.message}
      action={
        onRetry ? (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-medium transition-colors"
          >
            {t('common.retry')}
          </button>
        ) : undefined
      }
    />
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function Earnings({
  summary,
  transactions,
  pendingPayments,
  chartData,
  loading = false,
  error = null,
  onChartPeriodChange,
  chartPeriod,
  onViewWallet,
}: EarningsPageProps) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900">{t('earnings.title', 'My Earnings')}</h1>
        <LoadingSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900">{t('earnings.title', 'My Earnings')}</h1>
        <ErrorState error={error} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <h1 className="text-xl font-bold text-gray-900">Mis Ganancias</h1>

      {/* Summary Card */}
      {summary && <SummaryCard summary={summary} />}

      {/* Chart */}
      <EarningsChart data={chartData} period={chartPeriod} onPeriodChange={onChartPeriodChange} />

      {/* Pending Payments */}
      <PendingPaymentsSection payments={pendingPayments} />

      {/* Wallet info — funds flow direct on-chain per ADR-001 */}
      <WalletInfoBanner onViewWallet={onViewWallet} />

      {/* Transaction History */}
      <TransactionHistory transactions={transactions} />
    </div>
  )
}

export default Earnings
