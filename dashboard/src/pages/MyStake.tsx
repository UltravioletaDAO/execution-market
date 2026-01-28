/**
 * MyStake Page (NOW-038)
 *
 * Shows worker's stake status, locked amounts, and slashing history.
 * Allows workers to stake/unstake tokens for validation participation.
 */

import { useState, useCallback, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { Executor } from '../types/database'

// ============================================================================
// TYPES
// ============================================================================

export interface MyStakeProps {
  executor: Executor
  onBack?: () => void
}

interface StakeData {
  available_stake: number
  locked_stake: number
  total_stake: number
  min_stake_required: number
  pending_rewards: number
  lifetime_rewards: number
  can_unstake: boolean
  unstake_cooldown_ends: string | null
}

interface SlashingEvent {
  id: string
  amount: number
  reason: string
  task_id: string
  task_title: string
  created_at: string
  tx_hash: string | null
}

interface StakeAction {
  id: string
  type: 'stake' | 'unstake' | 'reward' | 'slash'
  amount: number
  balance_after: number
  created_at: string
  tx_hash: string | null
  description: string
}

interface ActiveLock {
  task_id: string
  task_title: string
  locked_amount: number
  locked_at: string
  estimated_unlock: string
  status: 'validating' | 'dispute_pending' | 'releasing'
}

// ============================================================================
// MOCK DATA HOOKS (Replace with real API calls)
// ============================================================================

function useStakeData(executorId: string) {
  const [data, setData] = useState<StakeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        // Mock data - replace with actual API call
        await new Promise(resolve => setTimeout(resolve, 500))
        setData({
          available_stake: 150.00,
          locked_stake: 50.00,
          total_stake: 200.00,
          min_stake_required: 100.00,
          pending_rewards: 12.50,
          lifetime_rewards: 245.75,
          can_unstake: true,
          unstake_cooldown_ends: null,
        })
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch stake data'))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [executorId])

  const refetch = useCallback(async () => {
    setLoading(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 300))
      // Refetch logic
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, refetch }
}

function useSlashingHistory(executorId: string) {
  const [history, setHistory] = useState<SlashingEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true)
      try {
        await new Promise(resolve => setTimeout(resolve, 400))
        // Mock data - replace with actual API call
        setHistory([
          {
            id: 'slash_1',
            amount: 5.00,
            reason: 'Failed validation - incorrect evidence review',
            task_id: 'task_abc123',
            task_title: 'Verify store opening hours',
            created_at: '2026-01-20T14:30:00Z',
            tx_hash: '0x1234...abcd',
          },
          {
            id: 'slash_2',
            amount: 10.00,
            reason: 'Dispute lost - biased validation',
            task_id: 'task_def456',
            task_title: 'Photo verification at location',
            created_at: '2026-01-15T09:15:00Z',
            tx_hash: '0x5678...efgh',
          },
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [executorId])

  return { history, loading }
}

function useActiveLocks(executorId: string) {
  const [locks, setLocks] = useState<ActiveLock[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchLocks = async () => {
      setLoading(true)
      try {
        await new Promise(resolve => setTimeout(resolve, 350))
        // Mock data
        setLocks([
          {
            task_id: 'task_xyz789',
            task_title: 'Validate delivery confirmation',
            locked_amount: 25.00,
            locked_at: '2026-01-24T10:00:00Z',
            estimated_unlock: '2026-01-25T10:00:00Z',
            status: 'validating',
          },
          {
            task_id: 'task_uvw012',
            task_title: 'Review medical document submission',
            locked_amount: 25.00,
            locked_at: '2026-01-23T15:30:00Z',
            estimated_unlock: '2026-01-26T15:30:00Z',
            status: 'dispute_pending',
          },
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchLocks()
  }, [executorId])

  return { locks, loading }
}

function useStakeHistory(executorId: string) {
  const [history, setHistory] = useState<StakeAction[]>([])
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true)
      try {
        await new Promise(resolve => setTimeout(resolve, 400))
        setHistory([
          {
            id: 'action_1',
            type: 'reward',
            amount: 5.50,
            balance_after: 200.00,
            created_at: '2026-01-24T16:00:00Z',
            tx_hash: '0xaaaa...1111',
            description: 'Validation reward for task #xyz789',
          },
          {
            id: 'action_2',
            type: 'stake',
            amount: 50.00,
            balance_after: 194.50,
            created_at: '2026-01-22T12:00:00Z',
            tx_hash: '0xbbbb...2222',
            description: 'Added stake',
          },
          {
            id: 'action_3',
            type: 'slash',
            amount: -5.00,
            balance_after: 144.50,
            created_at: '2026-01-20T14:30:00Z',
            tx_hash: '0x1234...abcd',
            description: 'Slashed for incorrect validation',
          },
          {
            id: 'action_4',
            type: 'reward',
            amount: 8.25,
            balance_after: 149.50,
            created_at: '2026-01-18T09:00:00Z',
            tx_hash: '0xcccc...3333',
            description: 'Validation rewards (3 tasks)',
          },
        ])
        setHasMore(false)
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [executorId])

  const loadMore = useCallback(async () => {
    // Load more logic
  }, [])

  return { history, loading, hasMore, loadMore }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('es-MX', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('es-MX', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffMs < 0) return 'Expired'
  if (diffHours < 1) return 'Less than 1 hour'
  if (diffHours < 24) return `${diffHours}h remaining`
  return `${diffDays}d remaining`
}

function shortenTxHash(hash: string | null): string {
  if (!hash) return '-'
  return `${hash.slice(0, 6)}...${hash.slice(-4)}`
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function StakeOverviewCard({
  data,
  loading,
  onStake,
  onUnstake,
  onClaimRewards,
}: {
  data: StakeData | null
  loading: boolean
  onStake: () => void
  onUnstake: () => void
  onClaimRewards: () => void
}) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-xl p-6 text-white">
        <div className="animate-pulse">
          <div className="h-4 bg-indigo-400/50 rounded w-1/3 mb-4"></div>
          <div className="h-10 bg-indigo-400/50 rounded w-1/2 mb-6"></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 bg-indigo-400/50 rounded"></div>
            <div className="h-16 bg-indigo-400/50 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!data) return null

  const stakePercentage = (data.locked_stake / data.total_stake) * 100

  return (
    <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-xl shadow-lg p-6 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-indigo-100 text-sm font-medium">
          {t('stake.totalStake', 'Total Stake')}
        </h2>
        <div className="flex items-center gap-1 text-indigo-200">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          <span className="text-xs">USDC</span>
        </div>
      </div>

      {/* Total Balance */}
      <div className="mb-4">
        <span className="text-4xl font-bold">{formatCurrency(data.total_stake)}</span>
      </div>

      {/* Stake Breakdown Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs text-indigo-200 mb-1">
          <span>{t('stake.available', 'Available')}: {formatCurrency(data.available_stake)}</span>
          <span>{t('stake.locked', 'Locked')}: {formatCurrency(data.locked_stake)}</span>
        </div>
        <div className="h-2 bg-indigo-400/30 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-300 rounded-full transition-all duration-300"
            style={{ width: `${100 - stakePercentage}%` }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-indigo-200 text-xs mb-1">
            {t('stake.pendingRewards', 'Pending Rewards')}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold">{formatCurrency(data.pending_rewards)}</span>
            {data.pending_rewards > 0 && (
              <button
                onClick={onClaimRewards}
                className="text-xs px-2 py-0.5 bg-green-400/20 text-green-200 rounded hover:bg-green-400/30 transition-colors"
              >
                {t('stake.claim', 'Claim')}
              </button>
            )}
          </div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-indigo-200 text-xs mb-1">
            {t('stake.lifetimeRewards', 'Lifetime Rewards')}
          </div>
          <div className="text-lg font-semibold">{formatCurrency(data.lifetime_rewards)}</div>
        </div>
      </div>

      {/* Minimum Stake Info */}
      {data.total_stake < data.min_stake_required && (
        <div className="mb-4 p-3 bg-amber-400/20 rounded-lg text-amber-200 text-sm">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>
              {t('stake.minRequired', 'Minimum stake required to validate')}: {formatCurrency(data.min_stake_required)}
            </span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={onStake}
          className="flex-1 py-2.5 bg-white text-indigo-600 font-medium rounded-lg hover:bg-indigo-50 transition-colors"
        >
          {t('stake.addStake', 'Add Stake')}
        </button>
        <button
          onClick={onUnstake}
          disabled={!data.can_unstake || data.available_stake <= 0}
          className={`flex-1 py-2.5 font-medium rounded-lg transition-colors ${
            data.can_unstake && data.available_stake > 0
              ? 'bg-white/20 text-white hover:bg-white/30'
              : 'bg-white/10 text-indigo-300 cursor-not-allowed'
          }`}
        >
          {t('stake.unstake', 'Unstake')}
        </button>
      </div>

      {/* Cooldown Notice */}
      {data.unstake_cooldown_ends && (
        <p className="text-xs text-indigo-200 text-center mt-2">
          {t('stake.cooldownActive', 'Unstaking available after')}: {formatDateTime(data.unstake_cooldown_ends)}
        </p>
      )}
    </div>
  )
}

function ActiveLocksSection({ locks, loading }: { locks: ActiveLock[]; loading: boolean }) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="h-5 bg-gray-200 rounded w-1/3 animate-pulse"></div>
        </div>
        <div className="p-6 space-y-3">
          <div className="h-16 bg-gray-100 rounded animate-pulse"></div>
          <div className="h-16 bg-gray-100 rounded animate-pulse"></div>
        </div>
      </section>
    )
  }

  const statusColors: Record<ActiveLock['status'], { bg: string; text: string; label: string }> = {
    validating: { bg: 'bg-blue-100', text: 'text-blue-700', label: t('stake.status.validating', 'Validating') },
    dispute_pending: { bg: 'bg-amber-100', text: 'text-amber-700', label: t('stake.status.disputePending', 'Dispute Pending') },
    releasing: { bg: 'bg-green-100', text: 'text-green-700', label: t('stake.status.releasing', 'Releasing') },
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          {t('stake.activeLocks', 'Active Locks')}
        </h2>
        {locks.length > 0 && (
          <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full">
            {locks.length}
          </span>
        )}
      </div>

      {locks.length === 0 ? (
        <div className="p-8 text-center">
          <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">
            {t('stake.noActiveLocks', 'No active stake locks')}
          </p>
          <p className="text-gray-400 text-sm mt-1">
            {t('stake.locksExplanation', 'Stake is locked when you validate tasks')}
          </p>
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {locks.map(lock => {
            const status = statusColors[lock.status]
            return (
              <div key={lock.task_id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-gray-900 font-medium text-sm truncate">
                        {lock.task_title}
                      </h4>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${status.bg} ${status.text}`}>
                        {status.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span>Locked: {formatDateTime(lock.locked_at)}</span>
                      <span className="text-gray-300">|</span>
                      <span className={lock.status === 'dispute_pending' ? 'text-amber-600' : ''}>
                        {formatRelativeTime(lock.estimated_unlock)}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-indigo-600 font-semibold">
                      {formatCurrency(lock.locked_amount)}
                    </div>
                    <div className="text-xs text-gray-400">locked</div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

function SlashingHistorySection({ history, loading }: { history: SlashingEvent[]; loading: boolean }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  if (loading) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="h-5 bg-gray-200 rounded w-1/3 animate-pulse"></div>
        </div>
        <div className="p-6">
          <div className="h-20 bg-gray-100 rounded animate-pulse"></div>
        </div>
      </section>
    )
  }

  const displayedHistory = expanded ? history : history.slice(0, 3)
  const totalSlashed = history.reduce((sum, event) => sum + event.amount, 0)

  return (
    <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {t('stake.slashingHistory', 'Slashing History')}
          </h2>
          {history.length > 0 && (
            <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full">
              {history.length} {t('stake.events', 'events')}
            </span>
          )}
        </div>
        {totalSlashed > 0 && (
          <span className="text-sm text-red-600 font-medium">
            -{formatCurrency(totalSlashed)} total
          </span>
        )}
      </div>

      {history.length === 0 ? (
        <div className="p-8 text-center">
          <div className="w-14 h-14 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-7 h-7 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">
            {t('stake.noSlashing', 'No slashing events')}
          </p>
          <p className="text-gray-400 text-sm mt-1">
            {t('stake.keepItUp', 'Keep up the good work!')}
          </p>
        </div>
      ) : (
        <>
          <div className="divide-y divide-gray-50">
            {displayedHistory.map(event => (
              <div key={event.id} className="px-6 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div>
                        <h4 className="text-gray-900 font-medium text-sm">
                          {event.task_title}
                        </h4>
                        <p className="text-xs text-gray-500">{event.reason}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-400 ml-10">
                      <span>{formatDate(event.created_at)}</span>
                      {event.tx_hash && (
                        <>
                          <span className="text-gray-300">|</span>
                          <a
                            href={`https://basescan.org/tx/${event.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:text-indigo-700"
                          >
                            {shortenTxHash(event.tx_hash)}
                          </a>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="text-red-600 font-semibold">
                    -{formatCurrency(event.amount)}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {history.length > 3 && (
            <div className="px-6 py-3 border-t border-gray-100">
              <button
                onClick={() => setExpanded(!expanded)}
                className="w-full py-2 text-indigo-600 hover:text-indigo-700 text-sm font-medium transition-colors"
              >
                {expanded
                  ? t('common.showLess', 'Show less')
                  : t('common.showMore', 'Show all ({count})', { count: history.length })
                }
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function StakeHistorySection({
  history,
  loading,
  hasMore,
  onLoadMore,
}: {
  history: StakeAction[]
  loading: boolean
  hasMore: boolean
  onLoadMore: () => void
}) {
  const { t } = useTranslation()

  const actionIcons: Record<StakeAction['type'], { icon: React.ReactNode; color: string }> = {
    stake: {
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      ),
      color: 'bg-indigo-100 text-indigo-600',
    },
    unstake: {
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
        </svg>
      ),
      color: 'bg-gray-100 text-gray-600',
    },
    reward: {
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ),
      color: 'bg-green-100 text-green-600',
    },
    slash: {
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      ),
      color: 'bg-red-100 text-red-600',
    },
  }

  if (loading && history.length === 0) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="h-5 bg-gray-200 rounded w-1/3 animate-pulse"></div>
        </div>
        <div className="p-6 space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-14 bg-gray-100 rounded animate-pulse"></div>
          ))}
        </div>
      </section>
    )
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">
          {t('stake.activityHistory', 'Stake Activity')}
        </h2>
      </div>

      {history.length === 0 ? (
        <div className="p-8 text-center">
          <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">
            {t('stake.noActivity', 'No stake activity yet')}
          </p>
        </div>
      ) : (
        <>
          <div className="divide-y divide-gray-50">
            {history.map(action => {
              const iconConfig = actionIcons[action.type]
              const isPositive = action.amount > 0

              return (
                <div key={action.id} className="px-6 py-3 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${iconConfig.color}`}>
                      {iconConfig.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-900">{action.description}</span>
                        <span className={`font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                          {isPositive ? '+' : ''}{formatCurrency(action.amount)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                        <span>{formatDateTime(action.created_at)}</span>
                        {action.tx_hash && (
                          <>
                            <span className="text-gray-300">|</span>
                            <a
                              href={`https://basescan.org/tx/${action.tx_hash}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-indigo-600 hover:text-indigo-700"
                            >
                              {shortenTxHash(action.tx_hash)}
                            </a>
                          </>
                        )}
                        <span className="text-gray-300">|</span>
                        <span>Balance: {formatCurrency(action.balance_after)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {hasMore && (
            <div className="px-6 py-3 border-t border-gray-100">
              <button
                onClick={onLoadMore}
                disabled={loading}
                className="w-full py-2 text-indigo-600 hover:text-indigo-700 text-sm font-medium transition-colors disabled:opacity-50"
              >
                {loading ? t('common.loading', 'Loading...') : t('common.loadMore', 'Load more')}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

// ============================================================================
// MODALS
// ============================================================================

function StakeModal({
  isOpen,
  onClose,
  mode,
  availableBalance,
  onConfirm,
}: {
  isOpen: boolean
  onClose: () => void
  mode: 'stake' | 'unstake'
  availableBalance: number
  onConfirm: (amount: number) => Promise<void>
}) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const amountNum = parseFloat(amount)

    if (isNaN(amountNum) || amountNum <= 0) {
      setError(t('stake.error.invalidAmount', 'Please enter a valid amount'))
      return
    }

    if (mode === 'unstake' && amountNum > availableBalance) {
      setError(t('stake.error.insufficientBalance', 'Insufficient available balance'))
      return
    }

    setLoading(true)
    setError(null)

    try {
      await onConfirm(amountNum)
      onClose()
      setAmount('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {mode === 'stake'
              ? t('stake.addStakeTitle', 'Add Stake')
              : t('stake.unstakeTitle', 'Unstake Tokens')
            }
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'unstake' && (
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-sm text-gray-600">
                {t('stake.availableToUnstake', 'Available to unstake')}
              </div>
              <div className="text-xl font-bold text-gray-900">
                {formatCurrency(availableBalance)}
              </div>
            </div>
          )}

          <div>
            <label htmlFor="stakeAmount" className="block text-sm font-medium text-gray-700 mb-2">
              {t('stake.amount', 'Amount (USDC)')}
            </label>
            <input
              id="stakeAmount"
              type="number"
              step="0.01"
              min="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              required
            />
            {mode === 'unstake' && (
              <button
                type="button"
                onClick={() => setAmount(availableBalance.toString())}
                className="mt-1 text-sm text-indigo-600 hover:text-indigo-700"
              >
                {t('stake.unstakeAll', 'Unstake all')}
              </button>
            )}
          </div>

          {mode === 'stake' && (
            <div className="p-3 bg-indigo-50 rounded-lg text-sm text-indigo-700">
              <p>{t('stake.stakeInfo', 'Staked tokens allow you to participate in task validation and earn rewards.')}</p>
            </div>
          )}

          {mode === 'unstake' && (
            <div className="p-3 bg-amber-50 rounded-lg text-sm text-amber-700">
              <p>{t('stake.unstakeWarning', 'Unstaking will reduce your validation capacity. A 24-hour cooldown applies.')}</p>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t('common.processing', 'Processing...')}
              </>
            ) : (
              mode === 'stake'
                ? t('stake.confirmStake', 'Confirm Stake')
                : t('stake.confirmUnstake', 'Confirm Unstake')
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function MyStake({ executor, onBack }: MyStakeProps) {
  const { t } = useTranslation()

  // Data hooks
  const { data: stakeData, loading: stakeLoading, refetch: refetchStake } = useStakeData(executor.id)
  const { locks, loading: locksLoading } = useActiveLocks(executor.id)
  const { history: slashingHistory, loading: slashingLoading } = useSlashingHistory(executor.id)
  const { history: stakeHistory, loading: historyLoading, hasMore, loadMore } = useStakeHistory(executor.id)

  // Modal state
  const [showStakeModal, setShowStakeModal] = useState(false)
  const [stakeMode, setStakeMode] = useState<'stake' | 'unstake'>('stake')

  // Handlers
  const handleStake = useCallback(() => {
    setStakeMode('stake')
    setShowStakeModal(true)
  }, [])

  const handleUnstake = useCallback(() => {
    setStakeMode('unstake')
    setShowStakeModal(true)
  }, [])

  const handleClaimRewards = useCallback(async () => {
    // TODO: Implement claim rewards
    console.log('Claiming rewards...')
    await refetchStake()
  }, [refetchStake])

  const handleConfirmStake = useCallback(async (amount: number) => {
    // TODO: Implement actual stake/unstake logic
    console.log(`${stakeMode}ing ${amount} USDC...`)
    await new Promise(resolve => setTimeout(resolve, 1000))
    await refetchStake()
  }, [stakeMode, refetchStake])

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-8">
      {/* Navigation */}
      <div className="flex items-center justify-between">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-sm font-medium">{t('common.back', 'Back')}</span>
          </button>
        )}
        <h1 className="text-xl font-bold text-gray-900">
          {t('stake.title', 'My Stake')}
        </h1>
        <div className="w-16" /> {/* Spacer for centering */}
      </div>

      {/* Info Banner */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-indigo-900 mb-1">
              {t('stake.whatIsStaking', 'What is Staking?')}
            </h3>
            <p className="text-sm text-indigo-700">
              {t('stake.stakingExplanation', 'Staking allows you to validate other workers\' task submissions and earn rewards. Your stake acts as collateral - incorrect validations may result in partial slashing.')}
            </p>
          </div>
        </div>
      </div>

      {/* Stake Overview */}
      <StakeOverviewCard
        data={stakeData}
        loading={stakeLoading}
        onStake={handleStake}
        onUnstake={handleUnstake}
        onClaimRewards={handleClaimRewards}
      />

      {/* Active Locks */}
      <ActiveLocksSection locks={locks} loading={locksLoading} />

      {/* Slashing History */}
      <SlashingHistorySection history={slashingHistory} loading={slashingLoading} />

      {/* Stake Activity History */}
      <StakeHistorySection
        history={stakeHistory}
        loading={historyLoading}
        hasMore={hasMore}
        onLoadMore={loadMore}
      />

      {/* Stake/Unstake Modal */}
      <StakeModal
        isOpen={showStakeModal}
        onClose={() => setShowStakeModal(false)}
        mode={stakeMode}
        availableBalance={stakeData?.available_stake || 0}
        onConfirm={handleConfirmStake}
      />
    </div>
  )
}

export default MyStake
