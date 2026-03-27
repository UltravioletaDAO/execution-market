import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet, adminFetch } from '../lib/api'

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

/** GET /admin/fees/accrued response */
interface AccruedFeesResponse {
  platform_wallet: string
  balance_usdc: number
  safety_buffer_usdc: number
  sweepable_usdc: number
  accrued_from_tasks_usdc: number
  operator_fees_pending_usdc: number
  operator_address: string
  treasury_address: string
  network: string
  token: string
  error?: string
}

/** POST /admin/fees/sweep response */
interface SweepFeesResponse {
  success: boolean
  tx_hash: string | null
  distribute_fees_tx: string | null
  amount_swept_usdc: number
  balance_before_usdc?: number
  treasury_address: string
  error?: string
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

async function fetchAccruedFees(
  adminKey: string,
  network: string,
  token: string = 'USDC',
): Promise<AccruedFeesResponse> {
  return adminGet<AccruedFeesResponse>('/api/v1/admin/fees/accrued', adminKey, {
    network,
    token,
  })
}

async function sweepFees(
  adminKey: string,
  network: string,
  token: string = 'USDC',
): Promise<SweepFeesResponse> {
  const params = new URLSearchParams({ network, token })
  const response = await adminFetch(
    `/api/v1/admin/fees/sweep?${params}`,
    adminKey,
    { method: 'POST' },
  )
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Sweep failed: ${response.status}`)
  }
  return response.json()
}

// ---------------------------------------------------------------------------
// Network configuration
// ---------------------------------------------------------------------------

const NETWORKS = [
  { value: 'base', label: 'Base' },
  { value: 'ethereum', label: 'Ethereum' },
  { value: 'polygon', label: 'Polygon' },
  { value: 'arbitrum', label: 'Arbitrum' },
  { value: 'optimism', label: 'Optimism' },
  { value: 'avalanche', label: 'Avalanche' },
  { value: 'celo', label: 'Celo' },
  { value: 'monad', label: 'Monad' },
  { value: 'skale', label: 'SKALE' },
] as const

const BLOCK_EXPLORERS: Record<string, { name: string; txUrl: string }> = {
  base: { name: 'Basescan', txUrl: 'https://basescan.org/tx/' },
  ethereum: { name: 'Etherscan', txUrl: 'https://etherscan.io/tx/' },
  polygon: { name: 'Polygonscan', txUrl: 'https://polygonscan.com/tx/' },
  arbitrum: { name: 'Arbiscan', txUrl: 'https://arbiscan.io/tx/' },
  optimism: { name: 'Optimism Explorer', txUrl: 'https://optimistic.etherscan.io/tx/' },
  avalanche: { name: 'Snowtrace', txUrl: 'https://snowtrace.io/tx/' },
  celo: { name: 'Celoscan', txUrl: 'https://celoscan.io/tx/' },
  monad: { name: 'Monad Explorer', txUrl: 'https://explorer.monad.xyz/tx/' },
  skale: { name: 'SKALE Explorer', txUrl: 'https://elated-tan-skat.explorer.mainnet.skalenodes.com/tx/' },
}

function getExplorerTxUrl(network: string, txHash: string): string {
  const explorer = BLOCK_EXPLORERS[network] || BLOCK_EXPLORERS['base']
  return `${explorer.txUrl}${txHash}`
}

function getExplorerName(network: string): string {
  return BLOCK_EXPLORERS[network]?.name || 'Explorer'
}

// ---------------------------------------------------------------------------
// Display maps (values match backend output exactly)
// ---------------------------------------------------------------------------

/** Transaction type badge colors -- keys match backend type_map values */
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

/** Strategy badge -- backend always returns "x402_escrow" */
const strategyLabels: Record<string, string> = {
  x402_escrow: 'x402 Escrow',
}

const strategyColors: Record<string, string> = {
  x402_escrow: 'bg-indigo-600',
}

/** Status colors -- keys match backend status_map values */
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
  const [feeNetwork, setFeeNetwork] = useState('base')
  const [showSweepConfirm, setShowSweepConfirm] = useState(false)
  const [sweepResult, setSweepResult] = useState<SweepFeesResponse | null>(null)

  const queryClient = useQueryClient()

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

  const {
    data: accruedFees,
    isLoading: feesLoading,
    isError: feesError,
    refetch: refetchFees,
  } = useQuery({
    queryKey: ['accruedFees', adminKey, feeNetwork],
    queryFn: () => fetchAccruedFees(adminKey, feeNetwork),
    enabled: !!adminKey,
  })

  const sweepMutation = useMutation({
    mutationFn: () => sweepFees(adminKey, feeNetwork),
    onSuccess: (data) => {
      setSweepResult(data)
      setShowSweepConfirm(false)
      // Refresh fee data after sweep
      queryClient.invalidateQueries({ queryKey: ['accruedFees'] })
      queryClient.invalidateQueries({ queryKey: ['paymentStats'] })
    },
    onError: () => {
      setShowSweepConfirm(false)
    },
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
      {/* ================================================================= */}
      {/* FEE MANAGEMENT SECTION                                            */}
      {/* ================================================================= */}
      <div className="mb-10">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-white">Fee Management</h1>
          <select
            value={feeNetwork}
            onChange={(e) => {
              setFeeNetwork(e.target.value)
              setSweepResult(null)
            }}
            className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
          >
            {NETWORKS.map((n) => (
              <option key={n.value} value={n.value}>
                {n.label}
              </option>
            ))}
          </select>
        </div>

        {/* Accrued Fees Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {feesLoading ? (
            <div className="col-span-4 text-center py-8 text-gray-400">
              Loading fee data...
            </div>
          ) : feesError ? (
            <div className="col-span-4 text-center py-8 text-red-400">
              Failed to load fee data for {feeNetwork}.
            </div>
          ) : accruedFees?.error ? (
            <div className="col-span-4 text-center py-8 text-red-400">
              Error: {accruedFees.error}
            </div>
          ) : (
            <>
              <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
                <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-1">
                  Operator Pending Fees
                </h3>
                <div className="text-2xl font-bold text-em-400">
                  ${(accruedFees?.operator_fees_pending_usdc ?? 0).toFixed(4)}
                </div>
                <p className="text-gray-500 text-xs mt-1">
                  In operator contract, awaiting distributeFees()
                </p>
              </div>

              <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
                <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-1">
                  Platform Wallet Balance
                </h3>
                <div className="text-2xl font-bold text-white">
                  ${(accruedFees?.balance_usdc ?? 0).toFixed(4)}
                </div>
                <p className="text-gray-500 text-xs mt-1">
                  Buffer: ${(accruedFees?.safety_buffer_usdc ?? 0).toFixed(2)} reserved
                </p>
              </div>

              <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
                <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-1">
                  Sweepable Amount
                </h3>
                <div className="text-2xl font-bold text-green-400">
                  ${(accruedFees?.sweepable_usdc ?? 0).toFixed(4)}
                </div>
                <p className="text-gray-500 text-xs mt-1">
                  Available to send to treasury
                </p>
              </div>

              <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
                <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-1">
                  Accrued from Tasks
                </h3>
                <div className="text-2xl font-bold text-yellow-400">
                  ${(accruedFees?.accrued_from_tasks_usdc ?? 0).toFixed(4)}
                </div>
                <p className="text-gray-500 text-xs mt-1">
                  DB-tracked fee events (status: accrued)
                </p>
              </div>
            </>
          )}
        </div>

        {/* Addresses row */}
        {accruedFees && !accruedFees.error && !feesLoading && (
          <div className="bg-gray-800 rounded-lg p-4 mb-6 border border-gray-700 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Platform Wallet: </span>
              <span className="text-gray-300 font-mono">
                {accruedFees.platform_wallet
                  ? `${accruedFees.platform_wallet.slice(0, 6)}...${accruedFees.platform_wallet.slice(-4)}`
                  : '-'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Operator: </span>
              <span className="text-gray-300 font-mono">
                {accruedFees.operator_address
                  ? `${accruedFees.operator_address.slice(0, 6)}...${accruedFees.operator_address.slice(-4)}`
                  : '-'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Treasury: </span>
              <span className="text-gray-300 font-mono">
                {accruedFees.treasury_address
                  ? `${accruedFees.treasury_address.slice(0, 6)}...${accruedFees.treasury_address.slice(-4)}`
                  : '-'}
              </span>
            </div>
          </div>
        )}

        {/* Sweep button + result */}
        <div className="flex items-center gap-4 flex-wrap">
          <button
            onClick={() => {
              setSweepResult(null)
              setShowSweepConfirm(true)
            }}
            disabled={
              feesLoading ||
              sweepMutation.isPending ||
              !accruedFees ||
              !!accruedFees.error ||
              (accruedFees.sweepable_usdc <= 0 && accruedFees.operator_fees_pending_usdc <= 0)
            }
            className="px-6 py-2.5 bg-em-600 hover:bg-em-500 text-white font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {sweepMutation.isPending ? 'Sweeping...' : 'Sweep to Treasury'}
          </button>

          <button
            onClick={() => refetchFees()}
            disabled={feesLoading}
            className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors disabled:opacity-40"
          >
            Refresh
          </button>

          {/* Sweep error */}
          {sweepMutation.isError && (
            <span className="text-red-400 text-sm">
              Sweep failed: {(sweepMutation.error as Error).message}
            </span>
          )}
        </div>

        {/* Sweep result */}
        {sweepResult && (
          <div className={`mt-4 p-4 rounded-lg border ${
            sweepResult.success
              ? 'bg-green-900/20 border-green-700'
              : 'bg-red-900/20 border-red-700'
          }`}>
            <h4 className={`font-semibold mb-2 ${
              sweepResult.success ? 'text-green-400' : 'text-red-400'
            }`}>
              {sweepResult.success ? 'Sweep Completed' : 'Sweep Failed'}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
              {sweepResult.success && (
                <div>
                  <span className="text-gray-400">Amount swept: </span>
                  <span className="text-white font-mono">
                    ${sweepResult.amount_swept_usdc.toFixed(4)} USDC
                  </span>
                </div>
              )}
              {sweepResult.treasury_address && (
                <div>
                  <span className="text-gray-400">To treasury: </span>
                  <span className="text-gray-300 font-mono">
                    {sweepResult.treasury_address.slice(0, 6)}...{sweepResult.treasury_address.slice(-4)}
                  </span>
                </div>
              )}
              {sweepResult.distribute_fees_tx && (
                <div>
                  <span className="text-gray-400">distributeFees() tx: </span>
                  <a
                    href={getExplorerTxUrl(feeNetwork, sweepResult.distribute_fees_tx)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-em-400 hover:text-em-300 font-mono"
                  >
                    {sweepResult.distribute_fees_tx.slice(0, 10)}... [{getExplorerName(feeNetwork)}]
                  </a>
                </div>
              )}
              {sweepResult.tx_hash && (
                <div>
                  <span className="text-gray-400">Sweep tx: </span>
                  <a
                    href={getExplorerTxUrl(feeNetwork, sweepResult.tx_hash)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-em-400 hover:text-em-300 font-mono"
                  >
                    {sweepResult.tx_hash.slice(0, 10)}... [{getExplorerName(feeNetwork)}]
                  </a>
                </div>
              )}
              {sweepResult.error && (
                <div className="col-span-2">
                  <span className="text-gray-400">Error: </span>
                  <span className="text-red-400">{sweepResult.error}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Sweep Confirmation Modal */}
      {showSweepConfirm && accruedFees && (
        <SweepConfirmModal
          network={feeNetwork}
          accruedFees={accruedFees}
          isPending={sweepMutation.isPending}
          onConfirm={() => sweepMutation.mutate()}
          onCancel={() => setShowSweepConfirm(false)}
        />
      )}

      {/* ================================================================= */}
      {/* PAYMENTS & TRANSACTIONS SECTION                                    */}
      {/* ================================================================= */}
      <div className="border-t border-gray-700 pt-8">
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
                          href={getExplorerTxUrl('base', tx.tx_hash)}
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

function SweepConfirmModal({
  network,
  accruedFees,
  isPending,
  onConfirm,
  onCancel,
}: {
  network: string
  accruedFees: AccruedFeesResponse
  isPending: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  const networkLabel = NETWORKS.find((n) => n.value === network)?.label ?? network

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-xl border border-gray-600 shadow-2xl max-w-lg w-full mx-4 p-6">
        <h3 className="text-xl font-bold text-white mb-4">
          Confirm Fee Sweep
        </h3>
        <p className="text-gray-300 text-sm mb-6">
          This will call distributeFees() on the operator contract and sweep the
          platform wallet balance to the treasury. This action triggers on-chain
          transactions and cannot be undone.
        </p>

        <div className="space-y-3 mb-6">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Network</span>
            <span className="text-white font-medium">{networkLabel}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Operator fees pending</span>
            <span className="text-em-400 font-mono">
              ${accruedFees.operator_fees_pending_usdc.toFixed(4)} USDC
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Platform wallet sweepable</span>
            <span className="text-green-400 font-mono">
              ${accruedFees.sweepable_usdc.toFixed(4)} USDC
            </span>
          </div>
          <div className="border-t border-gray-700 pt-3 flex justify-between text-sm">
            <span className="text-gray-400">Treasury destination</span>
            <span className="text-gray-300 font-mono text-xs">
              {accruedFees.treasury_address}
            </span>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={isPending}
            className="px-5 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="px-5 py-2 bg-em-600 hover:bg-em-500 text-white font-medium rounded-lg transition-colors disabled:opacity-40"
          >
            {isPending ? 'Sweeping...' : 'Confirm Sweep'}
          </button>
        </div>
      </div>
    </div>
  )
}
