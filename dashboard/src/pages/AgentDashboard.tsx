// Execution Market: Agent Dashboard Page (NOW-034)
// Dashboard for AI agents managing tasks, reviewing submissions, and viewing analytics

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import type { Task, TaskStatus, Submission } from '../types/database'
import { usePublicMetrics } from '../hooks/usePublicMetrics'
import { WorkerRatingModal } from '../components/WorkerRatingModal'
import { WorkerReputationBadge } from '../components/WorkerReputationBadge'
import { TxHashLink } from '../components/TxLink'
import { getAgentTasks, getTaskAnalytics } from '../services/tasks'
import { getPendingSubmissions } from '../services/submissions'
import { getAgentReputation, type ReputationInfo } from '../services/reputation'
import { safeSrc } from '../lib/safeHref'
import { Pill } from '../components/ui/Pill'
import { StatusBadge } from '../components/ui/StatusBadge'
import { getStatusDotClass } from '../lib/taskStatus'

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

interface AgentSubmission extends Omit<Submission, 'executor'> {
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
  return new Intl.NumberFormat('en-US', {
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

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatDeadline(deadline: string): string {
  const date = new Date(deadline)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffMs < 0) return 'Expired'
  if (diffHours < 1) return '< 1h left'
  if (diffHours < 24) return `${diffHours}h left`
  if (diffDays === 1) return '1 day'
  return `${diffDays} days`
}

// --------------------------------------------------------------------------
// Status Configuration
// --------------------------------------------------------------------------

const ACTIVITY_ICONS: Record<ActivityItem['type'], string> = {
  task_created: 'M12 4v16m8-8H4',
  submission_received: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  task_completed: 'M5 13l4 4L19 7',
  payment_sent: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  dispute_opened: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
}

const ACTIVITY_COLORS: Record<ActivityItem['type'], string> = {
  task_created: 'text-zinc-900 bg-zinc-100',
  submission_received: 'text-zinc-900 bg-zinc-200',
  task_completed: 'text-white bg-zinc-900',
  payment_sent: 'text-white bg-zinc-900',
  dispute_opened: 'text-red-700 bg-red-50 ring-1 ring-red-300',
}

// --------------------------------------------------------------------------
// Sub-Components
// --------------------------------------------------------------------------

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
    <div className="bg-white rounded-lg border border-zinc-200 p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-zinc-500 font-medium">{label}</p>
          <p className="text-2xl font-bold text-zinc-900 mt-1">{value}</p>
          {subValue && <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-0.5">{subValue}</p>}
          {trend && (
            <p className={`text-xs mt-1 ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {trend.isPositive ? '+' : ''}{trend.value}% vs mes anterior
            </p>
          )}
        </div>
        <div className="p-2 bg-zinc-50 rounded-lg">{icon}</div>
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
  const { t } = useTranslation()
  const isExpiringSoon = new Date(task.deadline).getTime() - Date.now() < 24 * 60 * 60 * 1000

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 p-3 hover:bg-zinc-50 rounded-lg cursor-pointer transition-colors"
    >
      {/* Status indicator */}
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${getStatusDotClass(task.status)}`} />

      {/* Task info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-900 truncate">{task.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-zinc-500">{t(`tasks.categories.${task.category}`, task.category)}</span>
          <span className="text-xs text-zinc-400">|</span>
          <span className={`text-xs ${isExpiringSoon ? 'text-amber-700 font-medium' : 'text-zinc-500'}`}>
            {formatDeadline(task.deadline)}
          </span>
        </div>
      </div>

      {/* Bounty and status */}
      <div className="text-right flex-shrink-0">
        <p className="text-sm font-semibold text-zinc-900">{formatCurrency(task.bounty_usd)}</p>
        <StatusBadge status={task.status} size="sm" withDot label={t(`tasks.statuses.${task.status}`, task.status)} />
      </div>
    </div>
  )
}

function PendingSubmissionItem({
  submission,
  onReview,
  onApproveAndRate,
}: {
  submission: AgentSubmission
  onReview?: () => void
  onApproveAndRate?: () => void
}) {
  const executor = submission.executor
  const task = submission.task

  return (
    <div className="flex items-start gap-3 p-4 bg-purple-50 border border-purple-100 rounded-lg">
      {/* Executor avatar */}
      <div className="w-10 h-10 bg-purple-200 rounded-full flex items-center justify-center flex-shrink-0">
        {executor?.avatar_url ? (
          <img
            src={safeSrc(executor.avatar_url)}
            alt={executor.display_name || 'Worker'}
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
            {executor?.display_name || 'Anonymous Worker'}
          </p>
          {executor && (
            <WorkerReputationBadge score={executor.reputation_score ?? 50} />
          )}
        </div>
        <p className="text-sm text-gray-600 truncate mt-0.5">{task?.title || 'Task'}</p>
        <p className="text-xs text-gray-400 mt-1">
          Submitted {formatRelativeTime(submission.submitted_at)}
        </p>
        {submission.reputation_tx && (
          <div className="flex items-center gap-1.5 mt-1">
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              ERC-8004
            </span>
            <TxHashLink txHash={submission.reputation_tx} />
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex flex-col gap-1.5 flex-shrink-0">
        <button
          onClick={onReview}
          className="px-3 py-1.5 bg-zinc-200 text-zinc-900 text-xs font-medium rounded-lg hover:bg-zinc-300 transition-colors"
        >
          Review
        </button>
        {submission.auto_check_passed && onApproveAndRate && (
          <button
            onClick={onApproveAndRate}
            className="px-3 py-1.5 bg-zinc-900 text-white text-xs font-medium rounded-lg hover:bg-zinc-800 transition-colors flex items-center gap-1"
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            Approve
          </button>
        )}
      </div>
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
// Agent Reputation Card (On-Chain)
// --------------------------------------------------------------------------

function getReputationTier(score: number): { nameEs: string; color: string; bgColor: string } {
  if (score >= 81) return { nameEs: 'Diamante', color: 'text-blue-700', bgColor: 'bg-blue-100' }
  if (score >= 61) return { nameEs: 'Oro', color: 'text-amber-700', bgColor: 'bg-amber-100' }
  if (score >= 31) return { nameEs: 'Plata', color: 'text-gray-600', bgColor: 'bg-gray-200' }
  return { nameEs: 'Bronce', color: 'text-orange-700', bgColor: 'bg-orange-100' }
}

function AgentReputationCard({
  agentId,
}: {
  agentId: string
}) {
  const { t } = useTranslation()
  const [reputation, setReputation] = useState<ReputationInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    const numericId = parseInt(agentId, 10)
    if (isNaN(numericId)) {
      setLoading(false)
      setError(true)
      return
    }

    getAgentReputation(numericId)
      .then((data) => {
        setReputation(data)
        setLoading(false)
      })
      .catch(() => {
        setError(true)
        setLoading(false)
      })
  }, [agentId])

  if (loading) {
    return (
      <section className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-gray-200 rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="h-5 bg-gray-200 rounded w-1/4" />
              <div className="h-3 bg-gray-200 rounded w-1/2" />
            </div>
          </div>
        </div>
      </section>
    )
  }

  if (error || !reputation) {
    return (
      <section className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-3">
          {t('agentReputation.title', 'Reputacion On-Chain')}
        </h2>
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
          <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-gray-500">
            {t('agentReputation.unavailable', 'Datos on-chain no disponibles')}
          </p>
        </div>
      </section>
    )
  }

  const tier = getReputationTier(reputation.score)
  const scoreRadius = 28
  const scoreCircumference = 2 * Math.PI * scoreRadius
  const scoreProgress = (reputation.score / 100) * scoreCircumference

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-4">
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-3">
        {t('agentReputation.title', 'Reputacion On-Chain')}
      </h2>

      <div className="flex items-center gap-4">
        {/* Score gauge */}
        <div className="relative flex-shrink-0" style={{ width: 72, height: 72 }}>
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="36"
              cy="36"
              r={scoreRadius}
              stroke="currentColor"
              strokeWidth="6"
              fill="none"
              className="text-gray-100"
            />
            <circle
              cx="36"
              cy="36"
              r={scoreRadius}
              stroke="currentColor"
              strokeWidth="6"
              fill="none"
              strokeDasharray={`${scoreProgress} ${scoreCircumference}`}
              strokeLinecap="round"
              className="text-blue-500"
              style={{ transition: 'stroke-dasharray 0.5s ease-out' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-lg font-bold text-gray-900">{reputation.score}</span>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-gray-900">
              {t('agentReputation.score', 'Puntuacion')}
            </span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${tier.bgColor} ${tier.color}`}>
              {tier.nameEs}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-sm text-gray-500">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            <span>
              {reputation.count} {t('agentReputation.ratings', 'calificaciones recibidas')}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-400 mt-0.5">
            <div className="w-2 h-2 bg-zinc-900 dark:bg-zinc-100 rounded-full" />
            <span>ERC-8004 &middot; {reputation.network || 'Base'}</span>
          </div>
        </div>
      </div>
    </section>
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

  // Rating modal state
  const [ratingSubmission, setRatingSubmission] = useState<AgentSubmission | null>(null)

  const { t } = useTranslation()

  // Fetch real data from API/Supabase
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)

      try {
        // Fetch all data in parallel
        const [tasksResult, analyticsResult, submissionsResult] = await Promise.allSettled([
          getAgentTasks(agentId, { limit: 50 }),
          getTaskAnalytics(agentId, 30),
          getPendingSubmissions(agentId),
        ])

        // Map analytics from service shape to component shape
        if (analyticsResult.status === 'fulfilled') {
          const a = analyticsResult.value
          const activeStatuses = ['published', 'accepted', 'in_progress', 'submitted', 'verifying']
          const pending = Object.entries(a.byStatus)
            .filter(([s]) => activeStatuses.includes(s))
            .reduce((sum, [, count]) => sum + count, 0)

          setAnalytics({
            tasksCreated: a.totals.total,
            tasksCompleted: a.totals.completed,
            tasksPending: pending,
            totalSpent: a.totals.totalPaid,
            completionRate: a.totals.completionRate,
            avgCompletionTime: 0,
            activeExecutors: a.topWorkers?.length ?? 0,
          })
        } else {
          setAnalytics(null)
        }

        // Set active tasks (non-completed, non-cancelled)
        if (tasksResult.status === 'fulfilled') {
          const nonTerminal = tasksResult.value.data.filter(
            (t) => !['completed', 'cancelled', 'expired'].includes(t.status)
          )
          setActiveTasks(nonTerminal as Task[])
        }

        // Set pending submissions
        if (submissionsResult.status === 'fulfilled') {
          const mapped = submissionsResult.value.map((s) => ({
            ...s,
            executor: s.executor ? {
              id: s.executor.id,
              display_name: s.executor.display_name ?? null,
              reputation_score: s.executor.reputation_score ?? 0,
              avatar_url: null,
              wallet_address: s.executor.wallet_address ?? '',
            } : undefined,
          }))
          setPendingSubmissions(mapped as AgentSubmission[])
        }

        // Build recent activity from real data
        const activities: ActivityItem[] = []

        if (submissionsResult.status === 'fulfilled') {
          submissionsResult.value.forEach((s) => {
            activities.push({
              id: `sub-${s.id}`,
              type: 'submission_received',
              title: 'New evidence received',
              description: `${s.executor?.display_name ?? 'Worker'} submitted evidence for "${s.task?.title ?? 'task'}"`,
              timestamp: s.submitted_at,
              metadata: { taskId: s.task_id, submissionId: s.id },
            })
          })
        }

        if (tasksResult.status === 'fulfilled') {
          tasksResult.value.data.slice(0, 10).forEach((t) => {
            if (t.status === 'completed' && t.completed_at) {
              activities.push({
                id: `comp-${t.id}`,
                type: 'task_completed',
                title: 'Task completed',
                description: `"${t.title}" finished`,
                timestamp: t.completed_at,
                metadata: { taskId: t.id },
              })
            }
            activities.push({
              id: `created-${t.id}`,
              type: 'task_created',
              title: 'Task published',
              description: `"${t.title}" created`,
              timestamp: t.created_at,
              metadata: { taskId: t.id },
            })
          })
        }

        // Sort by timestamp descending, take top 10
        activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        setRecentActivity(activities.slice(0, 10))
      } catch (err) {
        console.error('Failed to load agent dashboard data:', err)
      }

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
            <h1 className="text-xl font-bold text-gray-900">{t('agentDashboard.title', 'Agent Dashboard')}</h1>
            <p className="text-sm text-gray-500">{t('agentDashboard.subtitle', 'Manage your tasks and review submissions')}</p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onCreateTask}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white text-sm font-medium rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {t('agentDashboard.createTask', 'Create Task')}
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Analytics Overview */}
      {/* ------------------------------------------------------------------ */}
      <section>
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-3">
          Platform Pulse
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label={t('metrics.registeredUsers', 'Registered Users')}
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
            label={t('metrics.activeWorkers', 'Active Workers')}
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
            label={t('metrics.activeAgents', 'Active Agents')}
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
            label={t('metrics.completedTasks', 'Completed Tasks')}
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
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-3">
            {t('agentDashboard.activitySummary', 'Activity Summary')}
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label={t('agentDashboard.tasksCreated', 'Tasks Created')}
              value={analytics.tasksCreated}
              subValue={`${analytics.tasksPending} ${t('agentDashboard.pending', 'pending')}`}
              icon={
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              }
            />
            <StatCard
              label={t('agentDashboard.completionRate', 'Completion Rate')}
              value={`${analytics.completionRate.toFixed(1)}%`}
              subValue={`${analytics.tasksCompleted} ${t('agentDashboard.completed', 'completed')}`}
              /* trend removed — no real historical data to compare */
              icon={
                <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <StatCard
              label={t('agentDashboard.totalSpent', 'Total Spent')}
              value={formatCurrency(analytics.totalSpent)}
              subValue={t('agentDashboard.thisMonth', 'This month')}
              icon={
                <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <StatCard
              label={t('agentDashboard.avgTime', 'Avg. Completion Time')}
              value={analytics.avgCompletionTime > 0 ? `${analytics.avgCompletionTime}h` : 'N/A'}
              subValue={`${analytics.activeExecutors} ${t('agentDashboard.activeExecutors', 'active workers')}`}
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
      {/* Agent On-Chain Reputation */}
      {/* ------------------------------------------------------------------ */}
      <AgentReputationCard agentId={agentId} />

      {/* ------------------------------------------------------------------ */}
      {/* Main Content Grid */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Active Tasks */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">{t('agentDashboard.activeTasks', 'Active Tasks')}</h2>
            <div className="flex items-center gap-1">
              {(['all', 'pending', 'in_progress'] as const).map((filter) => (
                <Pill
                  key={filter}
                  variant={activeTasksFilter === filter ? 'selected' : 'default'}
                  size="sm"
                  onClick={() => setActiveTasksFilter(filter)}
                >
                  {filter === 'all' ? t('common.all', 'All') : filter === 'pending' ? t('agentDashboard.pending', 'Pending') : t('tasks.inProgress', 'In Progress')}
                </Pill>
              ))}
            </div>
          </div>

          <div className="divide-y divide-zinc-200 dark:divide-zinc-800 max-h-80 overflow-y-auto">
            {filteredTasks.length === 0 ? (
              <div className="p-6 text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <p className="text-sm text-gray-500">{t('agentDashboard.noTasksFilter', 'No tasks match this filter')}</p>
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

          {/* "View all tasks" footer removed — no separate tasks list page for agents yet */}
        </section>

        {/* Pending Submissions */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-gray-900">{t('agentDashboard.pendingReview', 'Pending Review')}</h2>
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
                <div className="w-12 h-12 bg-zinc-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-sm text-zinc-700">{t('agentDashboard.noSubmissions', 'No pending submissions')}</p>
                <p className="text-xs text-zinc-500 mt-1">{t('agentDashboard.submissionsWillAppear', 'Submissions will appear here for review')}</p>
              </div>
            ) : (
              pendingSubmissions.map((submission) => (
                <PendingSubmissionItem
                  key={submission.id}
                  submission={submission}
                  onReview={() => onReviewSubmission?.(submission)}
                  onApproveAndRate={() => setRatingSubmission(submission)}
                />
              ))
            )}
          </div>

          {pendingSubmissions.length > 0 && (
            <div className="px-4 py-3 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between">
              <span className="text-xs text-zinc-600">
                {pendingSubmissions.filter((s) => s.auto_check_passed).length} {t('agentDashboard.passedAutoCheck', 'passed auto-check')}
              </span>
            </div>
          )}
        </section>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Quick Actions Bar */}
      {/* ------------------------------------------------------------------ */}
      <section className="bg-zinc-900 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-white font-medium">{t('agentDashboard.quickActions', 'Quick Actions')}</h3>
            <p className="text-zinc-300 text-sm">{t('agentDashboard.quickActionsDesc', 'Shortcuts for common tasks')}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onCreateTask}
              className="flex items-center gap-2 px-4 py-2 bg-white text-zinc-900 text-sm font-medium rounded-lg hover:bg-zinc-100 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {t('agentDashboard.newTask', 'New Task')}
            </button>
            <button
              onClick={() => pendingSubmissions[0] && onReviewSubmission?.(pendingSubmissions[0])}
              disabled={pendingSubmissions.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white text-sm font-medium rounded-lg hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              {t('agentDashboard.reviewNext', 'Review Next')}
            </button>
            {/* Reports button removed — no reports page exists yet */}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Recent Activity */}
      {/* ------------------------------------------------------------------ */}
      <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">{t('agentDashboard.recentActivity', 'Recent Activity')}</h2>
        </div>

        <div className="divide-y divide-zinc-200 dark:divide-zinc-800 px-4">
          {recentActivity.length === 0 ? (
            <div className="py-6 text-center">
              <p className="text-sm text-gray-500">{t('agentDashboard.noActivity', 'No recent activity')}</p>
            </div>
          ) : (
            recentActivity.map((activity) => (
              <ActivityFeedItem key={activity.id} activity={activity} />
            ))
          )}
        </div>

        {/* "View all activity" footer removed — no separate activity page exists yet */}
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Worker Rating Modal */}
      {/* ------------------------------------------------------------------ */}
      {ratingSubmission && ratingSubmission.executor && (
        <WorkerRatingModal
          taskId={ratingSubmission.task_id}
          taskTitle={ratingSubmission.task?.title || 'Task'}
          worker={{
            id: ratingSubmission.executor.id,
            display_name: ratingSubmission.executor.display_name,
            reputation_score: ratingSubmission.executor.reputation_score,
            avatar_url: ratingSubmission.executor.avatar_url,
            wallet_address: ratingSubmission.executor.wallet_address,
          }}
          proofTx={ratingSubmission.payment_tx}
          onClose={() => setRatingSubmission(null)}
          onSuccess={() => {
            setRatingSubmission(null)
          }}
        />
      )}
    </div>
  )
}

export default AgentDashboard
