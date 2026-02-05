import { useTranslation } from 'react-i18next'
import { usePublicMetrics } from '../../hooks/usePublicMetrics'

function formatCount(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

export function StatsBar() {
  const { t } = useTranslation()
  const { metrics, loading } = usePublicMetrics()

  const stats = [
    {
      value: metrics ? formatCount(metrics.users.registered_workers) : (loading ? '...' : '0'),
      label: t('landing.stats.registeredUsers', 'Registered Users'),
    },
    {
      value: metrics ? formatCount(metrics.activity.workers_with_active_tasks) : (loading ? '...' : '0'),
      label: t('landing.stats.activeWorkers', 'Workers Taking Tasks'),
    },
    {
      value: metrics ? formatCount(metrics.tasks.completed) : (loading ? '...' : '0'),
      label: t('landing.stats.completedTasks', 'Completed Tasks'),
    },
  ]

  return (
    <div className="flex items-center justify-center gap-8 md:gap-12 py-4 border-y border-gray-200">
      {stats.map((stat, i) => (
        <div key={i} className="text-center">
          <div className="text-xl md:text-2xl font-bold text-amber-500">{stat.value}</div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">{stat.label}</div>
        </div>
      ))}
    </div>
  )
}
