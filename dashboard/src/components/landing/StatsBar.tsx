import { useTranslation } from 'react-i18next'
import { usePublicMetrics } from '../../hooks/usePublicMetrics'

function formatCount(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

function formatUsd(value: number): string {
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`
  return `$${value.toFixed(2)}`
}

export function StatsBar() {
  const { t } = useTranslation()
  const { metrics, loading } = usePublicMetrics()
  const totalRegisteredUsers = metrics
    ? (metrics.users.registered_workers || 0) + (metrics.users.registered_agents || 0)
    : 0

  const stats = [
    {
      value: metrics ? formatCount(metrics.tasks.live) : (loading ? '...' : '0'),
      label: t('landing.stats.liveTasks', 'Live Tasks'),
    },
    {
      value: metrics ? formatCount(totalRegisteredUsers) : (loading ? '...' : '0'),
      label: t('landing.stats.registeredUsers', 'Registered Users'),
    },
    {
      value: metrics ? formatCount(metrics.tasks.completed) : (loading ? '...' : '0'),
      label: t('landing.stats.completedTasks', 'Completed Tasks'),
    },
    {
      value: metrics ? formatUsd(metrics.payments.total_volume_usd) : (loading ? '...' : '$0'),
      label: t('landing.stats.totalPaid', 'Total Paid Out'),
    },
  ]

  return (
    <div className="flex items-center justify-center gap-6 md:gap-10 py-4 border-y border-gray-200 flex-wrap">
      {stats.map((stat, i) => (
        <div key={i} className="text-center">
          <div className="text-xl md:text-2xl font-bold text-amber-500">{stat.value}</div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">{stat.label}</div>
        </div>
      ))}
    </div>
  )
}
