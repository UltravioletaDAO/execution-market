// Execution Market: Earnings Card Component (read-only lifetime stats)
//
// NOTE: This card shows HISTORICAL earnings only (lifetime + monthly).
// It does NOT show a withdrawable balance — in ADR-001 (agent-signed escrow)
// funds flow directly from agent to the worker's wallet on-chain. There is no
// custodial platform balance. For wallet actions (send/receive/export) see
// the WalletSection component.
import { useTranslation } from 'react-i18next'
import type { EarningsData } from '../../hooks/useProfile'

interface EarningsCardProps {
  earnings: EarningsData | null
  loading: boolean
}

export function EarningsCard({ earnings, loading }: EarningsCardProps) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2 mb-6"></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="h-12 bg-gray-200 rounded"></div>
            <div className="h-12 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  const totalEarned = earnings?.total_earned_usdc || 0
  const pending = earnings?.pending_earnings_usdc || 0
  const thisMonth = earnings?.this_month_usdc || 0
  const lastMonth = earnings?.last_month_usdc || 0

  const monthChange = lastMonth > 0
    ? ((thisMonth - lastMonth) / lastMonth) * 100
    : thisMonth > 0 ? 100 : 0

  return (
    <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl shadow-lg p-6 text-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-blue-100 text-sm font-medium">
          {t('profile.lifetimeEarnings', 'Lifetime Earnings')}
        </h3>
        <div className="flex items-center gap-1 text-blue-200">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          <span className="text-xs">USDC</span>
        </div>
      </div>

      <div className="mb-6">
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-bold">${totalEarned.toFixed(2)}</span>
          {pending > 0 && (
            <span className="text-blue-200 text-sm">
              +${pending.toFixed(2)} {t('profile.pending', 'pending')}
            </span>
          )}
        </div>
        <p className="text-blue-200 text-xs mt-1">
          {t('profile.earningsNote', 'Paid directly to your wallet on-chain.')}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-blue-200 text-xs mb-1">
            {t('profile.thisMonth', 'This Month')}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold">${thisMonth.toFixed(2)}</span>
            {monthChange !== 0 && (
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                monthChange > 0
                  ? 'bg-green-400/20 text-green-200'
                  : 'bg-red-400/20 text-red-200'
              }`}>
                {monthChange > 0 ? '+' : ''}{monthChange.toFixed(0)}%
              </span>
            )}
          </div>
        </div>
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-blue-200 text-xs mb-1">
            {t('profile.lastMonth', 'Last Month')}
          </div>
          <span className="text-lg font-semibold">${lastMonth.toFixed(2)}</span>
        </div>
      </div>
    </div>
  )
}
