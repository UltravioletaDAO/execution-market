import { useQuery } from '@tanstack/react-query'
import { adminGet } from '../lib/api'

interface EscrowReconciliation {
  checked: number
  pass: number
  fail: number
  errors: Array<{
    task_id: string
    issues: string[]
    status: string
  }>
}

interface OpenEscrow {
  task_id: string
  amount: number
  status: string
  age_hours: number
}

interface AuditSummary {
  period: string
  tasks_created: number
  tasks_by_status: Record<string, number>
  total_bounty_usd: number
  payments_released: number
  payments_refunded: number
  total_released_usd: number
  total_refunded_usd: number
  estimated_fees_usd: number
  escrow_reconciliation: EscrowReconciliation
  open_escrows: OpenEscrow[]
}

interface FinancialAuditProps {
  adminKey: string
}

const escrowStatusColors: Record<string, string> = {
  deposited: 'text-yellow-400',
  pending: 'text-blue-400',
  locked: 'text-em-400',
}

function formatUSD(amount: number): string {
  return `$${amount.toFixed(6)}`
}

function formatTimestamp(date: Date): string {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export default function FinancialAudit({ adminKey }: FinancialAuditProps) {
  const {
    data,
    isLoading,
    isError,
    error,
    dataUpdatedAt,
    refetch,
    isFetching,
  } = useQuery<AuditSummary>({
    queryKey: ['audit-summary'],
    queryFn: () => adminGet<AuditSummary>('/api/v1/admin/audit/summary', adminKey),
    enabled: !!adminKey,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-48" />
          <div className="grid grid-cols-3 gap-4">
            <div className="h-24 bg-gray-700 rounded" />
            <div className="h-24 bg-gray-700 rounded" />
            <div className="h-24 bg-gray-700 rounded" />
          </div>
          <div className="h-32 bg-gray-700 rounded" />
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="bg-gray-800 rounded-lg border border-red-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-2">Financial Audit</h2>
        <p className="text-red-400 text-sm">
          Failed to load audit summary: {error instanceof Error ? error.message : 'Unknown error'}
        </p>
        <button
          onClick={() => refetch()}
          className="mt-3 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data) return null

  const recon = data.escrow_reconciliation
  const hasDiscrepancies = recon.fail > 0
  const completedCount = data.tasks_by_status['completed'] ?? 0
  const cancelledCount = data.tasks_by_status['cancelled'] ?? 0

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Financial Audit -- Last 24h</h2>
          {dataUpdatedAt > 0 && (
            <p className="text-gray-500 text-xs mt-1">
              Last updated: {formatTimestamp(new Date(dataUpdatedAt))}
            </p>
          )}
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="px-4 py-2 bg-em-600 hover:bg-em-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded transition-colors"
        >
          {isFetching ? 'Refreshing...' : 'Refresh Audit'}
        </button>
      </div>

      {/* Tasks Section */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Tasks</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Created</p>
            <p className="text-2xl font-bold text-white">{data.tasks_created}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Completed</p>
            <p className="text-2xl font-bold text-green-400">{completedCount}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Cancelled</p>
            <p className="text-2xl font-bold text-red-400">{cancelledCount}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Total Bounty</p>
            <p className="text-2xl font-bold text-em-400">${data.total_bounty_usd.toFixed(2)}</p>
          </div>
        </div>
        {Object.keys(data.tasks_by_status).length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(data.tasks_by_status).map(([status, count]) => (
              <span
                key={status}
                className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-gray-700 text-gray-300"
              >
                {status}: {count}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Volume Section */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Volume</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Released (count)</p>
            <p className="text-2xl font-bold text-green-400">{data.payments_released}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Released (USD)</p>
            <p className="text-2xl font-bold text-green-400">{formatUSD(data.total_released_usd)}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Refunded (count)</p>
            <p className="text-2xl font-bold text-yellow-400">{data.payments_refunded}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Fees Collected (est.)</p>
            <p className="text-2xl font-bold text-em-400">{formatUSD(data.estimated_fees_usd)}</p>
          </div>
        </div>
        {data.total_refunded_usd > 0 && (
          <p className="mt-2 text-gray-500 text-xs">
            Total refunded: {formatUSD(data.total_refunded_usd)}
          </p>
        )}
      </div>

      {/* Escrow Reconciliation */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
          Escrow Reconciliation
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Checked</p>
            <p className="text-2xl font-bold text-white">{recon.checked}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-xs mb-1">Passed</p>
            <p className="text-2xl font-bold text-green-400">{recon.pass}</p>
          </div>
          <div className={`bg-gray-900 rounded-lg p-4 ${hasDiscrepancies ? 'ring-1 ring-red-500' : ''}`}>
            <p className="text-gray-500 text-xs mb-1">Failed</p>
            <p className={`text-2xl font-bold ${hasDiscrepancies ? 'text-red-400' : 'text-green-400'}`}>
              {recon.fail}
            </p>
          </div>
        </div>

        {/* Discrepancies */}
        {hasDiscrepancies ? (
          <div className="mt-3 bg-red-900/20 border border-red-700 rounded-lg p-4">
            <p className="text-red-400 font-medium text-sm mb-2">
              {recon.fail} discrepanc{recon.fail === 1 ? 'y' : 'ies'} detected
            </p>
            <ul className="space-y-2">
              {recon.errors.map((err, idx) => (
                <li key={idx} className="text-sm">
                  <span className="text-gray-400 font-mono text-xs">{err.task_id.slice(0, 8)}...</span>
                  <span className="text-gray-500 mx-1">|</span>
                  <span className="text-red-300">{err.issues.join(', ')}</span>
                  <span className="text-gray-600 ml-1">({err.status})</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="mt-3 bg-green-900/20 border border-green-700 rounded-lg p-4">
            <p className="text-green-400 font-medium text-sm">
              All clear -- {recon.checked} escrow{recon.checked !== 1 ? 's' : ''} verified, no discrepancies.
            </p>
          </div>
        )}
      </div>

      {/* Open Escrows */}
      {data.open_escrows.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            Open Escrows ({data.open_escrows.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs uppercase border-b border-gray-700">
                  <th className="text-left py-2 pr-4">Task</th>
                  <th className="text-right py-2 pr-4">Amount</th>
                  <th className="text-left py-2 pr-4">Status</th>
                  <th className="text-right py-2">Age (h)</th>
                </tr>
              </thead>
              <tbody>
                {data.open_escrows.map((esc, idx) => (
                  <tr key={idx} className="border-b border-gray-700/50">
                    <td className="py-2 pr-4 font-mono text-gray-300 text-xs">
                      {esc.task_id.slice(0, 12)}...
                    </td>
                    <td className="py-2 pr-4 text-right text-white">
                      ${esc.amount.toFixed(2)}
                    </td>
                    <td className={`py-2 pr-4 ${escrowStatusColors[esc.status] ?? 'text-gray-400'}`}>
                      {esc.status}
                    </td>
                    <td className={`py-2 text-right ${esc.age_hours > 48 ? 'text-red-400' : 'text-gray-400'}`}>
                      {esc.age_hours}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
