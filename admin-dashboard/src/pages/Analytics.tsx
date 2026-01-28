import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface AnalyticsProps {
  adminKey: string
}

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.chamba.ultravioletadao.xyz'

async function fetchAnalytics(adminKey: string, period: string) {
  const params = new URLSearchParams({
    admin_key: adminKey,
    period,
  })

  const response = await fetch(`${API_BASE}/api/v1/admin/analytics?${params}`)
  if (!response.ok) {
    throw new Error('Failed to fetch analytics')
  }
  return response.json()
}

async function fetchStats(adminKey: string) {
  const response = await fetch(`${API_BASE}/api/v1/admin/stats?admin_key=${adminKey}`)
  if (!response.ok) {
    throw new Error('Failed to fetch stats')
  }
  return response.json()
}

const COLORS = ['#10B981', '#F59E0B', '#6366F1', '#EC4899', '#8B5CF6', '#EF4444']

function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: string
  trend?: { value: number; label: string }
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-gray-400 text-sm">{title}</h3>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="mt-2">
        <span className="text-3xl font-bold text-white">{value}</span>
        {subtitle && (
          <span className="text-gray-400 text-sm ml-2">{subtitle}</span>
        )}
      </div>
      {trend && (
        <div className="mt-2">
          <span className={`text-sm ${trend.value >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
          </span>
        </div>
      )}
    </div>
  )
}

export default function Analytics({ adminKey }: AnalyticsProps) {
  const [period, setPeriod] = useState('30d')

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', adminKey],
    queryFn: () => fetchStats(adminKey),
    enabled: !!adminKey,
  })

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analytics', adminKey, period],
    queryFn: () => fetchAnalytics(adminKey, period),
    enabled: !!adminKey,
  })

  const isLoading = statsLoading || analyticsLoading

  if (isLoading) {
    return <div className="text-gray-400">Loading analytics...</div>
  }

  const { tasks = {}, payments = {}, users = {} } = stats || {}

  // Prepare chart data
  const tasksByStatus = Object.entries(tasks.by_status || {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: value as number,
  }))

  const timeSeriesData = analytics?.time_series || []
  const topAgents = analytics?.top_agents || []
  const topWorkers = analytics?.top_workers || []

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-white">Platform Analytics</h1>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Tasks"
          value={tasks.total || 0}
          icon="📋"
          trend={analytics?.trends?.tasks}
        />
        <StatCard
          title="Total Volume"
          value={`$${(payments.total_volume_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon="💰"
          trend={analytics?.trends?.volume}
        />
        <StatCard
          title="Fees Earned"
          value={`$${(payments.total_fees_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon="📈"
          trend={analytics?.trends?.fees}
        />
        <StatCard
          title="Active Users"
          value={(users.active_workers || 0) + (users.active_agents || 0)}
          subtitle={`${users.active_workers || 0} workers, ${users.active_agents || 0} agents`}
          icon="👥"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Tasks Over Time */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Tasks Over Time</h2>
          {timeSeriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="colorTasks" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                  labelStyle={{ color: '#9CA3AF' }}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="created"
                  name="Created"
                  stroke="#10B981"
                  fillOpacity={1}
                  fill="url(#colorTasks)"
                />
                <Area
                  type="monotone"
                  dataKey="completed"
                  name="Completed"
                  stroke="#6366F1"
                  fillOpacity={1}
                  fill="url(#colorCompleted)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-400">
              No time series data available
            </div>
          )}
        </div>

        {/* Tasks by Status */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Tasks by Status</h2>
          {tasksByStatus.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={tasksByStatus}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {tasksByStatus.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-400">
              No task data available
            </div>
          )}
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Volume Over Time */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Volume Over Time</h2>
          {timeSeriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={timeSeriesData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                  labelStyle={{ color: '#9CA3AF' }}
                  formatter={(value: number) => [`$${value.toFixed(2)}`, 'Volume']}
                />
                <Bar dataKey="volume" name="Volume" fill="#F59E0B" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-400">
              No volume data available
            </div>
          )}
        </div>

        {/* Platform Health */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Platform Health</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-3 border-b border-gray-700">
              <span className="text-gray-300">Completion Rate</span>
              <div className="flex items-center gap-3">
                <div className="w-32 h-2 bg-gray-700 rounded overflow-hidden">
                  <div
                    className="h-full bg-green-500"
                    style={{
                      width: `${tasks.total > 0 ? ((tasks.by_status?.completed || 0) / tasks.total * 100) : 0}%`
                    }}
                  />
                </div>
                <span className="text-white font-mono w-16 text-right">
                  {tasks.total > 0
                    ? `${((tasks.by_status?.completed || 0) / tasks.total * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>
            </div>
            <div className="flex justify-between items-center py-3 border-b border-gray-700">
              <span className="text-gray-300">Average Bounty</span>
              <span className="text-white font-mono">
                {tasks.total > 0 && payments.total_volume_usd
                  ? `$${(payments.total_volume_usd / tasks.total).toFixed(2)}`
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between items-center py-3 border-b border-gray-700">
              <span className="text-gray-300">Fee Rate</span>
              <span className="text-white font-mono">
                {payments.total_volume_usd > 0
                  ? `${((payments.total_fees_usd / payments.total_volume_usd) * 100).toFixed(1)}%`
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between items-center py-3 border-b border-gray-700">
              <span className="text-gray-300">Active Escrow</span>
              <span className="text-yellow-400 font-mono">
                ${(payments.active_escrow_usd || 0).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-center py-3">
              <span className="text-gray-300">Dispute Rate</span>
              <span className="text-white font-mono">
                {tasks.total > 0 && tasks.disputed !== undefined
                  ? `${((tasks.disputed / tasks.total) * 100).toFixed(1)}%`
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Users */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Agents */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Top Agents by Spend</h2>
          {topAgents.length > 0 ? (
            <div className="space-y-3">
              {topAgents.slice(0, 5).map((agent: any, index: number) => (
                <div key={agent.id} className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500 w-6">{index + 1}.</span>
                    <span className="text-gray-300 font-mono text-sm">
                      {agent.wallet_address?.slice(0, 6)}...{agent.wallet_address?.slice(-4)}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-white font-semibold">
                      ${agent.total_spent_usd?.toFixed(2)}
                    </span>
                    <span className="text-gray-500 text-sm ml-2">
                      ({agent.task_count} tasks)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400">No agent data available</p>
          )}
        </div>

        {/* Top Workers */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Top Workers by Earnings</h2>
          {topWorkers.length > 0 ? (
            <div className="space-y-3">
              {topWorkers.slice(0, 5).map((worker: any, index: number) => (
                <div key={worker.id} className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500 w-6">{index + 1}.</span>
                    <span className="text-gray-300 font-mono text-sm">
                      {worker.wallet_address?.slice(0, 6)}...{worker.wallet_address?.slice(-4)}
                    </span>
                    <span className="text-yellow-400 text-sm">
                      ⭐ {worker.reputation_score?.toFixed(0) || 'N/A'}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-green-400 font-semibold">
                      ${worker.total_earned_usd?.toFixed(2)}
                    </span>
                    <span className="text-gray-500 text-sm ml-2">
                      ({worker.task_count} tasks)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400">No worker data available</p>
          )}
        </div>
      </div>

      <div className="mt-6 text-gray-500 text-sm">
        Last updated: {stats?.generated_at ? new Date(stats.generated_at).toLocaleString() : 'N/A'}
      </div>
    </div>
  )
}
