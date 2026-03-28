import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet, adminPost } from '../lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OrphanedSubmission {
  id: string
  task_id: string
  executor_id: string
  agent_verdict: string
  payment_tx: string | null
  updated_at: string
  task: {
    id: string
    title: string
    bounty_usd: number
    escrow_tx: string | null
    status: string
  }
  executor: {
    id: string
    wallet_address: string
    display_name: string | null
  }
}

interface OrphanedResponse {
  orphaned_submissions: OrphanedSubmission[]
  count: number
}

interface RetryResult {
  status: 'settled' | 'already_paid' | 'failed'
  payment_tx?: string | null
  paid_at?: string | null
  payment_amount?: number | null
  message?: string
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface OrphanedPaymentsProps {
  adminKey: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function truncateWallet(address: string): string {
  if (!address || address.length < 12) return address || '--'
  return `${address.slice(0, 6)}...${address.slice(-4)}`
}

function timeSince(dateStr: string): string {
  const then = new Date(dateStr).getTime()
  const now = Date.now()
  const diffMs = now - then
  if (diffMs < 0) return 'just now'

  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ${minutes % 60}m ago`

  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h ago`
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OrphanedPayments({ adminKey }: OrphanedPaymentsProps) {
  const queryClient = useQueryClient()
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<{ id: string; result: RetryResult } | null>(null)

  // Fetch orphaned payments
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery<OrphanedResponse>({
    queryKey: ['orphanedPayments'],
    queryFn: () => adminGet<OrphanedResponse>('/api/v1/admin/payments/orphaned', adminKey),
    refetchInterval: 30_000,
  })

  // Retry mutation
  const retryMutation = useMutation<RetryResult, Error, string>({
    mutationFn: (submissionId: string) =>
      adminPost<RetryResult>(`/api/v1/admin/payments/retry/${submissionId}`, adminKey, {}),
    onSuccess: (result, submissionId) => {
      setLastResult({ id: submissionId, result })
      setConfirmId(null)
      queryClient.invalidateQueries({ queryKey: ['orphanedPayments'] })
    },
    onError: () => {
      setConfirmId(null)
    },
  })

  // ------- Render helpers -------

  const submissions = data?.orphaned_submissions ?? []

  if (isLoading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Orphaned Payments</h2>
        <div className="flex items-center justify-center py-12 text-gray-400">
          <svg className="animate-spin h-5 w-5 mr-3 text-purple-400" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading orphaned payments...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Orphaned Payments</h2>
        <div className="bg-red-900/30 border border-red-700 rounded-md p-4 text-red-300 text-sm">
          Failed to load orphaned payments: {(error as Error).message}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">
          Orphaned Payments
          {data && (
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({data.count} found)
            </span>
          )}
        </h2>
        <button
          onClick={() => refetch()}
          className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Result banner */}
      {lastResult && (
        <div
          className={`mb-4 rounded-md p-3 text-sm border ${
            lastResult.result.status === 'settled'
              ? 'bg-green-900/30 border-green-700 text-green-300'
              : lastResult.result.status === 'already_paid'
                ? 'bg-blue-900/30 border-blue-700 text-blue-300'
                : 'bg-red-900/30 border-red-700 text-red-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <div>
              {lastResult.result.status === 'settled' && (
                <>
                  Settlement successful.{' '}
                  {lastResult.result.payment_tx && (
                    <span className="font-mono text-xs">
                      TX: {lastResult.result.payment_tx}
                    </span>
                  )}
                </>
              )}
              {lastResult.result.status === 'already_paid' && (
                <>Already paid. TX: <span className="font-mono text-xs">{lastResult.result.payment_tx}</span></>
              )}
              {lastResult.result.status === 'failed' && (
                <>Retry failed: {lastResult.result.message || 'Check server logs.'}</>
              )}
            </div>
            <button
              onClick={() => setLastResult(null)}
              className="text-gray-400 hover:text-white ml-4"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {submissions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <svg className="h-12 w-12 text-green-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-green-400 font-medium">No orphaned payments found</p>
          <p className="text-gray-500 text-sm mt-1">All approved submissions have been settled.</p>
        </div>
      ) : (
        /* Table */
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
                <th className="pb-3 pr-4">Task Title</th>
                <th className="pb-3 pr-4">Worker Wallet</th>
                <th className="pb-3 pr-4 text-right">Amount (USD)</th>
                <th className="pb-3 pr-4">Time Since Approval</th>
                <th className="pb-3 pr-4">Status</th>
                <th className="pb-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => (
                <tr key={sub.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                  {/* Task title */}
                  <td className="py-3 pr-4 text-white max-w-[200px] truncate" title={sub.task?.title}>
                    {sub.task?.title || sub.task_id}
                  </td>

                  {/* Worker wallet */}
                  <td className="py-3 pr-4 font-mono text-gray-300 text-xs" title={sub.executor?.wallet_address}>
                    {truncateWallet(sub.executor?.wallet_address)}
                  </td>

                  {/* Amount */}
                  <td className="py-3 pr-4 text-right text-white font-medium">
                    ${sub.task?.bounty_usd?.toFixed(2) ?? '--'}
                  </td>

                  {/* Time since approval */}
                  <td className="py-3 pr-4 text-gray-400">
                    {timeSince(sub.updated_at)}
                  </td>

                  {/* Status */}
                  <td className="py-3 pr-4">
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-yellow-600/20 text-yellow-400 border border-yellow-600/30">
                      {sub.agent_verdict}
                    </span>
                  </td>

                  {/* Actions */}
                  <td className="py-3">
                    {confirmId === sub.id ? (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => retryMutation.mutate(sub.id)}
                          disabled={retryMutation.isPending}
                          className="px-3 py-1 text-xs font-medium rounded bg-purple-600 hover:bg-purple-500 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {retryMutation.isPending ? 'Retrying...' : 'Confirm'}
                        </button>
                        <button
                          onClick={() => setConfirmId(null)}
                          disabled={retryMutation.isPending}
                          className="px-3 py-1 text-xs font-medium rounded bg-gray-700 hover:bg-gray-600 text-gray-300 disabled:opacity-50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmId(sub.id)}
                        disabled={retryMutation.isPending}
                        className="px-3 py-1 text-xs font-medium rounded bg-purple-700/40 hover:bg-purple-600/60 text-purple-300 border border-purple-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Retry Settlement
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Mutation error */}
      {retryMutation.isError && (
        <div className="mt-4 bg-red-900/30 border border-red-700 rounded-md p-3 text-red-300 text-sm">
          Retry failed: {retryMutation.error?.message || 'Unknown error'}
        </div>
      )}
    </div>
  )
}
