// Execution Market: Earnings Card Component
import { useTranslation } from 'react-i18next'
import type { EarningsData } from '../../hooks/useProfile'

interface EarningsCardProps {
  earnings: EarningsData | null
  loading: boolean
  onWithdraw: () => void
}

export function EarningsCard({ earnings, loading, onWithdraw }: EarningsCardProps) {
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

  const balance = earnings?.balance_usdc || 0
  const totalEarned = earnings?.total_earned_usdc || 0
  const pending = earnings?.pending_earnings_usdc || 0
  const thisMonth = earnings?.this_month_usdc || 0
  const lastMonth = earnings?.last_month_usdc || 0

  // Calculate month-over-month change
  const monthChange = lastMonth > 0
    ? ((thisMonth - lastMonth) / lastMonth) * 100
    : thisMonth > 0 ? 100 : 0

  return (
    <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl shadow-lg p-6 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-blue-100 text-sm font-medium">
          {t('profile.availableBalance', 'Available Balance')}
        </h3>
        <div className="flex items-center gap-1 text-blue-200">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          <span className="text-xs">USDC</span>
        </div>
      </div>

      {/* Balance */}
      <div className="mb-6">
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-bold">${balance.toFixed(2)}</span>
          {pending > 0 && (
            <span className="text-blue-200 text-sm">
              +${pending.toFixed(2)} {t('profile.pending', 'pending')}
            </span>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white/10 rounded-lg p-3">
          <div className="text-blue-200 text-xs mb-1">
            {t('profile.totalEarned', 'Total Earned')}
          </div>
          <div className="text-lg font-semibold">${totalEarned.toFixed(2)}</div>
        </div>
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
      </div>

      {/* Withdraw button */}
      <button
        onClick={onWithdraw}
        disabled={balance <= 0}
        className={`w-full py-3 rounded-lg font-medium transition-all ${
          balance > 0
            ? 'bg-white text-blue-600 hover:bg-blue-50 active:scale-98'
            : 'bg-white/20 text-blue-200 cursor-not-allowed'
        }`}
      >
        {t('profile.withdraw', 'Withdraw Funds')}
      </button>
    </div>
  )
}
