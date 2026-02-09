/**
 * WorkerDashboard - Dashboard principal para ejecutores (trabajadores humanos)
 *
 * Incluye:
 * - Tareas disponibles cercanas o que coinciden con habilidades
 * - Mis tareas activas en progreso
 * - Vista rapida de ganancias
 * - Badge de reputacion
 * - Acciones rapidas (explorar tareas, ver ganancias, configuracion)
 * - Pronostico de ingresos basado en tasa de completacion
 */

import { useMemo } from 'react'
import type {
  Task,
  TaskCategory,
  TaskStatus,
  Executor,
} from '../types/database'

// ============================================================================
// TYPES
// ============================================================================

export interface WorkerDashboardProps {
  executor: Executor
  availableTasks: Task[]
  myActiveTasks: Task[]
  loadingTasks?: boolean
  onTaskClick: (task: Task) => void
  onBrowseTasks: () => void
  onViewEarnings: () => void
  onViewSettings: () => void
  onWithdraw?: () => void
}

interface EarningsQuickViewData {
  availableBalance: number
  pendingEarnings: number
  thisWeek: number
  completedThisWeek: number
}

interface IncomeForecastData {
  projectedMonthly: number
  avgTaskValue: number
  completionRate: number
  tasksPerWeek: number
}

// ============================================================================
// CONSTANTS
// ============================================================================

const CATEGORY_LABELS: Record<TaskCategory, string> = {
  physical_presence: 'Presencia Fisica',
  knowledge_access: 'Acceso a Conocimiento',
  human_authority: 'Autoridad Humana',
  simple_action: 'Accion Simple',
  digital_physical: 'Digital-Fisico',
}

const CATEGORY_ICONS: Record<TaskCategory, string> = {
  physical_presence: '📍',
  knowledge_access: '📚',
  human_authority: '📋',
  simple_action: '✋',
  digital_physical: '🔗',
}

const STATUS_COLORS: Record<TaskStatus, string> = {
  published: 'bg-green-100 text-green-800',
  accepted: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  submitted: 'bg-purple-100 text-purple-800',
  verifying: 'bg-indigo-100 text-indigo-800',
  completed: 'bg-gray-100 text-gray-800',
  disputed: 'bg-red-100 text-red-800',
  expired: 'bg-gray-100 text-gray-500',
  cancelled: 'bg-gray-100 text-gray-400',
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  published: 'Disponible',
  accepted: 'Aceptada',
  in_progress: 'En Progreso',
  submitted: 'Enviada',
  verifying: 'Verificando',
  completed: 'Completada',
  disputed: 'En Disputa',
  expired: 'Expirada',
  cancelled: 'Cancelada',
}

// ============================================================================
// UTILITIES
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatDeadline(deadline: string): string {
  const date = new Date(deadline)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffMs < 0) return 'Expirada'
  if (diffHours < 1) return 'Menos de 1 hora'
  if (diffHours < 24) return `${diffHours} horas`
  if (diffDays === 1) return '1 dia'
  return `${diffDays} dias`
}

function getReputationTier(score: number): {
  name: string
  color: string
  bgColor: string
  icon: string
} {
  if (score >= 90)
    return {
      name: 'Experto',
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      icon: '💎',
    }
  if (score >= 75)
    return {
      name: 'Confiable',
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      icon: '🌟',
    }
  if (score >= 60)
    return {
      name: 'Fiable',
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      icon: '✓',
    }
  if (score >= 40)
    return {
      name: 'Estandar',
      color: 'text-gray-600',
      bgColor: 'bg-gray-100',
      icon: '○',
    }
  return {
    name: 'Nuevo',
    color: 'text-amber-600',
    bgColor: 'bg-amber-100',
    icon: '🌱',
  }
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/**
 * ReputationBadge - Muestra el nivel de reputacion del trabajador
 */
function ReputationBadge({ executor }: { executor: Executor }) {
  const tier = getReputationTier(executor.reputation_score)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-4">
        {/* Circular progress */}
        <div className="relative w-16 h-16 flex-shrink-0">
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="32"
              cy="32"
              r="28"
              stroke="currentColor"
              strokeWidth="6"
              fill="none"
              className="text-gray-100"
            />
            <circle
              cx="32"
              cy="32"
              r="28"
              stroke="currentColor"
              strokeWidth="6"
              fill="none"
              strokeDasharray={`${(executor.reputation_score / 100) * 176} 176`}
              strokeLinecap="round"
              className={
                executor.reputation_score >= 75
                  ? 'text-green-500'
                  : executor.reputation_score >= 50
                    ? 'text-blue-500'
                    : executor.reputation_score >= 25
                      ? 'text-amber-500'
                      : 'text-red-500'
              }
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-bold text-gray-900">
              {executor.reputation_score}
            </span>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{tier.icon}</span>
            <span className={`font-semibold ${tier.color}`}>{tier.name}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-500">Completadas:</span>{' '}
              <span className="font-medium text-gray-900">
                {executor.tasks_completed}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Disputas:</span>{' '}
              <span
                className={`font-medium ${executor.tasks_disputed > 0 ? 'text-red-600' : 'text-gray-900'}`}
              >
                {executor.tasks_disputed}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * EarningsQuickView - Vista rapida de ganancias
 */
function EarningsQuickView({
  data,
  onViewDetails,
  onWithdraw,
}: {
  data: EarningsQuickViewData
  onViewDetails: () => void
  onWithdraw?: () => void
}) {
  return (
    <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl shadow-lg p-5 text-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-green-100 text-sm font-medium">Mis Ganancias</h3>
        <div className="flex items-center gap-1 text-green-200">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-xs">USDC</span>
        </div>
      </div>

      {/* Balance */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold">
            {formatCurrency(data.availableBalance)}
          </span>
          {data.pendingEarnings > 0 && (
            <span className="text-green-200 text-sm">
              +{formatCurrency(data.pendingEarnings)} pendiente
            </span>
          )}
        </div>
      </div>

      {/* Weekly stats */}
      <div className="flex items-center gap-4 mb-4 py-3 border-t border-green-500/30">
        <div className="flex-1">
          <div className="text-green-200 text-xs mb-0.5">Esta semana</div>
          <div className="text-lg font-semibold">
            {formatCurrency(data.thisWeek)}
          </div>
        </div>
        <div className="flex-1">
          <div className="text-green-200 text-xs mb-0.5">Tareas completadas</div>
          <div className="text-lg font-semibold">{data.completedThisWeek}</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onViewDetails}
          className="flex-1 py-2.5 bg-white/20 text-white font-medium rounded-lg hover:bg-white/30 transition-colors text-sm"
        >
          Ver Detalles
        </button>
        {onWithdraw && (
          <button
            onClick={onWithdraw}
            disabled={data.availableBalance <= 0}
            className={`flex-1 py-2.5 font-medium rounded-lg text-sm transition-colors ${
              data.availableBalance > 0
                ? 'bg-white text-green-600 hover:bg-green-50'
                : 'bg-white/20 text-green-200 cursor-not-allowed'
            }`}
          >
            Retirar
          </button>
        )}
      </div>
    </div>
  )
}

/**
 * IncomeForecast - Pronostico de ingresos
 */
function IncomeForecast({ data }: { data: IncomeForecastData }) {
  const rateColor =
    data.completionRate >= 80
      ? 'text-green-600'
      : data.completionRate >= 60
        ? 'text-blue-600'
        : data.completionRate >= 40
          ? 'text-amber-600'
          : 'text-red-600'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">
        Pronostico de Ingresos
      </h3>

      {/* Projected monthly */}
      <div className="text-center mb-4 pb-4 border-b border-gray-100">
        <div className="text-gray-500 text-xs mb-1">Proyeccion mensual</div>
        <div className="text-3xl font-bold text-gray-900">
          {formatCurrency(data.projectedMonthly)}
        </div>
        <div className="text-xs text-gray-400 mt-1">
          Basado en tu ritmo actual
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-1">Valor promedio</div>
          <div className="text-sm font-semibold text-gray-900">
            {formatCurrency(data.avgTaskValue)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-1">Tareas/semana</div>
          <div className="text-sm font-semibold text-gray-900">
            {data.tasksPerWeek.toFixed(1)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-1">Tasa completacion</div>
          <div className={`text-sm font-semibold ${rateColor}`}>
            {data.completionRate.toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Improvement tip */}
      {data.completionRate < 80 && (
        <div className="mt-4 p-3 bg-amber-50 rounded-lg">
          <div className="flex items-start gap-2">
            <svg
              className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-xs text-amber-800">
              <span className="font-medium">Consejo:</span> Mejorar tu tasa de
              completacion aumentara tus ingresos proyectados y tu reputacion.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * QuickActions - Acciones rapidas para el trabajador
 */
function QuickActions({
  onBrowseTasks,
  onViewEarnings,
  onViewSettings,
}: {
  onBrowseTasks: () => void
  onViewEarnings: () => void
  onViewSettings: () => void
}) {
  const actions = [
    {
      label: 'Buscar Tareas',
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      ),
      color: 'bg-blue-50 text-blue-600 hover:bg-blue-100',
      onClick: onBrowseTasks,
    },
    {
      label: 'Ganancias',
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      color: 'bg-green-50 text-green-600 hover:bg-green-100',
      onClick: onViewEarnings,
    },
    {
      label: 'Configuracion',
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      ),
      color: 'bg-gray-50 text-gray-600 hover:bg-gray-100',
      onClick: onViewSettings,
    },
  ]

  return (
    <div className="grid grid-cols-3 gap-3">
      {actions.map((action) => (
        <button
          key={action.label}
          onClick={action.onClick}
          className={`p-4 rounded-xl flex flex-col items-center gap-2 transition-colors ${action.color}`}
        >
          {action.icon}
          <span className="text-xs font-medium">{action.label}</span>
        </button>
      ))}
    </div>
  )
}

/**
 * CompactTaskCard - Tarjeta compacta de tarea para el dashboard
 */
function CompactTaskCard({
  task,
  onClick,
  showStatus = false,
}: {
  task: Task
  onClick: () => void
  showStatus?: boolean
}) {
  const isExpiringSoon =
    new Date(task.deadline).getTime() - Date.now() < 24 * 60 * 60 * 1000

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-lg border border-gray-200 p-3 hover:border-gray-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start gap-3">
        {/* Category icon */}
        <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
          <span className="text-lg">{CATEGORY_ICONS[task.category]}</span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className="font-medium text-gray-900 text-sm line-clamp-1">
              {task.title}
            </h4>
            <span className="text-sm font-semibold text-green-600 flex-shrink-0">
              {formatCurrency(task.bounty_usd)}
            </span>
          </div>

          <div className="flex items-center gap-2 mt-1">
            {showStatus ? (
              <span
                className={`px-1.5 py-0.5 text-xs font-medium rounded ${STATUS_COLORS[task.status]}`}
              >
                {STATUS_LABELS[task.status]}
              </span>
            ) : (
              <span className="text-xs text-gray-500">
                {CATEGORY_LABELS[task.category]}
              </span>
            )}

            <span
              className={`text-xs ${isExpiringSoon ? 'text-orange-600' : 'text-gray-400'}`}
            >
              {formatDeadline(task.deadline)}
            </span>
          </div>

          {task.location_hint && (
            <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="truncate">{task.location_hint}</span>
            </div>
          )}
        </div>
      </div>
    </button>
  )
}

/**
 * TaskSection - Seccion de tareas con titulo y lista
 */
function TaskSection({
  title,
  tasks,
  loading,
  emptyMessage,
  emptyIcon,
  showStatus = false,
  onTaskClick,
  onViewAll,
  maxItems = 3,
}: {
  title: string
  tasks: Task[]
  loading?: boolean
  emptyMessage: string
  emptyIcon: React.ReactNode
  showStatus?: boolean
  onTaskClick: (task: Task) => void
  onViewAll?: () => void
  maxItems?: number
}) {
  const displayedTasks = tasks.slice(0, maxItems)
  const hasMore = tasks.length > maxItems

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        {tasks.length > 0 && (
          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">
            {tasks.length}
          </span>
        )}
      </div>

      {/* Content */}
      {tasks.length === 0 ? (
        <div className="p-6 text-center">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            {emptyIcon}
          </div>
          <p className="text-gray-500 text-sm">{emptyMessage}</p>
        </div>
      ) : (
        <>
          <div className="p-3 space-y-2">
            {displayedTasks.map((task) => (
              <CompactTaskCard
                key={task.id}
                task={task}
                onClick={() => onTaskClick(task)}
                showStatus={showStatus}
              />
            ))}
          </div>

          {/* View all button */}
          {hasMore && onViewAll && (
            <div className="px-4 py-3 border-t border-gray-100">
              <button
                onClick={onViewAll}
                className="w-full py-2 text-blue-600 hover:text-blue-700 text-sm font-medium transition-colors"
              >
                Ver todas ({tasks.length})
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function WorkerDashboard({
  executor,
  availableTasks,
  myActiveTasks,
  loadingTasks = false,
  onTaskClick,
  onBrowseTasks,
  onViewEarnings,
  onViewSettings,
  onWithdraw,
}: WorkerDashboardProps) {
  // Calculate mock earnings data (in production, fetch from API)
  const earningsData = useMemo<EarningsQuickViewData>(() => {
    // Mock data - replace with actual API data
    const completedTasks = myActiveTasks.filter(
      (t) => t.status === 'completed'
    ).length
    const pendingTasks = myActiveTasks.filter((t) =>
      ['submitted', 'verifying'].includes(t.status)
    )
    const pendingEarnings = pendingTasks.reduce(
      (sum, t) => sum + t.bounty_usd,
      0
    )

    return {
      availableBalance: executor.tasks_completed * 12.5, // Mock calculation
      pendingEarnings,
      thisWeek: completedTasks * 15, // Mock calculation
      completedThisWeek: completedTasks,
    }
  }, [executor.tasks_completed, myActiveTasks])

  // Calculate forecast data
  const forecastData = useMemo<IncomeForecastData>(() => {
    const totalTasks = executor.tasks_completed + executor.tasks_disputed
    const completionRate =
      totalTasks > 0 ? (executor.tasks_completed / totalTasks) * 100 : 0

    // Calculate average task value from available tasks
    const avgValue =
      availableTasks.length > 0
        ? availableTasks.reduce((sum, t) => sum + t.bounty_usd, 0) /
          availableTasks.length
        : 15

    // Estimate tasks per week (mock - would come from historical data)
    const tasksPerWeek = Math.max(1, executor.tasks_completed / 4)

    // Project monthly income
    const projectedMonthly = tasksPerWeek * 4.33 * avgValue * (completionRate / 100)

    return {
      projectedMonthly,
      avgTaskValue: avgValue,
      completionRate,
      tasksPerWeek,
    }
  }, [executor, availableTasks])

  // Filter active tasks (in progress, accepted, submitted)
  const activeTasks = useMemo(
    () =>
      myActiveTasks.filter((t) =>
        ['accepted', 'in_progress', 'submitted', 'verifying'].includes(t.status)
      ),
    [myActiveTasks]
  )

  // Filter available tasks matching worker's skills/location
  // For now, just show first few - in production, apply filters
  const recommendedTasks = useMemo(() => {
    return availableTasks
      .filter((t) => t.min_reputation <= executor.reputation_score)
      .slice(0, 5)
  }, [availableTasks, executor.reputation_score])

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            Hola, {executor.display_name || 'Trabajador'}!
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {activeTasks.length > 0
              ? `Tienes ${activeTasks.length} tarea${activeTasks.length !== 1 ? 's' : ''} activa${activeTasks.length !== 1 ? 's' : ''}`
              : 'Listo para trabajar?'}
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <QuickActions
        onBrowseTasks={onBrowseTasks}
        onViewEarnings={onViewEarnings}
        onViewSettings={onViewSettings}
      />

      {/* Earnings Quick View */}
      <EarningsQuickView
        data={earningsData}
        onViewDetails={onViewEarnings}
        onWithdraw={onWithdraw}
      />

      {/* My Active Tasks */}
      <TaskSection
        title="Mis Tareas Activas"
        tasks={activeTasks}
        loading={loadingTasks}
        emptyMessage="No tienes tareas en progreso"
        emptyIcon={
          <svg
            className="w-6 h-6 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
        }
        showStatus={true}
        onTaskClick={onTaskClick}
      />

      {/* Available Tasks */}
      <TaskSection
        title="Tareas Disponibles"
        tasks={recommendedTasks}
        loading={loadingTasks}
        emptyMessage="No hay tareas disponibles en tu zona"
        emptyIcon={
          <svg
            className="w-6 h-6 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        }
        onTaskClick={onTaskClick}
        onViewAll={onBrowseTasks}
      />

      {/* Reputation Badge */}
      <ReputationBadge executor={executor} />

      {/* Income Forecast */}
      <IncomeForecast data={forecastData} />

      {/* New worker tips */}
      {executor.tasks_completed < 5 && (
        <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
              <svg
                className="w-5 h-5 text-blue-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <h4 className="font-semibold text-blue-900 mb-1">
                Consejos para nuevos trabajadores
              </h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>
                  - Completa tu perfil para acceder a mas tareas
                </li>
                <li>
                  - Comienza con tareas simples para construir tu reputacion
                </li>
                <li>
                  - Envia evidencias claras y completas
                </li>
                <li>
                  - Responde rapido a las tareas urgentes
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default WorkerDashboard
