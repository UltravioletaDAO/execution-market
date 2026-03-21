/**
 * Karma Kadabra V2 — Task 6.4: Community Dashboard Widget
 *
 * Displays KK swarm activity on the Execution Market dashboard:
 *   - Active agents count
 *   - Tasks published today
 *   - Total USDC transacted
 *   - Agent leaderboard (most active)
 *   - Recent transactions feed
 */

import { memo, useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'
const REFRESH_INTERVAL = 60_000 // 1 minute

interface SwarmMetrics {
  activeAgents: number
  totalAgents: number
  tasksToday: number
  tasksTotal: number
  usdcTransacted: number
  topAgents: Array<{
    name: string
    tasks: number
    earned: number
  }>
  recentTasks: Array<{
    id: string
    title: string
    bounty: number
    status: string
    created: string
  }>
}

const DEFAULT_METRICS: SwarmMetrics = {
  activeAgents: 0,
  totalAgents: 39,
  tasksToday: 0,
  tasksTotal: 0,
  usdcTransacted: 0,
  topAgents: [],
  recentTasks: [],
}

async function fetchSwarmMetrics(): Promise<SwarmMetrics> {
  try {
    // Fetch available tasks with KK prefix
    const resp = await fetch(`${API_BASE}/api/v1/tasks/available?limit=50`)
    if (!resp.ok) return DEFAULT_METRICS

    const data = await resp.json()
    const tasks = data.tasks || data || []

    // Filter KK tasks
    const kkTasks = tasks.filter(
      (t: any) => t.title?.includes('[KK') || t.title?.includes('Karma Kadabra')
    )

    // Compute metrics from available data
    const today = new Date().toISOString().slice(0, 10)
    const tasksToday = kkTasks.filter(
      (t: any) => t.created_at?.startsWith(today)
    ).length

    const totalBounty = kkTasks.reduce(
      (sum: number, t: any) => sum + (t.bounty_usd || 0),
      0
    )

    // Agent activity from task data
    const agentActivity: Record<string, { tasks: number; earned: number }> = {}
    for (const task of kkTasks) {
      const wallet = task.agent_wallet || 'unknown'
      if (!agentActivity[wallet]) {
        agentActivity[wallet] = { tasks: 0, earned: 0 }
      }
      agentActivity[wallet].tasks++
      agentActivity[wallet].earned += task.bounty_usd || 0
    }

    const topAgents = Object.entries(agentActivity)
      .map(([name, data]) => ({
        name: name.slice(0, 8) + '...',
        tasks: data.tasks,
        earned: data.earned,
      }))
      .sort((a, b) => b.tasks - a.tasks)
      .slice(0, 5)

    const recentTasks = kkTasks.slice(0, 5).map((t: any) => ({
      id: t.id || '',
      title: t.title || '',
      bounty: t.bounty_usd || 0,
      status: t.status || 'unknown',
      created: t.created_at || '',
    }))

    return {
      activeAgents: Object.keys(agentActivity).length,
      totalAgents: 39,
      tasksToday,
      tasksTotal: kkTasks.length,
      usdcTransacted: totalBounty,
      topAgents,
      recentTasks,
    }
  } catch {
    return DEFAULT_METRICS
  }
}

function formatUSDC(amount: number): string {
  return `$${amount.toFixed(2)}`
}

function timeAgo(dateStr: string, nowLabel = 'now'): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return nowLabel
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}

const STATUS_DOT: Record<string, string> = {
  published: 'bg-green-400',
  accepted: 'bg-blue-400',
  in_progress: 'bg-yellow-400',
  submitted: 'bg-purple-400',
  completed: 'bg-gray-400',
}

export const KKSwarmWidget = memo(function KKSwarmWidget() {
  const { t } = useTranslation()
  const [metrics, setMetrics] = useState<SwarmMetrics>(DEFAULT_METRICS)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    const data = await fetchSwarmMetrics()
    setMetrics(data)
    setLoading(false)
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [refresh])

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Karma Kadabra Swarm
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('kkSwarm.subtitle', 'Autonomous agents of Ultravioleta DAO')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              metrics.activeAgents > 0 ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
            }`}
          />
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {metrics.activeAgents}/{metrics.totalAgents} {t('kkSwarm.active', 'active')}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label={t('kkSwarm.agents', 'Agents')} value={`${metrics.activeAgents}`} sub={`${t('kkSwarm.of', 'of')} ${metrics.totalAgents}`} />
        <StatCard label={t('kkSwarm.tasksToday', 'Tasks Today')} value={`${metrics.tasksToday}`} sub={`${metrics.tasksTotal} total`} />
        <StatCard label="USDC" value={formatUSDC(metrics.usdcTransacted)} sub={t('kkSwarm.totalTransacted', 'total transacted')} />
        <StatCard label={t('kkSwarm.status', 'Status')} value={loading ? '...' : t('kkSwarm.activeStatus', 'Active')} sub={t('kkSwarm.swarmStatus', 'swarm status')} />
      </div>

      {/* Two columns: Leaderboard + Recent */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top Agents */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('kkSwarm.topAgents', 'Top Agents')}
          </h4>
          {metrics.topAgents.length === 0 ? (
            <p className="text-xs text-gray-400">{t('kkSwarm.noRecentActivity', 'No recent activity')}</p>
          ) : (
            <div className="space-y-1">
              {metrics.topAgents.map((agent, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <span className="text-gray-600 dark:text-gray-400 font-mono text-xs">
                    {agent.name}
                  </span>
                  <span className="text-gray-900 dark:text-white">
                    {agent.tasks} {t('kkSwarm.tasks', 'tasks')} / {formatUSDC(agent.earned)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Tasks */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('kkSwarm.recentTasks', 'Recent Tasks')}
          </h4>
          {metrics.recentTasks.length === 0 ? (
            <p className="text-xs text-gray-400">{t('kkSwarm.noRecentTasks', 'No recent KK tasks')}</p>
          ) : (
            <div className="space-y-1">
              {metrics.recentTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                        STATUS_DOT[task.status] || 'bg-gray-400'
                      }`}
                    />
                    <span className="truncate text-gray-600 dark:text-gray-400 text-xs">
                      {task.title.replace('[KK Data] ', '').replace('[KK] ', '')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-gray-900 dark:text-white text-xs">
                      {formatUSDC(task.bounty)}
                    </span>
                    <span className="text-gray-400 text-xs">
                      {timeAgo(task.created, t('common.now', 'now'))}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
})

function StatCard({
  label,
  value,
  sub,
}: {
  label: string
  value: string
  sub: string
}) {
  return (
    <div className="text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
      <p className="text-xl font-bold text-gray-900 dark:text-white">{value}</p>
      <p className="text-xs text-gray-400 dark:text-gray-500">{sub}</p>
    </div>
  )
}
