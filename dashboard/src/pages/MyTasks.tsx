/**
 * MyTasks - Worker's Tasks Page
 *
 * Features:
 * - Tabs: Applied, In Progress, Completed
 * - Task cards with status indicators
 * - Progress tracking for in-progress tasks
 * - Quick actions for each task
 */

import { useState, useMemo } from 'react'
import type { Task, TaskStatus, TaskCategory, TaskApplication } from '../types/database'

// ============================================================================
// TYPES
// ============================================================================

export type MyTasksTab = 'applied' | 'in_progress' | 'completed'

export interface MyTasksPageProps {
  tasks: Task[]
  applications: TaskApplication[]
  loading?: boolean
  error?: Error | null
  onTaskClick: (task: Task) => void
  onRefresh?: () => void
}

// ============================================================================
// CONSTANTS
// ============================================================================

const TAB_OPTIONS: { value: MyTasksTab; label: string; statuses: TaskStatus[] }[] = [
  {
    value: 'applied',
    label: 'Solicitadas',
    statuses: ['published'], // Tasks where I've applied but not yet assigned
  },
  {
    value: 'in_progress',
    label: 'En Progreso',
    statuses: ['accepted', 'in_progress', 'submitted', 'verifying'],
  },
  {
    value: 'completed',
    label: 'Completadas',
    statuses: ['completed', 'disputed', 'expired', 'cancelled'],
  },
]

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
  published: 'Solicitada',
  accepted: 'Aceptada',
  in_progress: 'En Progreso',
  submitted: 'Enviada',
  verifying: 'Verificando',
  completed: 'Completada',
  disputed: 'En Disputa',
  expired: 'Expirada',
  cancelled: 'Cancelada',
}

const APPLICATION_STATUS_LABELS: Record<TaskApplication['status'], string> = {
  pending: 'Pendiente',
  accepted: 'Aceptada',
  rejected: 'Rechazada',
}

const APPLICATION_STATUS_COLORS: Record<TaskApplication['status'], string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}

// ============================================================================
// UTILITIES
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatDeadline(deadline: string): { text: string; urgent: boolean; expired: boolean } {
  const date = new Date(deadline)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffMs < 0) return { text: 'Expirada', urgent: false, expired: true }
  if (diffHours < 1) return { text: 'Menos de 1 hora', urgent: true, expired: false }
  if (diffHours < 6) return { text: `${diffHours} horas`, urgent: true, expired: false }
  if (diffHours < 24) return { text: `${diffHours} horas`, urgent: false, expired: false }
  if (diffDays === 1) return { text: '1 dia', urgent: false, expired: false }
  return { text: `${diffDays} dias`, urgent: false, expired: false }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function TabSelector({
  selected,
  onChange,
  counts,
}: {
  selected: MyTasksTab
  onChange: (tab: MyTasksTab) => void
  counts: Record<MyTasksTab, number>
}) {
  return (
    <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
      {TAB_OPTIONS.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-all ${
            selected === tab.value
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <span>{tab.label}</span>
          {counts[tab.value] > 0 && (
            <span
              className={`px-1.5 py-0.5 text-xs font-medium rounded-full ${
                selected === tab.value
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              {counts[tab.value]}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

function ProgressBar({ status }: { status: TaskStatus }) {
  const stages: { status: TaskStatus; label: string }[] = [
    { status: 'accepted', label: 'Aceptada' },
    { status: 'in_progress', label: 'Trabajando' },
    { status: 'submitted', label: 'Enviada' },
    { status: 'verifying', label: 'Verificando' },
    { status: 'completed', label: 'Completada' },
  ]

  const currentIndex = stages.findIndex((s) => s.status === status)
  const progress = Math.max(0, ((currentIndex + 1) / stages.length) * 100)

  return (
    <div className="space-y-2">
      {/* Progress bar */}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Stage labels */}
      <div className="flex justify-between text-xs">
        {stages.map((stage, index) => {
          const isComplete = index <= currentIndex
          const isCurrent = index === currentIndex
          return (
            <div
              key={stage.status}
              className={`flex flex-col items-center ${
                isComplete ? 'text-blue-600' : 'text-gray-400'
              }`}
            >
              <div
                className={`w-3 h-3 rounded-full mb-1 ${
                  isCurrent
                    ? 'bg-blue-600 ring-2 ring-blue-200'
                    : isComplete
                      ? 'bg-blue-600'
                      : 'bg-gray-300'
                }`}
              />
              <span className="hidden sm:inline">{stage.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function TaskCard({
  task,
  application,
  tab,
  onClick,
}: {
  task: Task
  application?: TaskApplication
  tab: MyTasksTab
  onClick: () => void
}) {
  const deadline = formatDeadline(task.deadline)

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-xl border border-gray-200 overflow-hidden hover:border-gray-300 hover:shadow-sm transition-all"
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Category icon */}
          <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-lg">{CATEGORY_ICONS[task.category]}</span>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-gray-900 line-clamp-1">{task.title}</h3>
              <span className="text-lg font-bold text-green-600 flex-shrink-0">
                {formatCurrency(task.bounty_usd)}
              </span>
            </div>

            {/* Status badges */}
            <div className="flex flex-wrap items-center gap-2 mt-2">
              {tab === 'applied' && application ? (
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full ${APPLICATION_STATUS_COLORS[application.status]}`}
                >
                  {APPLICATION_STATUS_LABELS[application.status]}
                </span>
              ) : (
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[task.status]}`}
                >
                  {STATUS_LABELS[task.status]}
                </span>
              )}

              {/* Deadline */}
              <span
                className={`flex items-center gap-1 text-xs ${
                  deadline.expired
                    ? 'text-gray-400'
                    : deadline.urgent
                      ? 'text-red-600'
                      : 'text-gray-500'
                }`}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {deadline.text}
              </span>
            </div>

            {/* Location if available */}
            {task.location_hint && (
              <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
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
      </div>

      {/* Progress bar for in-progress tasks */}
      {tab === 'in_progress' && (
        <div className="px-4 pb-4">
          <ProgressBar status={task.status} />
        </div>
      )}

      {/* Footer for completed tasks */}
      {tab === 'completed' && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {task.status === 'completed'
              ? `Completada: ${formatDate(task.completed_at || task.updated_at)}`
              : task.status === 'disputed'
                ? 'En disputa'
                : task.status === 'expired'
                  ? 'Expirada'
                  : 'Cancelada'}
          </span>
          {task.status === 'completed' && (
            <span className="text-xs font-medium text-green-600">
              +{formatCurrency(task.bounty_usd)}
            </span>
          )}
        </div>
      )}
    </button>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-gray-200 rounded-lg" />
            <div className="flex-1">
              <div className="h-5 bg-gray-200 rounded w-3/4 mb-2" />
              <div className="h-4 bg-gray-200 rounded w-1/2" />
            </div>
            <div className="w-16 h-6 bg-gray-200 rounded" />
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ tab }: { tab: MyTasksTab }) {
  const config = {
    applied: {
      icon: (
        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
          />
        </svg>
      ),
      title: 'No tienes solicitudes activas',
      description: 'Explora las tareas disponibles y aplica a las que te interesen',
    },
    in_progress: {
      icon: (
        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      title: 'No tienes tareas en progreso',
      description: 'Cuando seas aceptado en una tarea, aparecera aqui',
    },
    completed: {
      icon: (
        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      title: 'No tienes tareas completadas',
      description: 'Tu historial de tareas completadas aparecera aqui',
    },
  }

  const { icon, title, description } = config[tab]

  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
        {icon}
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
      <p className="text-gray-500">{description}</p>
    </div>
  )
}

function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">Error al cargar tareas</h3>
      <p className="text-gray-500 mb-4">{error.message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}

function SummaryStats({
  tasks,
  applications,
}: {
  tasks: Task[]
  applications: TaskApplication[]
}) {
  const stats = useMemo(() => {
    const completed = tasks.filter((t) => t.status === 'completed')
    const inProgress = tasks.filter((t) =>
      ['accepted', 'in_progress', 'submitted', 'verifying'].includes(t.status)
    )
    const totalEarned = completed.reduce((sum, t) => sum + t.bounty_usd, 0)
    const pendingEarnings = inProgress
      .filter((t) => ['submitted', 'verifying'].includes(t.status))
      .reduce((sum, t) => sum + t.bounty_usd, 0)

    return {
      completed: completed.length,
      inProgress: inProgress.length,
      pendingApplications: applications.filter((a) => a.status === 'pending').length,
      totalEarned,
      pendingEarnings,
    }
  }, [tasks, applications])

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="text-xs text-gray-500 mb-1">En progreso</div>
        <div className="text-2xl font-bold text-gray-900">{stats.inProgress}</div>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="text-xs text-gray-500 mb-1">Solicitudes</div>
        <div className="text-2xl font-bold text-gray-900">{stats.pendingApplications}</div>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="text-xs text-gray-500 mb-1">Completadas</div>
        <div className="text-2xl font-bold text-gray-900">{stats.completed}</div>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="text-xs text-gray-500 mb-1">Total ganado</div>
        <div className="text-2xl font-bold text-green-600">{formatCurrency(stats.totalEarned)}</div>
      </div>
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function MyTasks({
  tasks,
  applications,
  loading = false,
  error = null,
  onTaskClick,
  onRefresh,
}: MyTasksPageProps) {
  const [activeTab, setActiveTab] = useState<MyTasksTab>('in_progress')

  // Create a map of task applications
  const applicationsByTaskId = useMemo(() => {
    const map = new Map<string, TaskApplication>()
    applications.forEach((app) => map.set(app.task_id, app))
    return map
  }, [applications])

  // Filter tasks based on active tab
  const filteredTasks = useMemo(() => {
    const tabConfig = TAB_OPTIONS.find((t) => t.value === activeTab)!

    if (activeTab === 'applied') {
      // For applied tab, show tasks where we have pending applications
      const pendingAppTaskIds = new Set(
        applications.filter((a) => a.status === 'pending').map((a) => a.task_id)
      )
      return tasks.filter((t) => pendingAppTaskIds.has(t.id) && t.status === 'published')
    }

    return tasks.filter((t) => tabConfig.statuses.includes(t.status))
  }, [tasks, applications, activeTab])

  // Calculate tab counts
  const tabCounts = useMemo(() => {
    const pendingAppTaskIds = new Set(
      applications.filter((a) => a.status === 'pending').map((a) => a.task_id)
    )

    return {
      applied: tasks.filter((t) => pendingAppTaskIds.has(t.id) && t.status === 'published').length,
      in_progress: tasks.filter((t) =>
        ['accepted', 'in_progress', 'submitted', 'verifying'].includes(t.status)
      ).length,
      completed: tasks.filter((t) =>
        ['completed', 'disputed', 'expired', 'cancelled'].includes(t.status)
      ).length,
    }
  }, [tasks, applications])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Mis Tareas</h1>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            <svg
              className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Summary Stats */}
      <SummaryStats tasks={tasks} applications={applications} />

      {/* Tab Selector */}
      <TabSelector selected={activeTab} onChange={setActiveTab} counts={tabCounts} />

      {/* Content */}
      {loading ? (
        <LoadingSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={onRefresh} />
      ) : filteredTasks.length === 0 ? (
        <EmptyState tab={activeTab} />
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              application={applicationsByTaskId.get(task.id)}
              tab={activeTab}
              onClick={() => onTaskClick(task)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default MyTasks
