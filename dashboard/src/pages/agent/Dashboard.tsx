/**
 * Agent Dashboard - Overview page for AI agents managing tasks
 *
 * Features:
 * - Stats cards: Active Tasks, Pending Submissions, Total Spent, Success Rate
 * - Recent activity feed
 * - Quick actions: Create Task, Review Submissions
 * - Task status breakdown chart
 */

import { useState, useEffect, useMemo } from 'react'
import type { Task, TaskStatus, Submission } from '../../types/database'

// ============================================================================
// Types
// ============================================================================

interface AgentDashboardProps {
  agentId: string
  onNavigate?: (page: 'create' | 'tasks' | 'review' | 'analytics') => void
  onViewTask?: (task: Task) => void
  onReviewSubmission?: (submission: SubmissionWithContext) => void
}

interface AgentStats {
  activeTasks: number
  pendingSubmissions: number
  totalSpent: number
  successRate: number
  tasksCreated: number
  tasksCompleted: number
  avgCompletionTime: number // hours
  activeWorkers: number
}

interface SubmissionWithContext extends Submission {
  task?: Task
  executor?: {
    id: string
    display_name: string | null
    reputation_score: number
    avatar_url: string | null
    wallet_address: string
  }
}

interface ActivityItem {
  id: string
  type: 'task_created' | 'submission_received' | 'task_completed' | 'payment_sent' | 'dispute_opened' | 'task_accepted'
  title: string
  description: string
  timestamp: string
  metadata?: {
    taskId?: string
    submissionId?: string
    amount?: number
    workerName?: string
  }
}

interface TaskStatusBreakdown {
  status: TaskStatus
  count: number
  color: string
}

// ============================================================================
// Constants
// ============================================================================

const STATUS_COLORS: Record<TaskStatus, string> = {
  published: '#22c55e',
  accepted: '#3b82f6',
  in_progress: '#f59e0b',
  submitted: '#8b5cf6',
  verifying: '#6366f1',
  completed: '#6b7280',
  disputed: '#ef4444',
  expired: '#9ca3af',
  cancelled: '#d1d5db',
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  published: 'Publicadas',
  accepted: 'Aceptadas',
  in_progress: 'En Progreso',
  submitted: 'Por Revisar',
  verifying: 'Verificando',
  completed: 'Completadas',
  disputed: 'Disputadas',
  expired: 'Expiradas',
  cancelled: 'Canceladas',
}

const ACTIVITY_ICONS: Record<ActivityItem['type'], string> = {
  task_created: 'M12 4v16m8-8H4',
  submission_received: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  task_completed: 'M5 13l4 4L19 7',
  payment_sent: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  dispute_opened: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  task_accepted: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
}

const ACTIVITY_COLORS: Record<ActivityItem['type'], string> = {
  task_created: 'text-blue-600 bg-blue-100',
  submission_received: 'text-purple-600 bg-purple-100',
  task_completed: 'text-green-600 bg-green-100',
  payment_sent: 'text-emerald-600 bg-emerald-100',
  dispute_opened: 'text-red-600 bg-red-100',
  task_accepted: 'text-amber-600 bg-amber-100',
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'Ahora'
  if (diffMins < 60) return `Hace ${diffMins} min`
  if (diffHours < 24) return `Hace ${diffHours}h`
  if (diffDays === 1) return 'Ayer'
  if (diffDays < 7) return `Hace ${diffDays} dias`
  return date.toLocaleDateString('es-MX', { month: 'short', day: 'numeric' })
}

function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`
}

// ============================================================================
// Sub-Components
// ============================================================================

function StatCard({
  label,
  value,
  subValue,
  trend,
  icon,
  color = 'gray',
  onClick,
}: {
  label: string
  value: string | number
  subValue?: string
  trend?: { value: number; isPositive: boolean }
  icon: React.ReactNode
  color?: 'blue' | 'green' | 'purple' | 'amber' | 'red' | 'gray'
  onClick?: () => void
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
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-gray-200 p-5 ${onClick ? 'cursor-pointer hover:border-gray-300 hover:shadow-sm transition-all' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subValue && <p className="text-xs text-gray-400 mt-0.5">{subValue}</p>}
          {trend && (
            <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
              <svg
                className={`w-3 h-3 ${trend.isPositive ? '' : 'rotate-180'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
              <span>{formatPercentage(Math.abs(trend.value))}</span>
              <span className="text-gray-400 font-normal">vs anterior</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
    </div>
  )
}

function TaskStatusChart({ data }: { data: TaskStatusBreakdown[] }) {
  const total = data.reduce((sum, item) => sum + item.count, 0)

  if (total === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400 text-sm">
        Sin tareas
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Horizontal bar chart */}
      <div className="h-4 rounded-full overflow-hidden bg-gray-100 flex">
        {data
          .filter((d) => d.count > 0)
          .map((item, index) => (
            <div
              key={item.status}
              className="h-full transition-all duration-300"
              style={{
                width: `${(item.count / total) * 100}%`,
                backgroundColor: item.color,
              }}
              title={`${STATUS_LABELS[item.status]}: ${item.count}`}
            />
          ))}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-2">
        {data
          .filter((d) => d.count > 0)
          .map((item) => (
            <div key={item.status} className="flex items-center gap-2 text-sm">
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-gray-600 truncate">{STATUS_LABELS[item.status]}</span>
              <span className="font-medium text-gray-900 ml-auto">{item.count}</span>
            </div>
          ))}
      </div>
    </div>
  )
}

function PendingSubmissionCard({
  submission,
  onReview,
}: {
  submission: SubmissionWithContext
  onReview?: () => void
}) {
  const executor = submission.executor
  const task = submission.task
  const hasAutoCheckPassed = submission.auto_check_passed

  return (
    <div className={`p-4 rounded-lg border ${hasAutoCheckPassed ? 'bg-green-50 border-green-200' : 'bg-purple-50 border-purple-200'}`}>
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-purple-200 flex items-center justify-center flex-shrink-0">
          {executor?.avatar_url ? (
            <img
              src={executor.avatar_url}
              alt={executor.display_name || 'Trabajador'}
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            <span className="text-purple-700 font-medium text-sm">
              {(executor?.display_name || 'T')[0].toUpperCase()}
            </span>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-gray-900">
              {executor?.display_name || 'Trabajador Anonimo'}
            </p>
            <span className="flex items-center gap-1 text-xs text-amber-600">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              {executor?.reputation_score ?? 50}
            </span>
            {hasAutoCheckPassed && (
              <span className="flex items-center gap-1 text-xs text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Auto-verificado
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 truncate mt-0.5">{task?.title || 'Tarea'}</p>
          <p className="text-xs text-gray-400 mt-1">
            Enviado {formatRelativeTime(submission.submitted_at)}
          </p>
        </div>

        {/* Review button */}
        <button
          onClick={onReview}
          className="px-3 py-1.5 bg-purple-600 text-white text-xs font-medium rounded-lg hover:bg-purple-700 transition-colors flex-shrink-0"
        >
          Revisar
        </button>
      </div>
    </div>
  )
}

function ActivityFeedItem({ activity }: { activity: ActivityItem }) {
  const iconPath = ACTIVITY_ICONS[activity.type]
  const colorClass = ACTIVITY_COLORS[activity.type]

  return (
    <div className="flex items-start gap-3 py-3">
      <div className={`p-2 rounded-lg flex-shrink-0 ${colorClass}`}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
        </svg>
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{activity.title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{activity.description}</p>
      </div>

      <span className="text-xs text-gray-400 flex-shrink-0">
        {formatRelativeTime(activity.timestamp)}
      </span>
    </div>
  )
}

function QuickActionButton({
  label,
  icon,
  color,
  onClick,
  badge,
}: {
  label: string
  icon: React.ReactNode
  color: 'blue' | 'purple' | 'green' | 'amber'
  onClick?: () => void
  badge?: number
}) {
  const colorClasses = {
    blue: 'bg-blue-600 hover:bg-blue-700 text-white',
    purple: 'bg-purple-600 hover:bg-purple-700 text-white',
    green: 'bg-green-600 hover:bg-green-700 text-white',
    amber: 'bg-amber-600 hover:bg-amber-700 text-white',
  }

  return (
    <button
      onClick={onClick}
      className={`relative flex items-center gap-2 px-4 py-3 rounded-lg font-medium text-sm transition-colors ${colorClasses[color]}`}
    >
      {icon}
      <span>{label}</span>
      {badge !== undefined && badge > 0 && (
        <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
          {badge > 9 ? '9+' : badge}
        </span>
      )}
    </button>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function Dashboard({
  agentId,
  onNavigate,
  onViewTask,
  onReviewSubmission,
}: AgentDashboardProps) {
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([])
  const [pendingSubmissions, setPendingSubmissions] = useState<SubmissionWithContext[]>([])
  const [taskBreakdown, setTaskBreakdown] = useState<TaskStatusBreakdown[]>([])
  const [loading, setLoading] = useState(true)

  // Load dashboard data
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)

      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500))

      // Mock stats
      setStats({
        activeTasks: 12,
        pendingSubmissions: 3,
        totalSpent: 2847.50,
        successRate: 87.5,
        tasksCreated: 67,
        tasksCompleted: 52,
        avgCompletionTime: 4.2,
        activeWorkers: 18,
      })

      // Mock task status breakdown
      setTaskBreakdown([
        { status: 'published', count: 4, color: STATUS_COLORS.published },
        { status: 'accepted', count: 2, color: STATUS_COLORS.accepted },
        { status: 'in_progress', count: 3, color: STATUS_COLORS.in_progress },
        { status: 'submitted', count: 3, color: STATUS_COLORS.submitted },
        { status: 'completed', count: 52, color: STATUS_COLORS.completed },
        { status: 'disputed', count: 2, color: STATUS_COLORS.disputed },
        { status: 'cancelled', count: 1, color: STATUS_COLORS.cancelled },
      ])

      // Mock pending submissions
      setPendingSubmissions([
        {
          id: 'sub-1',
          task_id: 'task-1',
          executor_id: 'exec-1',
          evidence: {},
          evidence_files: ['photo.jpg'],
          evidence_ipfs_cid: null,
          evidence_hash: null,
          chainwitness_proof: null,
          submitted_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          verified_at: null,
          auto_check_passed: true,
          auto_check_details: { gps_verified: true },
          agent_verdict: null,
          agent_notes: null,
          payment_tx: null,
          paid_at: null,
          payment_amount: null,
          task: {
            id: 'task-1',
            agent_id: agentId,
            category: 'physical_presence',
            title: 'Verificar direccion en Polanco',
            instructions: 'Tomar foto del edificio',
            location: null,
            location_radius_km: null,
            location_hint: 'Polanco, CDMX',
            evidence_schema: { required: ['photo_geo'] },
            bounty_usd: 15.00,
            payment_token: 'USDC',
            escrow_tx: null,
            escrow_id: null,
            deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            min_reputation: 50,
            required_roles: [],
            max_executors: 1,
            status: 'submitted',
            executor_id: 'exec-1',
            accepted_at: null,
            chainwitness_proof: null,
            completed_at: null,
          },
          executor: {
            id: 'exec-1',
            display_name: 'Maria Garcia',
            reputation_score: 82,
            avatar_url: null,
            wallet_address: '0x1234...5678',
          },
        },
        {
          id: 'sub-2',
          task_id: 'task-2',
          executor_id: 'exec-2',
          evidence: {},
          evidence_files: ['photo.jpg'],
          evidence_ipfs_cid: null,
          evidence_hash: null,
          chainwitness_proof: null,
          submitted_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          verified_at: null,
          auto_check_passed: false,
          auto_check_details: { gps_verified: false, reason: 'GPS fuera de rango' },
          agent_verdict: null,
          agent_notes: null,
          payment_tx: null,
          paid_at: null,
          payment_amount: null,
          task: {
            id: 'task-2',
            agent_id: agentId,
            category: 'simple_action',
            title: 'Recoger paquete en OXXO',
            instructions: 'Recoger con codigo QR',
            location: null,
            location_radius_km: null,
            location_hint: 'Reforma, CDMX',
            evidence_schema: { required: ['photo', 'receipt'] },
            bounty_usd: 8.00,
            payment_token: 'USDC',
            escrow_tx: null,
            escrow_id: null,
            deadline: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            min_reputation: 30,
            required_roles: [],
            max_executors: 1,
            status: 'submitted',
            executor_id: 'exec-2',
            accepted_at: null,
            chainwitness_proof: null,
            completed_at: null,
          },
          executor: {
            id: 'exec-2',
            display_name: 'Carlos Lopez',
            reputation_score: 65,
            avatar_url: null,
            wallet_address: '0x9876...4321',
          },
        },
      ])

      // Mock activity
      setRecentActivity([
        {
          id: 'act-1',
          type: 'submission_received',
          title: 'Nueva entrega recibida',
          description: 'Maria Garcia envio evidencia para "Verificar direccion"',
          timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        },
        {
          id: 'act-2',
          type: 'task_accepted',
          title: 'Tarea aceptada',
          description: 'Carlos Lopez acepto "Recoger paquete en OXXO"',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: 'act-3',
          type: 'task_completed',
          title: 'Tarea completada',
          description: 'Verificacion de local finalizada exitosamente',
          timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: 'act-4',
          type: 'payment_sent',
          title: 'Pago enviado',
          description: '$12.00 USDC enviados a Juan Perez',
          timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: 'act-5',
          type: 'task_created',
          title: 'Tarea publicada',
          description: 'Nueva tarea "Firmar documento" creada',
          timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        },
      ])

      setLoading(false)
    }

    loadData()
  }, [agentId])

  // Loading state
  if (loading || !stats) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded w-48 animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="h-4 bg-gray-200 rounded w-20 animate-pulse" />
              <div className="h-8 bg-gray-200 rounded w-16 mt-2 animate-pulse" />
            </div>
          ))}
        </div>
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5 h-64 animate-pulse" />
          <div className="bg-white rounded-xl border border-gray-200 p-5 h-64 animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Panel de Agente</h1>
          <p className="text-sm text-gray-500">Gestiona tus tareas y revisa entregas</p>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <QuickActionButton
            label="Crear Tarea"
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            }
            color="blue"
            onClick={() => onNavigate?.('create')}
          />
          <QuickActionButton
            label="Revisar Entregas"
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            }
            color="purple"
            onClick={() => onNavigate?.('review')}
            badge={stats.pendingSubmissions}
          />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Tareas Activas"
          value={stats.activeTasks}
          subValue={`${stats.tasksCreated} totales creadas`}
          color="blue"
          onClick={() => onNavigate?.('tasks')}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          }
        />
        <StatCard
          label="Por Revisar"
          value={stats.pendingSubmissions}
          subValue="Entregas pendientes"
          color="purple"
          onClick={() => onNavigate?.('review')}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          }
        />
        <StatCard
          label="Gasto Total"
          value={formatCurrency(stats.totalSpent)}
          subValue="Este mes"
          trend={{ value: 12.5, isPositive: true }}
          color="green"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          label="Tasa de Exito"
          value={formatPercentage(stats.successRate)}
          subValue={`${stats.tasksCompleted} completadas`}
          trend={{ value: 3.2, isPositive: true }}
          color="amber"
          onClick={() => onNavigate?.('analytics')}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Task Status Breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-gray-900">Estado de Tareas</h2>
              <p className="text-xs text-gray-500 mt-0.5">Distribucion por estado</p>
            </div>
            <button
              onClick={() => onNavigate?.('tasks')}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Ver todas
            </button>
          </div>
          <div className="p-5">
            <TaskStatusChart data={taskBreakdown} />
          </div>
        </div>

        {/* Pending Submissions */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-gray-900">Entregas Pendientes</h2>
              {pendingSubmissions.length > 0 && (
                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                  {pendingSubmissions.length}
                </span>
              )}
            </div>
            <button
              onClick={() => onNavigate?.('review')}
              className="text-sm text-purple-600 hover:text-purple-700 font-medium"
            >
              Revisar todas
            </button>
          </div>
          <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
            {pendingSubmissions.length === 0 ? (
              <div className="text-center py-8">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-sm text-gray-500">No hay entregas pendientes</p>
              </div>
            ) : (
              pendingSubmissions.map((submission) => (
                <PendingSubmissionCard
                  key={submission.id}
                  submission={submission}
                  onReview={() => onReviewSubmission?.(submission)}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Actividad Reciente</h2>
        </div>
        <div className="divide-y divide-gray-100 px-5 max-h-80 overflow-y-auto">
          {recentActivity.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-gray-500">No hay actividad reciente</p>
            </div>
          ) : (
            recentActivity.map((activity) => (
              <ActivityFeedItem key={activity.id} activity={activity} />
            ))
          )}
        </div>
        {recentActivity.length > 5 && (
          <div className="px-5 py-3 border-t border-gray-100 bg-gray-50">
            <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
              Ver toda la actividad
            </button>
          </div>
        )}
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{stats.activeWorkers}</p>
          <p className="text-sm text-gray-500 mt-1">Trabajadores activos</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{stats.avgCompletionTime}h</p>
          <p className="text-sm text-gray-500 mt-1">Tiempo promedio</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(stats.totalSpent / stats.tasksCompleted)}</p>
          <p className="text-sm text-gray-500 mt-1">Costo promedio</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{stats.tasksCompleted}</p>
          <p className="text-sm text-gray-500 mt-1">Completadas este mes</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
