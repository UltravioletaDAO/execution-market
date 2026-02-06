/**
 * Agent Analytics - Analytics dashboard for AI agents
 *
 * Features:
 * - Task completion rates
 * - Average time to completion
 * - Worker performance metrics
 * - Cost analysis
 * - Time-series charts
 */

import { useState, useEffect, useMemo } from 'react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

// ============================================================================
// Types
// ============================================================================

interface AgentAnalyticsProps {
  agentId: string
  onBack?: () => void
}

interface TimeSeriesDataPoint {
  date: string
  tasks: number
  completed: number
  spent: number
  avgTime: number
}

interface WorkerPerformance {
  id: string
  name: string
  avatar?: string
  tasksCompleted: number
  avgRating: number
  avgTime: number
  totalEarned: number
  disputeRate: number
}

interface CategoryStats {
  category: string
  label: string
  count: number
  avgCost: number
  avgTime: number
  successRate: number
  color: string
}

interface AnalyticsData {
  // Summary stats
  totalTasks: number
  completedTasks: number
  completionRate: number
  totalSpent: number
  avgTaskCost: number
  avgCompletionTime: number // hours
  disputeRate: number
  activeWorkers: number

  // Time series
  timeSeries: TimeSeriesDataPoint[]

  // Worker performance
  topWorkers: WorkerPerformance[]

  // Category breakdown
  categoryStats: CategoryStats[]

  // Monthly comparison
  monthlyComparison: {
    current: number
    previous: number
    change: number
  }
}

type TimeRange = '7d' | '30d' | '90d' | '1y'

// ============================================================================
// Constants
// ============================================================================

const TIME_RANGES: { key: TimeRange; label: string }[] = [
  { key: '7d', label: '7 dias' },
  { key: '30d', label: '30 dias' },
  { key: '90d', label: '90 dias' },
  { key: '1y', label: '1 ano' },
]

const CATEGORY_COLORS = {
  physical_presence: '#404040',
  knowledge_access: '#3f3f46',
  human_authority: '#52525b',
  simple_action: '#71717a',
  digital_physical: '#5f5f5f',
}

const CATEGORY_LABELS = {
  physical_presence: 'Presencia Fisica',
  knowledge_access: 'Acceso a Conocimiento',
  human_authority: 'Autoridad Humana',
  simple_action: 'Accion Simple',
  digital_physical: 'Digital-Fisico',
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`
}

function formatHours(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)} min`
  return `${hours.toFixed(1)}h`
}

function formatCompactNumber(num: number): string {
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

// ============================================================================
// Mock Data Generator
// ============================================================================

function generateMockData(timeRange: TimeRange): AnalyticsData {
  const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365
  const now = new Date()

  // Generate time series
  const timeSeries: TimeSeriesDataPoint[] = []
  let totalTasks = 0
  let totalCompleted = 0
  let totalSpent = 0
  let totalTime = 0

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)

    const dailyTasks = Math.round(2 + Math.random() * 5)
    const dailyCompleted = Math.round(dailyTasks * (0.75 + Math.random() * 0.2))
    const dailySpent = dailyCompleted * (10 + Math.random() * 20)
    const dailyAvgTime = 2 + Math.random() * 4

    timeSeries.push({
      date: date.toISOString().split('T')[0],
      tasks: dailyTasks,
      completed: dailyCompleted,
      spent: Math.round(dailySpent),
      avgTime: dailyAvgTime,
    })

    totalTasks += dailyTasks
    totalCompleted += dailyCompleted
    totalSpent += dailySpent
    totalTime += dailyAvgTime * dailyCompleted
  }

  // Calculate stats
  const completionRate = (totalCompleted / totalTasks) * 100
  const avgTaskCost = totalSpent / totalCompleted
  const avgCompletionTime = totalTime / totalCompleted

  // Generate worker performance
  const workerNames = ['Maria Garcia', 'Carlos Lopez', 'Ana Martinez', 'Juan Perez', 'Sofia Rodriguez']
  const topWorkers: WorkerPerformance[] = workerNames.map((name, i) => ({
    id: `worker-${i}`,
    name,
    avatar: undefined,
    tasksCompleted: Math.round(10 + Math.random() * 40),
    avgRating: 3.5 + Math.random() * 1.5,
    avgTime: 2 + Math.random() * 4,
    totalEarned: Math.round(100 + Math.random() * 500),
    disputeRate: Math.random() * 10,
  })).sort((a, b) => b.tasksCompleted - a.tasksCompleted)

  // Category stats
  const categories = Object.keys(CATEGORY_COLORS) as (keyof typeof CATEGORY_COLORS)[]
  const categoryStats: CategoryStats[] = categories.map((cat) => ({
    category: cat,
    label: CATEGORY_LABELS[cat],
    count: Math.round(5 + Math.random() * 30),
    avgCost: 10 + Math.random() * 25,
    avgTime: 2 + Math.random() * 5,
    successRate: 75 + Math.random() * 20,
    color: CATEGORY_COLORS[cat],
  }))

  // Monthly comparison
  const currentMonth = totalSpent / (days / 30)
  const previousMonth = currentMonth * (0.8 + Math.random() * 0.4)
  const change = ((currentMonth - previousMonth) / previousMonth) * 100

  return {
    totalTasks,
    completedTasks: totalCompleted,
    completionRate,
    totalSpent: Math.round(totalSpent),
    avgTaskCost,
    avgCompletionTime,
    disputeRate: 2 + Math.random() * 5,
    activeWorkers: topWorkers.length,
    timeSeries,
    topWorkers,
    categoryStats,
    monthlyComparison: {
      current: Math.round(currentMonth),
      previous: Math.round(previousMonth),
      change,
    },
  }
}

// ============================================================================
// Sub-Components
// ============================================================================

function StatCard({
  title,
  value,
  subValue,
  change,
  icon,
  color = 'gray',
}: {
  title: string
  value: string | number
  subValue?: string
  change?: { value: number; isPositive: boolean }
  icon: React.ReactNode
  color?: 'blue' | 'green' | 'purple' | 'amber' | 'red' | 'gray'
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
    gray: 'bg-gray-50 text-gray-600',
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subValue && <p className="text-xs text-gray-400 mt-0.5">{subValue}</p>}
          {change && (
            <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${change.isPositive ? 'text-green-600' : 'text-red-600'}`}>
              <svg
                className={`w-3 h-3 ${change.isPositive ? '' : 'rotate-180'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
              <span>{formatPercentage(Math.abs(change.value))}</span>
              <span className="text-gray-400 font-normal">vs anterior</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
    </div>
  )
}

function ChartCard({
  title,
  subtitle,
  children,
  action,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

function TimeRangeSelector({
  value,
  onChange,
}: {
  value: TimeRange
  onChange: (range: TimeRange) => void
}) {
  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
      {TIME_RANGES.map((range) => (
        <button
          key={range.key}
          onClick={() => onChange(range.key)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            value === range.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {range.label}
        </button>
      ))}
    </div>
  )
}

function WorkerRankingTable({ workers }: { workers: WorkerPerformance[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-xs text-gray-500 border-b border-gray-100">
            <th className="text-left py-2 font-medium">#</th>
            <th className="text-left py-2 font-medium">Trabajador</th>
            <th className="text-right py-2 font-medium">Tareas</th>
            <th className="text-right py-2 font-medium">Rating</th>
            <th className="text-right py-2 font-medium">Tiempo Prom.</th>
            <th className="text-right py-2 font-medium">Ganado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {workers.map((worker, index) => (
            <tr key={worker.id} className="text-sm">
              <td className="py-3 text-gray-500">{index + 1}</td>
              <td className="py-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-blue-700 text-xs font-medium">
                      {worker.name[0].toUpperCase()}
                    </span>
                  </div>
                  <span className="text-gray-900 font-medium">{worker.name}</span>
                </div>
              </td>
              <td className="py-3 text-right text-gray-900">{worker.tasksCompleted}</td>
              <td className="py-3 text-right">
                <span className="flex items-center justify-end gap-1 text-amber-600">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {worker.avgRating.toFixed(1)}
                </span>
              </td>
              <td className="py-3 text-right text-gray-600">{formatHours(worker.avgTime)}</td>
              <td className="py-3 text-right text-green-600 font-medium">{formatCurrency(worker.totalEarned)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CategoryBreakdownChart({ data }: { data: CategoryStats[] }) {
  return (
    <div className="flex items-center gap-6">
      <div className="w-1/3">
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={70}
              paddingAngle={2}
              dataKey="count"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null
                const item = payload[0].payload as CategoryStats
                return (
                  <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                    <p className="font-medium text-gray-900">{item.label}</p>
                    <p className="text-sm text-gray-600">{item.count} tareas</p>
                  </div>
                )
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex-1 space-y-2">
        {data.map((cat) => (
          <div key={cat.category} className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-700 truncate">{cat.label}</span>
                <span className="text-sm font-medium text-gray-900">{cat.count}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                <span>{formatCurrency(cat.avgCost)} prom.</span>
                <span className="text-gray-300">|</span>
                <span>{formatPercentage(cat.successRate)} exito</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function Analytics({ agentId, onBack }: AgentAnalyticsProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<AnalyticsData | null>(null)

  // Load data
  useEffect(() => {
    setLoading(true)
    const timer = setTimeout(() => {
      setData(generateMockData(timeRange))
      setLoading(false)
    }, 500)
    return () => clearTimeout(timer)
  }, [timeRange])

  // Format time series for chart
  const chartData = useMemo(() => {
    if (!data) return []
    return data.timeSeries.map((d) => ({
      date: new Date(d.date).toLocaleDateString('es-MX', { month: 'short', day: 'numeric' }),
      Tareas: d.tasks,
      Completadas: d.completed,
      Gasto: d.spent,
    }))
  }, [data])

  // Loading state
  if (loading || !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-8 bg-gray-200 rounded w-48 animate-pulse" />
          <div className="h-10 bg-gray-200 rounded w-64 animate-pulse" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="h-4 bg-gray-200 rounded w-20 animate-pulse" />
              <div className="h-8 bg-gray-200 rounded w-24 mt-2 animate-pulse" />
            </div>
          ))}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 h-80 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {onBack && (
            <button onClick={onBack} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          <div>
            <h1 className="text-xl font-bold text-gray-900">Analytics</h1>
            <p className="text-sm text-gray-500">Rendimiento de tus tareas</p>
          </div>
        </div>

        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Tareas Completadas"
          value={data.completedTasks}
          subValue={`de ${data.totalTasks} creadas`}
          color="blue"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title="Tasa de Completacion"
          value={formatPercentage(data.completionRate)}
          subValue={`${data.disputeRate.toFixed(1)}% disputas`}
          change={{ value: 5.2, isPositive: true }}
          color="green"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          }
        />
        <StatCard
          title="Gasto Total"
          value={formatCurrency(data.totalSpent)}
          subValue={`${formatCurrency(data.avgTaskCost)} promedio`}
          change={{ value: data.monthlyComparison.change, isPositive: data.monthlyComparison.change < 0 }}
          color="purple"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title="Tiempo Promedio"
          value={formatHours(data.avgCompletionTime)}
          subValue={`${data.activeWorkers} trabajadores activos`}
          color="amber"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {/* Tasks Over Time Chart */}
      <ChartCard title="Tareas en el Tiempo" subtitle="Creadas vs completadas">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorTareas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#404040" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#404040" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorCompletadas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3f3f46" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3f3f46" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: '1px solid #e4e4e7' }}
                labelStyle={{ fontWeight: 600 }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="Tareas"
                stroke="#404040"
                fill="url(#colorTareas)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="Completadas"
                stroke="#3f3f46"
                fill="url(#colorCompletadas)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* Spending Over Time */}
      <ChartCard title="Gasto en el Tiempo" subtitle="USDC gastado por dia">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: '1px solid #e4e4e7' }}
                formatter={(value: number) => [formatCurrency(value), 'Gasto']}
              />
              <Bar dataKey="Gasto" fill="#52525b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* Two column layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <ChartCard title="Tareas por Categoria" subtitle="Distribucion y rendimiento">
          <CategoryBreakdownChart data={data.categoryStats} />
        </ChartCard>

        {/* Cost Analysis */}
        <ChartCard title="Analisis de Costos" subtitle="Costo promedio por categoria">
          <div className="space-y-3">
            {data.categoryStats.map((cat) => (
              <div key={cat.category}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
                    <span className="text-sm text-gray-700">{cat.label}</span>
                  </div>
                  <span className="text-sm font-medium text-gray-900">{formatCurrency(cat.avgCost)}</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(cat.avgCost / Math.max(...data.categoryStats.map((c) => c.avgCost))) * 100}%`,
                      backgroundColor: cat.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Worker Performance */}
      <ChartCard
        title="Top Trabajadores"
        subtitle="Ordenados por tareas completadas"
        action={
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            Ver todos
          </button>
        }
      >
        <WorkerRankingTable workers={data.topWorkers} />
      </ChartCard>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-5 text-white">
          <p className="text-blue-100 text-sm">Este mes</p>
          <p className="text-3xl font-bold mt-1">{formatCurrency(data.monthlyComparison.current)}</p>
          <p className={`text-sm mt-2 ${data.monthlyComparison.change > 0 ? 'text-red-200' : 'text-green-200'}`}>
            {data.monthlyComparison.change > 0 ? '+' : ''}{formatPercentage(data.monthlyComparison.change)} vs mes anterior
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-gray-500 text-sm">Costo por Tarea</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(data.avgTaskCost)}</p>
          <p className="text-xs text-gray-400 mt-2">Promedio general</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-gray-500 text-sm">Eficiencia</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatHours(data.avgCompletionTime)}</p>
          <p className="text-xs text-gray-400 mt-2">Tiempo promedio</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-gray-500 text-sm">Tasa de Disputas</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatPercentage(data.disputeRate)}</p>
          <p className="text-xs text-green-600 mt-2">Por debajo del promedio</p>
        </div>
      </div>

      {/* Export Button */}
      <div className="flex justify-end">
        <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Exportar Reporte
        </button>
      </div>
    </div>
  )
}

export default Analytics
