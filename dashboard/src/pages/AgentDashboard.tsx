// Execution Market: Agent Dashboard Page (NOW-034)
// Dashboard for AI agents managing tasks, reviewing submissions, and viewing analytics

import { useState, useCallback, useEffect } from 'react'
import type { Task, TaskStatus, TaskCategory, Submission } from '../types/database'
import { usePublicMetrics } from '../hooks/usePublicMetrics'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface AgentDashboardProps {
  agentId: string
  onBack?: () => void
  onCreateTask?: () => void
  onReviewSubmission?: (submission: AgentSubmission) => void
  onViewTask?: (task: Task) => void
}

interface AgentAnalytics {
  tasksCreated: number
  tasksCompleted: number
  tasksPending: number
  totalSpent: number
  completionRate: number
  avgCompletionTime: number // hours
  activeExecutors: number
}

interface AgentSubmission extends Submission {
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
  type: 'task_created' | 'submission_received' | 'task_completed' | 'payment_sent' | 'dispute_opened'
  title: string
  description: string
  timestamp: string
  metadata?: {
    taskId?: string
    submissionId?: string
    amount?: number
  }
}

// --------------------------------------------------------------------------
// Helper Functions
// --------------------------------------------------------------------------

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

function formatDeadline(deadline: string): string {
  const date = new Date(deadline)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffMs < 0) return 'Expirada'
  if (diffHours < 1) return 'Menos de 1h'
  if (diffHours < 24) return `${diffHours}h restantes`
  if (diffDays === 1) return '1 dia'
  return `${diffDays} dias`
}

// --------------------------------------------------------------------------
// Status Configuration
// --------------------------------------------------------------------------

const STATUS_CONFIG: Record<TaskStatus, { label: string; className: string; dotColor: string }> = {
  published: { label: 'Publicada', className: 'bg-green-100 text-green-800', dotColor: 'bg-green-500' },
  accepted: { label: 'Aceptada', className: 'bg-blue-100 text-blue-800', dotColor: 'bg-blue-500' },
  in_progress: { label: 'En Progreso', className: 'bg-yellow-100 text-yellow-800', dotColor: 'bg-yellow-500' },
  submitted: { label: 'Por Revisar', className: 'bg-purple-100 text-purple-800', dotColor: 'bg-purple-500' },
  verifying: { label: 'Verificando', className: 'bg-indigo-100 text-indigo-800', dotColor: 'bg-indigo-500' },
  completed: { label: 'Completada', className: 'bg-gray-100 text-gray-800', dotColor: 'bg-gray-500' },
  disputed: { label: 'En Disputa', className: 'bg-red-100 text-red-800', dotColor: 'bg-red-500' },
  expired: { label: 'Expirada', className: 'bg-gray-100 text-gray-500', dotColor: 'bg-gray-400' },
  cancelled: { label: 'Cancelada', className: 'bg-gray-100 text-gray-400', dotColor: 'bg-gray-300' },
}

const CATEGORY_LABELS: Record<TaskCategory, string> = {
  physical_presence: 'Presencia Fisica',
  knowledge_access: 'Acceso a Conocimiento',
  human_authority: 'Autoridad Humana',
  simple_action: 'Accion Simple',
  digital_physical: 'Digital-Fisico',
}

const ACTIVITY_ICONS: Record<ActivityItem['type'], string> = {
  task_created: 'M12 4v16m8-8H4',
  submission_received: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  task_completed: 'M5 13l4 4L19 7',
  payment_sent: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  dispute_opened: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
}

const ACTIVITY_COLORS: Record<ActivityItem['type'], string> = {
  task_created: 'text-blue-600 bg-blue-100',
  submission_received: 'text-purple-600 bg-purple-100',
  task_completed: 'text-green-600 bg-green-100',
  payment_sent: 'text-emerald-600 bg-emerald-100',
  dispute_opened: 'text-red-600 bg-red-100',
}

// --------------------------------------------------------------------------
// Sub-Components
// --------------------------------------------------------------------------

function StatusBadge({ status }: { status: TaskStatus }) {
  const config = STATUS_CONFIG[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full ${config.className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
      {config.label}
    </span>
  )
}

function StatCard({
  label,
  value,
  subValue,
  trend,
  icon,
}: {
  label: string
  value: string | number
  subValue?: string
  trend?: { value: number; isPositive: boolean }
  icon: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-500 font-medium">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subValue && <p className="text-xs text-gray-400 mt-0.5">{subValue}</p>}
          {trend && (
            <p className={`text-xs mt-1 ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {trend.isPositive ? '+' : ''}{trend.value}% vs mes anterior
            </p>
          )}
        </div>
        <div className="p-2 bg-gray-50 rounded-lg">{icon}</div>
      </div>
    </div>
  )
}

function ActiveTaskItem({
  task,
  onClick,
}: {
  task: Task
  onClick?: () => void
}) {
  const isExpiringSoon = new Date(task.deadline).getTime() - Date.now() < 24 * 60 * 60 * 1000
  const statusConfig = STATUS_CONFIG[task.status]

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors"
    >
      {/* Status indicator */}
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${statusConfig.dotColor}`} />

      {/* Task info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-500">{CATEGORY_LABELS[task.category]}</span>
          <span className="text-xs text-gray-300">|</span>
          <span className={`text-xs ${isExpiringSoon ? 'text-orange-600 font-medium' : 'text-gray-500'}`}>
            {formatDeadline(task.deadline)}
          </span>
        </div>
      </div>

      {/* Bounty and status */}
      <div className="text-right flex-shrink-0">
        <p className="text-sm font-semibold text-gray-900">{formatCurrency(task.bounty_usd)}</p>
        <StatusBadge status={task.status} />
      </div>
    </div>
  )
}

function PendingSubmissionItem({
  submission,
  onReview,
}: {
  submission: AgentSubmission
  onReview?: () => void
}) {
  const executor = submission.executor
  const task = submission.task

  return (
    <div className="flex items-start gap-3 p-4 bg-purple-50 border border-purple-100 rounded-lg">
      {/* Executor avatar */}
      <div className="w-10 h-10 bg-purple-200 rounded-full flex items-center justify-center flex-shrink-0">
        {executor?.avatar_url ? (
          <img
            src={executor.avatar_url}
            alt={executor.display_name || 'Ejecutor'}
            className="w-full h-full rounded-full object-cover"
          />
        ) : (
          <span className="text-purple-700 font-medium text-sm">
            {(executor?.display_name || 'E')[0].toUpperCase()}
          </span>
        )}
      </div>

      {/* Submission info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-gray-900">
            {executor?.display_name || 'Ejecutor Anonimo'}
          </p>
          <span className="flex items-center gap-1 text-xs text-amber-600">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            {executor?.reputation_score ?? 50}
          </span>
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
  )
}

function ActivityFeedItem({ activity }: { activity: ActivityItem }) {
  const iconPath = ACTIVITY_ICONS[activity.type]
  const colorClass = ACTIVITY_COLORS[activity.type]

  return (
    <div className="flex items-start gap-3 py-3">
      {/* Icon */}
      <div className={`p-2 rounded-lg flex-shrink-0 ${colorClass}`}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
        </svg>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{activity.title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{activity.description}</p>
      </div>

      {/* Timestamp */}
      <span className="text-xs text-gray-400 flex-shrink-0">
        {formatRelativeTime(activity.timestamp)}
      </span>
    </div>
  )
}

// --------------------------------------------------------------------------
// Main Component
// --------------------------------------------------------------------------

export function AgentDashboard({
  agentId,
  onBack,
  onCreateTask,
  onReviewSubmission,
  onViewTask,
}: AgentDashboardProps) {
  // State
  const [activeTasks, setActiveTasks] = useState<Task[]>([])
  const [pendingSubmissions, setPendingSubmissions] = useState<AgentSubmission[]>([])
  const [analytics, setAnalytics] = useState<AgentAnalytics | null>(null)
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTasksFilter, setActiveTasksFilter] = useState<'all' | 'pending' | 'in_progress'>('all')
  const { metrics: platformMetrics, loading: platformMetricsLoading } = usePublicMetrics()

  // Mock data load - in production, fetch from API/Supabase
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)

      // Simulate API call delay
      await new Promise((resolve) => setTimeout(resolve, 500))

      // Mock analytics
      setAnalytics({
        tasksCreated: 47,
        tasksCompleted: 38,
        tasksPending: 9,
        totalSpent: 1892.50,
        completionRate: 80.85,
        avgCompletionTime: 4.2,
        activeExecutors: 12,
      })

      // Mock active tasks
      setActiveTasks([
        {
          id: '1',
          agent_id: agentId,
          category: 'physical_presence',
          title: 'Verificar direccion de entrega en Polanco',
          instructions: 'Tomar foto del exterior del edificio y confirmar numero',
          location: { lat: 19.4326, lng: -99.1332 },
          location_radius_km: 0.5,
          location_hint: 'Polanco, CDMX',
          evidence_schema: { required: ['photo_geo'] },
          bounty_usd: 15.00,
          payment_token: 'USDC',
          escrow_tx: null,
          escrow_id: null,
          deadline: new Date(Date.now() + 12 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          min_reputation: 50,
          required_roles: [],
          max_executors: 1,
          status: 'in_progress',
          executor_id: 'exec-1',
          accepted_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
          chainwitness_proof: null,
          completed_at: null,
        },
        {
          id: '2',
          agent_id: agentId,
          category: 'human_authority',
          title: 'Firmar documento notarial en notaria 45',
          instructions: 'Presentarse con INE y firmar contrato de arrendamiento',
          location: { lat: 19.4284, lng: -99.1676 },
          location_radius_km: 0.2,
          location_hint: 'Roma Norte, CDMX',
          evidence_schema: { required: ['document', 'signature'] },
          bounty_usd: 45.00,
          payment_token: 'USDC',
          escrow_tx: null,
          escrow_id: null,
          deadline: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          min_reputation: 75,
          required_roles: [],
          max_executors: 1,
          status: 'published',
          executor_id: null,
          accepted_at: null,
          chainwitness_proof: null,
          completed_at: null,
        },
        {
          id: '3',
          agent_id: agentId,
          category: 'simple_action',
          title: 'Recoger paquete en OXXO Reforma',
          instructions: 'Mostrar codigo QR y recoger paquete',
          location: { lat: 19.4352, lng: -99.1537 },
          location_radius_km: 0.1,
          location_hint: 'Reforma, CDMX',
          evidence_schema: { required: ['photo', 'receipt'] },
          bounty_usd: 8.00,
          payment_token: 'USDC',
          escrow_tx: null,
          escrow_id: null,
          deadline: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          min_reputation: 30,
          required_roles: [],
          max_executors: 1,
          status: 'submitted',
          executor_id: 'exec-2',
          accepted_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
          chainwitness_proof: null,
          completed_at: null,
        },
      ])

      // Mock pending submissions
      setPendingSubmissions([
        {
          id: 'sub-1',
          task_id: '3',
          executor_id: 'exec-2',
          evidence: { photo: 'ipfs://...', receipt: 'ipfs://...' },
          evidence_files: ['photo.jpg', 'receipt.jpg'],
          evidence_ipfs_cid: 'QmXx...',
          evidence_hash: '0xabc...',
          chainwitness_proof: null,
          submitted_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          verified_at: null,
          auto_check_passed: true,
          auto_check_details: { gps_verified: true, timestamp_valid: true },
          agent_verdict: null,
          agent_notes: null,
          payment_tx: null,
          paid_at: null,
          payment_amount: null,
          task: {
            id: '3',
            agent_id: agentId,
            category: 'simple_action',
            title: 'Recoger paquete en OXXO Reforma',
            instructions: 'Mostrar codigo QR y recoger paquete',
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
            display_name: 'Maria Garcia',
            reputation_score: 82,
            avatar_url: null,
            wallet_address: '0x1234...5678',
          },
        },
        {
          id: 'sub-2',
          task_id: '4',
          executor_id: 'exec-3',
          evidence: { photo_geo: 'ipfs://...' },
          evidence_files: ['verificacion.jpg'],
          evidence_ipfs_cid: 'QmYy...',
          evidence_hash: '0xdef...',
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
            id: '4',
            agent_id: agentId,
            category: 'knowledge_access',
            title: 'Verificar horarios de farmacia',
            instructions: 'Confirmar horarios reales de la farmacia',
            location: null,
            location_radius_km: null,
            location_hint: 'Condesa, CDMX',
            evidence_schema: { required: ['photo_geo'] },
            bounty_usd: 5.00,
            payment_token: 'USDC',
            escrow_tx: null,
            escrow_id: null,
            deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            min_reputation: 20,
            required_roles: [],
            max_executors: 1,
            status: 'submitted',
            executor_id: 'exec-3',
            accepted_at: null,
            chainwitness_proof: null,
            completed_at: null,
          },
          executor: {
            id: 'exec-3',
            display_name: 'Carlos Lopez',
            reputation_score: 65,
            avatar_url: null,
            wallet_address: '0x9876...4321',
          },
        },
      ])

      // Mock recent activity
      setRecentActivity([
        {
          id: 'act-1',
          type: 'submission_received',
          title: 'Nueva evidencia recibida',
          description: 'Maria Garcia envio evidencia para "Recoger paquete en OXXO"',
          timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          metadata: { taskId: '3', submissionId: 'sub-1' },
        },
        {
          id: 'act-2',
          type: 'task_completed',
          title: 'Tarea completada',
          description: 'Verificacion de local en Coyoacan finalizada exitosamente',
          timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
          metadata: { taskId: '5' },
        },
        {
          id: 'act-3',
          type: 'payment_sent',
          title: 'Pago enviado',
          description: '$12.00 USDC enviados a Juan Perez',
          timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
          metadata: { amount: 12.00 },
        },
        {
          id: 'act-4',
          type: 'task_created',
          title: 'Tarea publicada',
          description: 'Nueva tarea "Firmar documento notarial" creada',
          timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          metadata: { taskId: '2' },
        },
        {
          id: 'act-5',
          type: 'dispute_opened',
          title: 'Disputa abierta',
          description: 'Ejecutor disputo el rechazo de evidencia',
          timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
          metadata: { taskId: '6' },
        },
      ])

      setLoading(false)
    }

    loadData()
  }, [agentId])

  // Filter active tasks
  const filteredTasks = activeTasks.filter((task) => {
    if (activeTasksFilter === 'all') return true
    if (activeTasksFilter === 'pending') return task.status === 'published' || task.status === 'submitted'
    if (activeTasksFilter === 'in_progress') return task.status === 'in_progress' || task.status === 'accepted'
    return true
  })

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        {/* Skeleton header */}
        <div className="h-8 bg-gray-200 rounded w-48 animate-pulse" />

        {/* Skeleton stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="h-4 bg-gray-200 rounded w-20 animate-pulse" />
              <div className="h-8 bg-gray-200 rounded w-16 mt-2 animate-pulse" />
            </div>
          ))}
        </div>

        {/* Skeleton content */}
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border border-gray-200 p-4 h-64 animate-pulse" />
          <div className="bg-white rounded-lg border border-gray-200 p-4 h-64 animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Header */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          <div>
            <h1 className="text-xl font-bold text-gray-900">Panel de Agente</h1>
            <p className="text-sm text-gray-500">Gestiona tus tareas y revisa entregas</p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onCreateTask}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Crear Tarea
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Analytics Overview */}
      {/* ------------------------------------------------------------------ */}
      <section>
        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
          Platform Pulse
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Usuarios Registrados"
            value={
              platformMetricsLoading || !platformMetrics
                ? '...'
                : new Intl.NumberFormat('en-US').format(platformMetrics.users.registered_workers)
            }
            icon={
              <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5V4H2v16h5m10 0v-8a2 2 0 00-2-2H9a2 2 0 00-2 2v8m10 0H7" />
              </svg>
            }
          />
          <StatCard
            label="Workers Activos"
            value={
              platformMetricsLoading || !platformMetrics
                ? '...'
                : new Intl.NumberFormat('en-US').format(platformMetrics.activity.workers_with_active_tasks)
            }
            icon={
              <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            }
          />
          <StatCard
            label="Agentes Activos"
            value={
              platformMetricsLoading || !platformMetrics
                ? '...'
                : new Intl.NumberFormat('en-US').format(platformMetrics.activity.agents_with_live_tasks)
            }
            icon={
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7h18M3 12h18M3 17h18" />
              </svg>
            }
          />
          <StatCard
            label="Tareas Completadas"
            value={
              platformMetricsLoading || !platformMetrics
                ? '...'
                : new Intl.NumberFormat('en-US').format(platformMetrics.tasks.completed)
            }
            icon={
              <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
        </div>
      </section>

      {analytics && (
        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
            Resumen de Actividad
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Tareas Creadas"
              value={analytics.tasksCreated}
              subValue={`${analytics.tasksPending} pendientes`}
              icon={
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              }
            />
            <StatCard
              label="Tasa de Completado"
              value={`${analytics.completionRate.toFixed(1)}%`}
              subValue={`${analytics.tasksCompleted} completadas`}
              trend={{ value: 5.2, isPositive: true }}
              icon={
                <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <StatCard
              label="Gasto Total"
              value={formatCurrency(analytics.totalSpent)}
              subValue="Este mes"
              icon={
                <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <StatCard
              label="Tiempo Promedio"
              value={`${analytics.avgCompletionTime}h`}
              subValue={`${analytics.activeExecutors} ejecutores activos`}
              icon={
                <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
          </div>
        </section>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Main Content Grid */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Active Tasks */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Tareas Activas</h2>
            <div className="flex items-center gap-1">
              {(['all', 'pending', 'in_progress'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setActiveTasksFilter(filter)}
                  className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                    activeTasksFilter === filter
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  {filter === 'all' ? 'Todas' : filter === 'pending' ? 'Pendientes' : 'En Progreso'}
                </button>
              ))}
            </div>
          </div>

          <div className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
            {filteredTasks.length === 0 ? (
              <div className="p-6 text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <p className="text-sm text-gray-500">No hay tareas con este filtro</p>
              </div>
            ) : (
              filteredTasks.map((task) => (
                <ActiveTaskItem
                  key={task.id}
                  task={task}
                  onClick={() => onViewTask?.(task)}
                />
              ))
            )}
          </div>

          {filteredTasks.length > 0 && (
            <div className="px-4 py-3 border-t border-gray-100 bg-gray-50">
              <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                Ver todas las tareas
              </button>
            </div>
          )}
        </section>

        {/* Pending Submissions */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-gray-900">Entregas por Revisar</h2>
              {pendingSubmissions.length > 0 && (
                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                  {pendingSubmissions.length}
                </span>
              )}
            </div>
          </div>

          <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
            {pendingSubmissions.length === 0 ? (
              <div className="text-center py-6">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-sm text-gray-500">No hay entregas pendientes</p>
                <p className="text-xs text-gray-400 mt-1">Las entregas apareceran aqui para revision</p>
              </div>
            ) : (
              pendingSubmissions.map((submission) => (
                <PendingSubmissionItem
                  key={submission.id}
                  submission={submission}
                  onReview={() => onReviewSubmission?.(submission)}
                />
              ))
            )}
          </div>

          {pendingSubmissions.length > 0 && (
            <div className="px-4 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
              <span className="text-xs text-gray-500">
                {pendingSubmissions.filter((s) => s.auto_check_passed).length} pasaron verificacion automatica
              </span>
              <button className="text-sm text-purple-600 hover:text-purple-700 font-medium">
                Revisar todas
              </button>
            </div>
          )}
        </section>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Quick Actions Bar */}
      {/* ------------------------------------------------------------------ */}
      <section className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-white font-medium">Acciones Rapidas</h3>
            <p className="text-blue-100 text-sm">Atajos para tareas comunes</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onCreateTask}
              className="flex items-center gap-2 px-4 py-2 bg-white text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Nueva Tarea
            </button>
            <button
              onClick={() => pendingSubmissions[0] && onReviewSubmission?.(pendingSubmissions[0])}
              disabled={pendingSubmissions.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              Revisar Siguiente
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-400 transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Ver Reportes
            </button>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Recent Activity */}
      {/* ------------------------------------------------------------------ */}
      <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Actividad Reciente</h2>
        </div>

        <div className="divide-y divide-gray-100 px-4">
          {recentActivity.length === 0 ? (
            <div className="py-6 text-center">
              <p className="text-sm text-gray-500">No hay actividad reciente</p>
            </div>
          ) : (
            recentActivity.map((activity) => (
              <ActivityFeedItem key={activity.id} activity={activity} />
            ))
          )}
        </div>

        {recentActivity.length > 5 && (
          <div className="px-4 py-3 border-t border-gray-100 bg-gray-50">
            <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
              Ver toda la actividad
            </button>
          </div>
        )}
      </section>
    </div>
  )
}

export default AgentDashboard
