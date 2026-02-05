import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

interface PaymentsProps {
  adminKey: string
}

import { adminGet } from '../lib/api'

async function fetchPayments(adminKey: string, period: string, page: number = 1) {
  return adminGet('/api/v1/admin/payments', adminKey, {
    period,
    limit: '20',
    offset: String((page - 1) * 20),
  })
}

async function fetchPaymentStats(adminKey: string, period: string) {
  return adminGet('/api/v1/admin/payments/stats', adminKey, { period })
}

const typeColors: Record<string, string> = {
  deposit: 'bg-blue-500',
  release: 'bg-green-500',
  partial_release: 'bg-teal-500',
  fee: 'bg-purple-500',
  refund: 'bg-orange-500',
  withdrawal: 'bg-yellow-500',
  charge: 'bg-emerald-500',
  dispute: 'bg-red-500',
}

const strategyLabels: Record<string, string> = {
  escrow_capture: 'Full Payment',
  escrow_cancel: 'Cancellation',
  instant_payment: 'Instant',
  partial_payment: 'Partial',
  dispute_resolution: 'Dispute',
}

const strategyColors: Record<string, string> = {
  escrow_capture: 'bg-green-600',
  escrow_cancel: 'bg-orange-600',
  instant_payment: 'bg-emerald-600',
  partial_payment: 'bg-teal-600',
  dispute_resolution: 'bg-red-600',
}

const statusColors: Record<string, string> = {
  confirmed: 'text-green-400',
  pending: 'text-yellow-400',
  failed: 'text-red-400',
}

export default function Payments({ adminKey }: PaymentsProps) {
  const [period, setPeriod] = useState('7d')
  const [page, setPage] = useState(1)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['paymentStats', adminKey, period],
    queryFn: () => fetchPaymentStats(adminKey, period),
    enabled: !!adminKey,
  })

  const { data: payments, isLoading: paymentsLoading } = useQuery({
    queryKey: ['payments', adminKey, period, page],
    queryFn: () => fetchPayments(adminKey, period, page),
    enabled: !!adminKey,
  })

  const isLoading = statsLoading || paymentsLoading

  if (isLoading) {
    return <div className="text-gray-400">Loading payments...</div>
  }

  const transactions = payments?.transactions || []
  const count = payments?.count || 0

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Payments & Transactions</h1>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
        >
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-400 text-sm">Total Volume</h3>
            <span className="text-2xl">💰</span>
          </div>
          <div className="mt-2">
            <span className="text-3xl font-bold text-white">
              ${(stats?.total_volume_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-400 text-sm">Fees Collected</h3>
            <span className="text-2xl">📈</span>
          </div>
          <div className="mt-2">
            <span className="text-3xl font-bold text-green-400">
              ${(stats?.total_fees_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-400 text-sm">Active Escrow</h3>
            <span className="text-2xl">🔒</span>
          </div>
          <div className="mt-2">
            <span className="text-3xl font-bold text-yellow-400">
              ${(stats?.active_escrow_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-400 text-sm">Transactions</h3>
            <span className="text-2xl">🔄</span>
          </div>
          <div className="mt-2">
            <span className="text-3xl font-bold text-white">
              {stats?.transaction_count || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Recent Transactions</h2>
        </div>
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Time</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Type</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Strategy</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Amount</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Task</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">From/To</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Status</th>
              <th className="text-left px-6 py-3 text-gray-300 text-sm font-medium">Tx Hash</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx: any) => (
              <tr key={tx.id} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-6 py-4 text-gray-400 text-sm">
                  {tx.created_at ? new Date(tx.created_at).toLocaleString() : 'N/A'}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs text-white ${typeColors[tx.type] || 'bg-gray-500'}`}>
                    {tx.type?.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4">
                  {tx.payment_strategy ? (
                    <span className={`px-2 py-1 rounded text-xs text-white ${strategyColors[tx.payment_strategy] || 'bg-gray-500'}`}>
                      {strategyLabels[tx.payment_strategy] || tx.payment_strategy}
                    </span>
                  ) : (
                    <span className="text-gray-600">-</span>
                  )}
                </td>
                <td className="px-6 py-4 text-white font-mono">
                  ${tx.amount_usd?.toFixed(2)}
                </td>
                <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                  {tx.task_id?.slice(0, 8)}...
                </td>
                <td className="px-6 py-4 text-gray-400 text-sm font-mono">
                  {tx.wallet_address?.slice(0, 6)}...{tx.wallet_address?.slice(-4)}
                </td>
                <td className={`px-6 py-4 text-sm ${statusColors[tx.status] || 'text-gray-400'}`}>
                  {tx.status}
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
                    'N/A'
                  )}
                </td>
              </tr>
            ))}
            {transactions.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-8 text-center text-gray-400">
                  No transactions found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {count > 20 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400">
            Page {page} of {Math.ceil(count / 20)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page * 20 >= count}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
