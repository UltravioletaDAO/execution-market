import { useState, useMemo, Suspense, lazy } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTranslation } from 'react-i18next'
import { useEarnings, useTaskHistory } from '../hooks/useProfile'
import type { ChartPeriod } from './Earnings'

const Earnings = lazy(() => import('./Earnings').then(m => ({ default: m.Earnings })))

export function EarningsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { executor } = useAuth()
  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>('month')

  const { earnings, loading: earningsLoading, error } = useEarnings(executor?.id)
  const { history, loading: historyLoading } = useTaskHistory(executor?.id, 20)

  const thisWeekUsdc = useMemo(() => {
    const cutoff = Date.now() - (7 * 24 * 60 * 60 * 1000)
    return history
      .filter((item) => item.status === 'approved' && new Date(item.submitted_at).getTime() >= cutoff)
      .reduce((sum, item) => sum + (item.payment_amount ?? item.bounty_usd ?? 0), 0)
  }, [history])

  const summary = useMemo(() => {
    if (!earnings) return null
    return {
      total_earned_usdc: earnings.total_earned_usdc ?? 0,
      available_balance_usdc: earnings.balance_usdc ?? 0,
      pending_usdc: earnings.pending_earnings_usdc ?? 0,
      this_month_usdc: earnings.this_month_usdc ?? 0,
      last_month_usdc: earnings.last_month_usdc ?? 0,
      this_week_usdc: thisWeekUsdc,
    }
  }, [earnings, thisWeekUsdc])

  const transactions = useMemo(() => {
    return history.map((item) => ({
      id: item.id,
      type: 'task_payment' as const,
      amount_usdc: item.payment_amount ?? item.bounty_usd ?? 0,
      status: (item.status === 'approved'
        ? 'completed'
        : item.status === 'rejected'
          ? 'failed'
          : 'pending') as 'completed' | 'failed' | 'pending',
      tx_hash: null,
      network: item.payment_network || 'base',
      created_at: item.verified_at ?? item.submitted_at,
      task_title: item.task_title,
      task_id: item.task_id,
    }))
  }, [history])

  const pendingPayments = useMemo(() => {
    return history
      .filter((item) => item.status === 'pending')
      .map((item) => ({
        id: item.id,
        task_id: item.task_id,
        task_title: item.task_title,
        bounty_usd: item.bounty_usd ?? 0,
        submitted_at: item.submitted_at,
        expected_payout_date: new Date(new Date(item.submitted_at).getTime() + (48 * 60 * 60 * 1000)).toISOString(),
        status: 'awaiting_review' as const,
      }))
  }, [history])

  const chartData = useMemo(() => {
    if (!summary) return []

    if (chartPeriod === 'week') {
      return [
        { label: t('dashboard.thisWeek', 'Last 7 days'), value: summary.this_week_usdc },
        { label: t('profile.pending', 'Pending'), value: summary.pending_usdc },
      ]
    }

    if (chartPeriod === 'year') {
      return [
        { label: 'Q1', value: summary.this_month_usdc },
        { label: 'Q2', value: summary.this_month_usdc },
        { label: 'Q3', value: summary.last_month_usdc },
        { label: 'Q4', value: summary.last_month_usdc },
      ]
    }

    return [
      { label: t('profile.thisMonth', 'This month'), value: summary.this_month_usdc },
      { label: t('analytics.lastMonth', 'Last month'), value: summary.last_month_usdc },
      { label: t('profile.pending', 'Pending'), value: summary.pending_usdc },
    ]
  }, [summary, chartPeriod, t])

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate('/tasks')}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="font-bold text-lg text-gray-900">{t('dashboard.myEarnings')}</h1>
      </div>
      <Suspense fallback={null}>
        <Earnings
          summary={summary}
          transactions={transactions}
          pendingPayments={pendingPayments}
          chartData={chartData}
          loading={earningsLoading || historyLoading}
          error={error}
          onWithdraw={() => navigate('/profile')}
          onChartPeriodChange={setChartPeriod}
          chartPeriod={chartPeriod}
        />
      </Suspense>
    </div>
  )
}

export default EarningsPage
