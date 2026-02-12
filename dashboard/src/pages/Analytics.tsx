/**
 * Analytics Page (NOW-036)
 *
 * Platform-wide analytics and metrics dashboard for Execution Market.
 * Displays:
 * - GMV (Gross Merchandise Value) over time
 * - Task completion rates
 * - Regional statistics
 * - Worker retention metrics
 * - Revenue breakdown (fees collected)
 */

import { useState, useEffect, useMemo } from 'react'
import {
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

interface GMVDataPoint {
  date: string
  amount: number
  tasks: number
}

interface RegionData {
  region: string
  count: number
  gmv: number
  avgBounty: number
}

interface RetentionData {
  month: string
  retained: number
  churned: number
  newWorkers: number
  retentionRate: number
}

interface CategoryBreakdown {
  category: string
  count: number
  revenue: number
  color: string
}

interface AnalyticsData {
  gmv: GMVDataPoint[]
  totalGMV: number
  gmvGrowth: number
  completionRate: number
  avgCompletionTime: number
  totalTasks: number
  completedTasks: number
  tasksByRegion: RegionData[]
  workerRetention: RetentionData[]
  categoryBreakdown: CategoryBreakdown[]
  feeRevenue: number
  feeRevenueGrowth: number
  activeWorkers: number
  activeAgents: number
  avgTaskValue: number
}

interface AnalyticsProps {
  onBack?: () => void
}

// ============================================================================
// Constants
// ============================================================================

const COLORS = {
  primary: '#404040',
  secondary: '#3f3f46',
  tertiary: '#52525b',
  quaternary: '#71717a',
  danger: '#1f1f1f',
  muted: '#71717a',
}

const CATEGORY_COLORS: Record<string, string> = {
  physical_presence: '#404040',
  knowledge_access: '#3f3f46',
  human_authority: '#52525b',
  simple_action: '#71717a',
  digital_physical: '#5f5f5f',
}

const TIME_RANGES = [
  { key: '7d', label: '7 dias' },
  { key: '30d', label: '30 dias' },
  { key: '90d', label: '90 dias' },
  { key: '1y', label: '1 ano' },
] as const

type TimeRange = (typeof TIME_RANGES)[number]['key']

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

function formatCompactNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`
}

function formatHours(hours: number): string {
  if (hours < 1) {
    return `${Math.round(hours * 60)} min`
  }
  return `${hours.toFixed(1)}h`
}

// ============================================================================
// Mock Data Generator
// ============================================================================

function generateMockData(timeRange: TimeRange): AnalyticsData {
  const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365
  const now = new Date()

  // Generate GMV data
  const gmv: GMVDataPoint[] = []
  let totalGMV = 0
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    const baseAmount = 500 + Math.random() * 1500
    const seasonality = 1 + 0.3 * Math.sin((i / 7) * Math.PI)
    const trend = 1 + (days - i) * 0.002
    const amount = Math.round(baseAmount * seasonality * trend)
    const tasks = Math.round(amount / (15 + Math.random() * 10))

    gmv.push({
      date: date.toISOString().split('T')[0],
      amount,
      tasks,
    })
    totalGMV += amount
  }

  // Calculate GMV growth (compare last half to first half)
  const midpoint = Math.floor(gmv.length / 2)
  const firstHalfGMV = gmv.slice(0, midpoint).reduce((sum, d) => sum + d.amount, 0)
  const secondHalfGMV = gmv.slice(midpoint).reduce((sum, d) => sum + d.amount, 0)
  const gmvGrowth = firstHalfGMV > 0 ? ((secondHalfGMV - firstHalfGMV) / firstHalfGMV) * 100 : 0

  // Task completion stats
  const totalTasks = gmv.reduce((sum, d) => sum + d.tasks, 0)
  const completedTasks = Math.round(totalTasks * (0.78 + Math.random() * 0.12))
  const completionRate = (completedTasks / totalTasks) * 100

  // Regional data (Mexico-focused)
  const tasksByRegion: RegionData[] = [
    { region: 'CDMX', count: Math.round(totalTasks * 0.35), gmv: Math.round(totalGMV * 0.38), avgBounty: 0 },
    { region: 'Guadalajara', count: Math.round(totalTasks * 0.18), gmv: Math.round(totalGMV * 0.17), avgBounty: 0 },
    { region: 'Monterrey', count: Math.round(totalTasks * 0.15), gmv: Math.round(totalGMV * 0.16), avgBounty: 0 },
    { region: 'Puebla', count: Math.round(totalTasks * 0.10), gmv: Math.round(totalGMV * 0.09), avgBounty: 0 },
    { region: 'Tijuana', count: Math.round(totalTasks * 0.08), gmv: Math.round(totalGMV * 0.08), avgBounty: 0 },
    { region: 'Otros', count: Math.round(totalTasks * 0.14), gmv: Math.round(totalGMV * 0.12), avgBounty: 0 },
  ].map((r) => ({ ...r, avgBounty: r.count > 0 ? r.gmv / r.count : 0 }))

  // Worker retention data (monthly)
  const workerRetention: RetentionData[] = []
  const months = ['Ago', 'Sep', 'Oct', 'Nov', 'Dic', 'Ene']
  let baseWorkers = 150
  for (const month of months) {
    const newWorkers = Math.round(30 + Math.random() * 40)
    const churned = Math.round(baseWorkers * (0.08 + Math.random() * 0.07))
    const retained = baseWorkers - churned + newWorkers
    const retentionRate = ((baseWorkers - churned) / baseWorkers) * 100

    workerRetention.push({
      month,
      retained,
      churned,
      newWorkers,
      retentionRate,
    })
    baseWorkers = retained
  }

  // Category breakdown
  const categoryBreakdown: CategoryBreakdown[] = [
    { category: 'Presencia Fisica', count: Math.round(totalTasks * 0.32), revenue: 0, color: CATEGORY_COLORS.physical_presence },
    { category: 'Acceso a Conocimiento', count: Math.round(totalTasks * 0.25), revenue: 0, color: CATEGORY_COLORS.knowledge_access },
    { category: 'Autoridad Humana', count: Math.round(totalTasks * 0.18), revenue: 0, color: CATEGORY_COLORS.human_authority },
    { category: 'Accion Simple', count: Math.round(totalTasks * 0.15), revenue: 0, color: CATEGORY_COLORS.simple_action },
    { category: 'Digital-Fisico', count: Math.round(totalTasks * 0.10), revenue: 0, color: CATEGORY_COLORS.digital_physical },
  ].map((c, i) => ({
    ...c,
    revenue: Math.round(totalGMV * [0.35, 0.22, 0.20, 0.13, 0.10][i]),
  }))

  // Fee revenue (13% platform fee)
  const feeRevenue = Math.round(totalGMV * 0.13)
  const feeRevenueGrowth = gmvGrowth // Same growth rate as GMV

  return {
    gmv,
    totalGMV,
    gmvGrowth,
    completionRate,
    avgCompletionTime: 3.2 + Math.random() * 2,
    totalTasks,
    completedTasks,
    tasksByRegion,
    workerRetention,
    categoryBreakdown,
    feeRevenue,
    feeRevenueGrowth,
    activeWorkers: workerRetention[workerRetention.length - 1]?.retained || 0,
    activeAgents: Math.round(25 + Math.random() * 15),
    avgTaskValue: totalGMV / totalTasks,
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
  color = 'blue',
}: {
  title: string
  value: string | number
  subValue?: string
  change?: { value: number; isPositive: boolean }
  icon: React.ReactNode
  color?: 'blue' | 'green' | 'purple' | 'amber' | 'red'
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
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
              <span className="text-gray-400 font-normal">vs periodo anterior</span>
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

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: unknown[]; label?: string }) {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
      <p className="text-sm font-medium text-gray-900 mb-2">{label}</p>
      {(payload as Array<{ name: string; value: number; color: string }>).map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium text-gray-900">
            {typeof entry.value === 'number' && entry.name.toLowerCase().includes('gmv')
              ? formatCurrency(entry.value)
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function Analytics({ onBack }: AnalyticsProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<AnalyticsData | null>(null)

  // Load data when time range changes
  useEffect(() => {
    setLoading(true)
    // Simulate API call
    const timer = setTimeout(() => {
      setData(generateMockData(timeRange))
      setLoading(false)
    }, 500)
    return () => clearTimeout(timer)
  }, [timeRange])

  // Format GMV data for chart
  const gmvChartData = useMemo(() => {
    if (!data) return []
    return data.gmv.map((d) => ({
      date: new Date(d.date).toLocaleDateString('es-MX', { month: 'short', day: 'numeric' }),
      GMV: d.amount,
      Tareas: d.tasks,
    }))
  }, [data])

  // Loading state
  if (loading || !data) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div className="h-8 bg-gray-200 rounded w-48 animate-pulse" />
          <div className="h-10 bg-gray-200 rounded w-64 animate-pulse" />
        </div>

        {/* Stats skeleton */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="h-4 bg-gray-200 rounded w-20 animate-pulse" />
              <div className="h-8 bg-gray-200 rounded w-24 mt-2 animate-pulse" />
            </div>
          ))}
        </div>

        {/* Chart skeleton */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 h-80 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* -------------------------------------------------------------------- */}
      {/* Header */}
      {/* -------------------------------------------------------------------- */}
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
            <p className="text-sm text-gray-500">Metricas de la plataforma</p>
          </div>
        </div>

        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {/* -------------------------------------------------------------------- */}
      {/* Key Metrics */}
      {/* -------------------------------------------------------------------- */}
      <section>
        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">Metricas Clave</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="GMV Total"
            value={formatCurrency(data.totalGMV)}
            subValue={`${formatCompactNumber(data.totalTasks)} tareas`}
            change={{ value: data.gmvGrowth, isPositive: data.gmvGrowth > 0 }}
            color="green"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            }
          />

          <StatCard
            title="Tasa de Completacion"
            value={formatPercentage(data.completionRate)}
            subValue={`${data.completedTasks} de ${data.totalTasks}`}
            color="blue"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />

          <StatCard
            title="Revenue (Fees)"
            value={formatCurrency(data.feeRevenue)}
            subValue="13% platform fee"
            change={{ value: data.feeRevenueGrowth, isPositive: data.feeRevenueGrowth > 0 }}
            color="purple"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
            }
          />

          <StatCard
            title="Tiempo Promedio"
            value={formatHours(data.avgCompletionTime)}
            subValue="por tarea completada"
            color="amber"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
        </div>
      </section>

      {/* -------------------------------------------------------------------- */}
      {/* GMV Chart */}
      {/* -------------------------------------------------------------------- */}
      <ChartCard title="GMV a lo largo del tiempo" subtitle="Valor bruto de mercado y numero de tareas">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={gmvChartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorGMV" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.secondary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.secondary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12 }}
                stroke="#a1a1aa"
                tickLine={false}
                tickFormatter={(value) => `$${formatCompactNumber(value)}`}
              />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="GMV"
                stroke={COLORS.secondary}
                fillOpacity={1}
                fill="url(#colorGMV)"
                strokeWidth={2}
              />
              <Line yAxisId="right" type="monotone" dataKey="Tareas" stroke={COLORS.primary} strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* -------------------------------------------------------------------- */}
      {/* Regional Stats & Category Breakdown */}
      {/* -------------------------------------------------------------------- */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Regional Statistics */}
        <ChartCard title="Estadisticas por Region" subtitle="Distribucion geografica de tareas">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.tasksByRegion} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
                <YAxis dataKey="region" type="category" tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} width={80} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null
                    const regionData = payload[0].payload as RegionData
                    return (
                      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                        <p className="font-medium text-gray-900 mb-2">{regionData.region}</p>
                        <div className="space-y-1 text-sm">
                          <p className="text-gray-600">
                            Tareas: <span className="font-medium text-gray-900">{regionData.count}</span>
                          </p>
                          <p className="text-gray-600">
                            GMV: <span className="font-medium text-gray-900">{formatCurrency(regionData.gmv)}</span>
                          </p>
                          <p className="text-gray-600">
                            Promedio: <span className="font-medium text-gray-900">{formatCurrency(regionData.avgBounty)}</span>
                          </p>
                        </div>
                      </div>
                    )
                  }}
                />
                <Bar dataKey="count" fill={COLORS.primary} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Category Breakdown */}
        <ChartCard title="Tareas por Categoria" subtitle="Distribucion por tipo de tarea">
          <div className="h-64 flex items-center">
            <ResponsiveContainer width="50%" height="100%">
              <PieChart>
                <Pie
                  data={data.categoryBreakdown}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="count"
                >
                  {data.categoryBreakdown.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null
                    const catData = payload[0].payload as CategoryBreakdown
                    return (
                      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                        <p className="font-medium text-gray-900 mb-1">{catData.category}</p>
                        <p className="text-sm text-gray-600">
                          {catData.count} tareas ({formatCurrency(catData.revenue)})
                        </p>
                      </div>
                    )
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-2">
              {data.categoryBreakdown.map((cat) => (
                <div key={cat.category} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
                  <span className="text-sm text-gray-600 flex-1 truncate">{cat.category}</span>
                  <span className="text-sm font-medium text-gray-900">{cat.count}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>

      {/* -------------------------------------------------------------------- */}
      {/* Worker Retention */}
      {/* -------------------------------------------------------------------- */}
      <ChartCard
        title="Retencion de Trabajadores"
        subtitle="Trabajadores activos, nuevos y perdidos por mes"
        action={
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span className="text-gray-600">Retenidos</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-gray-600">Nuevos</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-gray-600">Perdidos</span>
            </div>
          </div>
        }
      >
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.workerRetention} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} stroke="#a1a1aa" tickLine={false} />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload || !payload.length) return null
                  const retData = payload[0].payload as RetentionData
                  return (
                    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                      <p className="font-medium text-gray-900 mb-2">{label}</p>
                      <div className="space-y-1 text-sm">
                        <p className="text-gray-600">
                          Retenidos: <span className="font-medium text-blue-600">{retData.retained}</span>
                        </p>
                        <p className="text-gray-600">
                          Nuevos: <span className="font-medium text-green-600">+{retData.newWorkers}</span>
                        </p>
                        <p className="text-gray-600">
                          Perdidos: <span className="font-medium text-red-600">-{retData.churned}</span>
                        </p>
                        <p className="text-gray-600 pt-1 border-t border-gray-100">
                          Tasa: <span className="font-medium text-gray-900">{formatPercentage(retData.retentionRate)}</span>
                        </p>
                      </div>
                    </div>
                  )
                }}
              />
              <Bar dataKey="retained" stackId="a" fill={COLORS.primary} radius={[0, 0, 0, 0]} />
              <Bar dataKey="newWorkers" stackId="a" fill={COLORS.secondary} radius={[0, 0, 0, 0]} />
              <Bar dataKey="churned" fill={COLORS.danger} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* -------------------------------------------------------------------- */}
      {/* Secondary Metrics */}
      {/* -------------------------------------------------------------------- */}
      <section>
        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">Metricas Secundarias</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Trabajadores Activos"
            value={data.activeWorkers}
            subValue="ultimo mes"
            color="blue"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
            }
          />

          <StatCard
            title="Agentes Activos"
            value={data.activeAgents}
            subValue="publicando tareas"
            color="purple"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            }
          />

          <StatCard
            title="Valor Promedio"
            value={formatCurrency(data.avgTaskValue)}
            subValue="por tarea"
            color="green"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
            }
          />

          <StatCard
            title="Retencion"
            value={formatPercentage(data.workerRetention[data.workerRetention.length - 1]?.retentionRate || 0)}
            subValue="ultimo mes"
            color="amber"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            }
          />
        </div>
      </section>

      {/* -------------------------------------------------------------------- */}
      {/* Export Button */}
      {/* -------------------------------------------------------------------- */}
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
