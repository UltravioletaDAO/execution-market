import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet } from '../lib/api'

// ---------------------------------------------------------------------------
// Types matching backend response shapes (mcp_server/api/admin.py)
// ---------------------------------------------------------------------------

/** Single transaction returned by GET /admin/payments */
interface PaymentTransaction {
  id: string
  created_at: string
  /** release | deposit | refund | unknown */
  type: string
  amount_usd: number
  task_id: string
  /** Agent wallet or agent_id field from tasks table */
  wallet_address: string
  /** confirmed | pending | refunded */
  status: string
  tx_hash: string | null
  /** Always "x402_escrow" from the backend */
  payment_strategy: string
}

/** GET /admin/payments response */
interface PaymentsResponse {
  transactions: PaymentTransaction[]
  count: number
  offset: number
}

/** GET /admin/payments/stats response */
interface PaymentStatsResponse {
  total_volume_usd: number
  total_fees_usd: number
  active_escrow_usd: number
  transaction_count: number
}

// ---------------------------------------------------------------------------
// API fetchers
// ---------------------------------------------------------------------------

async function fetchPayments(
  adminKey: string,
  period: string,
  page: number = 1,
): Promise<PaymentsResponse> {
  return adminGet<PaymentsResponse>('/api/v1/admin/payments', adminKey, {
    period,
    limit: '20',
    offset: String((page - 1) * 20),
  })
}

async function fetchPaymentStats(
  adminKey: string,
  period: string,
): Promise<PaymentStatsResponse> {
  return adminGet<PaymentStatsResponse>('/api/v1/admin/payments/stats', adminKey, {
    period,
  })
}

// ---------------------------------------------------------------------------
// Display maps (values match backend output exactly)
// ---------------------------------------------------------------------------

/** Transaction type badge colors — keys match backend type_map values */
const typeColors: Record<string, string> = {
  deposit: 'bg-blue-500',
  release: 'bg-green-500',
  refund: 'bg-orange-500',
  unknown: 'bg-gray-500',
}

const typeLabels: Record<string, string> = {
  deposit: 'Deposit',
  release: 'Release',
  refund: 'Refund',
  unknown: 'Unknown',
}

/** Strategy badge — backend always returns "x402_escrow" */
const strategyLabels: Record<string, string> = {
  x402_escrow: 'x402 Escrow',
}

const strategyColors: Record<string, string> = {
  x402_escrow: 'bg-indigo-600',
}

/** Status colors — keys match backend status_map values */
const statusColors: Record<string, string> = {
  confirmed: 'text-green-400',
  pending: 'text-yellow-400',
  refunded: 'text-orange-400',
}

const statusLabels: Record<string, string> = {
  confirmed: 'Confirmed',
  pending: 'Pending',
  refunded: 'Refunded',
}

// ---------------------------------------------------------------------------
// Period options
// ---------------------------------------------------------------------------

const PERIOD_OPTIONS = [
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'all', label: 'All time' },
] as const

const PAGE_SIZE = 20

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface PaymentsProps {
  adminKey: string
}

export default function Payments({ adminKey }: PaymentsProps) {
  const [period, setPeriod] = useState('7d')
  const [page, setPage] = useState(1)

  // Reset to page 1 when period changes
  const handlePeriodChange = (newPeriod: string) => {
    setPeriod(newPeriod)
    setPage(1)
  }

  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
  } = useQuery({
    queryKey: ['paymentStats', adminKey, period],
    queryFn: () => fetchPaymentStats(adminKey, period),
    enabled: !!adminKey,
  })

  const {
    data: payments,
    isLoading: paymentsLoading,
    isError: paymentsError,
  } = useQuery({
    queryKey: ['payments', adminKey, period, page],
    queryFn: () => fetchPayments(adminKey, period, page),
    enabled: !!adminKey,
  })

  const transactions: PaymentTransaction[] = payments?.transactions ?? []
  const count = payments?.count ?? 0
  const totalPages = Math.ceil(count / PAGE_SIZE)

  // --- Loading state ---
  if (statsLoading || paymentsLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-400 text-lg">Loading payments...</div>
      </div>
    )
  }

  // --- Error state ---
  if (statsError || paymentsError) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-400 text-lg">
          Failed to load payment data. Check your admin key and try again.
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Header + Period filter */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Payments & Transactions</h1>
        <select
          value={period}
          onChange={(e) => handlePeriodChange(e.target.value)}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          label="Total Volume"
          value={`$${(stats?.total_volume_usd ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          color="text-white"
        />
        <StatCard
          label="Fees Collected"
          value={`$${(stats?.total_fees_usd ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          color="text-green-400"
        />
        <StatCard
          label="Active Escrow"
          value={`$${(stats?.active_escrow_usd ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          color="text-yellow-400"
        />
        <StatCard
          label="Transactions"
          value={String(stats?.transaction_count ?? 0)}
          color="text-white"
        />
      </div>

      {/* Transactions Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Recent Transactions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-700">
              <tr>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Time</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Type</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Strategy</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Amount</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Task</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Wallet</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Status</th>
                <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Tx Hash</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id} className="border-t border-gray-700 hover:bg-gray-750">
                  <td className="px-6 py-4 text-gray-400 text-sm whitespace-nowrap">
                    {tx.created_at ? new Date(tx.created_at).toLocaleString() : 'N/A'}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 rounded text-xs text-white ${typeColors[tx.type] ?? 'bg-gray-500'}`}
                    >
                      {typeLabels[tx.type] ?? tx.type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {tx.payment_strategy ? (
                      <span
                        className={`px-2 py-1 rounded text-xs text-white ${strategyColors[tx.payment_strategy] ?? 'bg-gray-500'}`}
                      >
                        {strategyLabels[tx.payment_strategy] ?? tx.payment_strategy}
                      </span>
                    ) : (
                      <span className="text-gray-600">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-white font-mono">
                    ${(tx.amount_usd ?? 0).toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                    {tx.task_id ? `${tx.task_id.slice(0, 8)}...` : '-'}
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                    {tx.wallet_address
                      ? `${tx.wallet_address.slice(0, 6)}...${tx.wallet_address.slice(-4)}`
                      : '-'}
                  </td>
                  <td
                    className={`px-6 py-4 text-sm ${statusColors[tx.status] ?? 'text-gray-400'}`}
                  >
                    {statusLabels[tx.status] ?? tx.status}
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                    {tx.tx_hash ? (
                      <a
                        href={`https://basescan.org/tx/${tx.tx_hash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-em-400 hover:text-em-300"
                      >
                        {tx.tx_hash.slice(0, 8)}...
                      </a>
                    ) : (
                      <span className="text-gray-600">-</span>
                    )}
                  </td>
                </tr>
              ))}
              {transactions.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-gray-400">
                    No transactions found for this period.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50 hover:bg-gray-600 transition-colors"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50 hover:bg-gray-600 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color: string
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h3 className="text-gray-400 text-sm">{label}</h3>
      <div className="mt-2">
        <span className={`text-3xl font-bold ${color}`}>{value}</span>
      </div>
    </div>
  )
}
