/**
 * TaskManagement - Manage tasks for AI agents
 *
 * Features:
 * - Tabs: Draft, Active, Completed, Cancelled
 * - Task cards with applicant count
 * - Quick actions: View Applicants, Cancel Task
 * - Filter and search
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import type { TaskStatus, TaskCategory, TaskApplication } from '../../types/database'
import type { TaskWithExecutor } from '../../services/types'
import { getAgentTasks, cancelTask } from '../../services/tasks'

// ============================================================================
// Types
// ============================================================================

interface TaskManagementProps {
  agentId: string
  onBack?: () => void
  onViewTask?: (task: TaskWithApplicants) => void
  onEditTask?: (task: TaskWithApplicants) => void
  onCreateTask?: () => void
  onViewApplicants?: (task: TaskWithApplicants, applicants: TaskApplicationWithExecutor[]) => void
}

interface TaskApplicationWithExecutor extends TaskApplication {
  executor?: {
    id: string
    display_name: string | null
    reputation_score: number
    avatar_url: string | null
    tasks_completed: number
  }
}

interface TaskWithApplicants extends TaskWithExecutor {
  applicants?: TaskApplicationWithExecutor[]
  applicant_count?: number
}

type TabKey = 'active' | 'pending' | 'completed' | 'cancelled'

// ============================================================================
// Constants
// ============================================================================

const TAB_CONFIG: { key: TabKey; i18nKey: string; statuses: TaskStatus[]; color: string }[] = [
  { key: 'active', i18nKey: 'taskMgmt.tabs.active', statuses: ['accepted', 'in_progress', 'submitted', 'verifying'], color: 'blue' },
  { key: 'pending', i18nKey: 'taskMgmt.tabs.published', statuses: ['published'], color: 'green' },
  { key: 'completed', i18nKey: 'taskMgmt.tabs.completed', statuses: ['completed'], color: 'gray' },
  { key: 'cancelled', i18nKey: 'taskMgmt.tabs.cancelled', statuses: ['cancelled', 'expired', 'disputed'], color: 'red' },
]

const STATUS_CONFIG: Record<TaskStatus, { i18nKey: string; className: string; dotColor: string }> = {
  published: { i18nKey: 'taskMgmt.status.published', className: 'bg-green-100 text-green-800', dotColor: 'bg-green-500' },
  accepted: { i18nKey: 'taskMgmt.status.accepted', className: 'bg-blue-100 text-blue-800', dotColor: 'bg-blue-500' },
  in_progress: { i18nKey: 'taskMgmt.status.inProgress', className: 'bg-yellow-100 text-yellow-800', dotColor: 'bg-yellow-500' },
  submitted: { i18nKey: 'taskMgmt.status.submitted', className: 'bg-purple-100 text-purple-800', dotColor: 'bg-purple-500' },
  verifying: { i18nKey: 'taskMgmt.status.verifying', className: 'bg-indigo-100 text-indigo-800', dotColor: 'bg-indigo-500' },
  completed: { i18nKey: 'taskMgmt.status.completed', className: 'bg-gray-100 text-gray-800', dotColor: 'bg-gray-500' },
  disputed: { i18nKey: 'taskMgmt.status.disputed', className: 'bg-red-100 text-red-800', dotColor: 'bg-red-500' },
  expired: { i18nKey: 'taskMgmt.status.expired', className: 'bg-gray-100 text-gray-500', dotColor: 'bg-gray-400' },
  cancelled: { i18nKey: 'taskMgmt.status.cancelled', className: 'bg-gray-100 text-gray-400', dotColor: 'bg-gray-300' },
}

// Category labels resolved via t() at render time (keys match categories.*)
const CATEGORY_I18N_KEYS: Record<TaskCategory, string> = {
  physical_presence: 'categories.physical_presence',
  knowledge_access: 'categories.knowledge_access',
  human_authority: 'categories.human_authority',
  simple_action: 'categories.simple_action',
  digital_physical: 'categories.digital_physical',
  data_processing: 'categories.data_processing',
  research: 'categories.research',
  content_generation: 'categories.content_generation',
  code_execution: 'categories.code_execution',
  api_integration: 'categories.api_integration',
  multi_step_workflow: 'categories.multi_step_workflow',
}

const CATEGORY_ICONS: Record<TaskCategory, string> = {
  physical_presence: 'M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z',
  knowledge_access: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
  human_authority: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  simple_action: 'M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11',
  digital_physical: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  data_processing: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
  research: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  content_generation: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
  code_execution: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
  api_integration: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1',
  multi_step_workflow: 'M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2',
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

function formatDeadline(deadline: string): { text: string; isUrgent: boolean; isExpired: boolean } {
  const date = new Date(deadline)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffMs < 0) {
    return { text: 'expired', isUrgent: false, isExpired: true }
  }
  if (diffHours < 1) {
    return { text: 'lessThan1h', isUrgent: true, isExpired: false }
  }
  if (diffHours < 24) {
    return { text: `${diffHours}h`, isUrgent: diffHours < 6, isExpired: false }
  }
  if (diffDays === 1) {
    return { text: '1d', isUrgent: false, isExpired: false }
  }
  return { text: `${diffDays}d`, isUrgent: false, isExpired: false }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('es-MX', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ============================================================================
// Sub-Components
// ============================================================================

function StatusBadge({ status }: { status: TaskStatus }) {
  const { t } = useTranslation()
  const config = STATUS_CONFIG[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full ${config.className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
      {t(config.i18nKey)}
    </span>
  )
}

function TaskCard({
  task,
  onView,
  onEdit,
  onCancel,
  onViewApplicants,
}: {
  task: TaskWithApplicants
  onView?: () => void
  onEdit?: () => void
  onCancel?: () => void
  onViewApplicants?: () => void
}) {
  const { t } = useTranslation()
  const [showActions, setShowActions] = useState(false)
  const deadline = formatDeadline(task.deadline)
  const canCancel = ['published', 'accepted'].includes(task.status)
  const hasApplicants = (task.applicant_count || 0) > 0
  const needsReview = task.status === 'submitted'

  return (
    <div className="bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-all">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            {/* Category icon */}
            <div className="p-2 bg-gray-100 rounded-lg flex-shrink-0">
              <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={CATEGORY_ICONS[task.category]} />
              </svg>
            </div>

            {/* Title and meta */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-medium text-gray-900 truncate">{task.title}</h3>
                <StatusBadge status={task.status} />
                {needsReview && (
                  <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full animate-pulse">
                    {t('taskMgmt.review', 'Review')}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                <span>{t(CATEGORY_I18N_KEYS[task.category])}</span>
                <span className="text-gray-300">|</span>
                <span className={deadline.isUrgent ? 'text-orange-600 font-medium' : deadline.isExpired ? 'text-red-500' : ''}>
                  {deadline.text}
                </span>
                {task.location_hint && (
                  <>
                    <span className="text-gray-300">|</span>
                    <span className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                      </svg>
                      <span className="truncate max-w-[150px]">{task.location_hint}</span>
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Bounty */}
          <div className="text-right flex-shrink-0">
            <p className="text-lg font-semibold text-green-600">{formatCurrency(task.bounty_usd)}</p>
            <p className="text-xs text-gray-400">USDC</p>
          </div>
        </div>

        {/* Instructions preview */}
        <p className="text-sm text-gray-600 mt-3 line-clamp-2">{task.instructions}</p>

        {/* Footer */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-4 text-sm">
            {/* Applicants */}
            {task.status === 'published' && (
              <button
                onClick={onViewApplicants}
                className={`flex items-center gap-1.5 ${hasApplicants ? 'text-blue-600 hover:text-blue-700' : 'text-gray-400'}`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>{task.applicant_count || 0} {t('taskMgmt.applicants', 'applicants')}</span>
              </button>
            )}

            {/* Executor info */}
            {task.executor_id && task.executor && (
              <div className="flex items-center gap-1.5 text-gray-600">
                <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-700 text-xs font-medium">
                    {(task.executor.display_name || 'T')[0].toUpperCase()}
                  </span>
                </div>
                <span>{task.executor.display_name || t('taskMgmt.worker', 'Worker')}</span>
              </div>
            )}

            {/* Created date */}
            <span className="text-gray-400">
              {t('taskMgmt.created', 'Created')} {formatDate(task.created_at)}
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 relative">
            <button
              onClick={onView}
              className="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
            >
              {t('taskMgmt.viewDetails', 'View details')}
            </button>

            {/* More actions dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowActions(!showActions)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                </svg>
              </button>

              {showActions && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowActions(false)}
                  />
                  <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                    {onEdit && ['published'].includes(task.status) && (
                      <button
                        onClick={() => {
                          setShowActions(false)
                          onEdit()
                        }}
                        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        {t('taskMgmt.editTask', 'Edit task')}
                      </button>
                    )}
                    {hasApplicants && (
                      <button
                        onClick={() => {
                          setShowActions(false)
                          onViewApplicants?.()
                        }}
                        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {t('taskMgmt.viewApplicants', 'View applicants')}
                      </button>
                    )}
                    {canCancel && (
                      <button
                        onClick={() => {
                          setShowActions(false)
                          onCancel?.()
                        }}
                        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        {t('taskMgmt.cancelTask', 'Cancel task')}
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setShowActions(false)
                        // Copy task ID
                        navigator.clipboard.writeText(task.id)
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                      {t('taskMgmt.copyId', 'Copy ID')}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function EmptyState({
  tab,
  onCreateTask,
}: {
  tab: TabKey
  onCreateTask?: () => void
}) {
  const { t } = useTranslation()
  const messages: Record<TabKey, { icon: string; titleKey: string; descKey: string }> = {
    active: {
      icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
      titleKey: 'taskMgmt.empty.activeTitle',
      descKey: 'taskMgmt.empty.activeDesc',
    },
    pending: {
      icon: 'M12 4v16m8-8H4',
      titleKey: 'taskMgmt.empty.pendingTitle',
      descKey: 'taskMgmt.empty.pendingDesc',
    },
    completed: {
      icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
      titleKey: 'taskMgmt.empty.completedTitle',
      descKey: 'taskMgmt.empty.completedDesc',
    },
    cancelled: {
      icon: 'M6 18L18 6M6 6l12 12',
      titleKey: 'taskMgmt.empty.cancelledTitle',
      descKey: 'taskMgmt.empty.cancelledDesc',
    },
  }

  const msg = messages[tab]

  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={msg.icon} />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">{t(msg.titleKey)}</h3>
      <p className="text-sm text-gray-500 mb-4">{t(msg.descKey)}</p>
      {tab === 'pending' && onCreateTask && (
        <button
          onClick={onCreateTask}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          {t('taskMgmt.createTask', 'Create Task')}
        </button>
      )}
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function TaskManagement({
  agentId,
  onBack,
  onViewTask,
  onEditTask,
  onCreateTask,
  onViewApplicants,
}: TaskManagementProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabKey>('active')
  const [tasks, setTasks] = useState<TaskWithApplicants[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<TaskCategory | 'all'>('all')
  const [cancellingTaskId, setCancellingTaskId] = useState<string | null>(null)

  // Load tasks from real API
  useEffect(() => {
    const loadTasks = async () => {
      setLoading(true)

      try {
        const result = await getAgentTasks(agentId, { limit: 100 })
        // Map API response to component's expected shape
        const mapped: TaskWithApplicants[] = result.data.map((t) => ({
          ...t,
          applicant_count: 0,
          applicants: [],
        }))
        setTasks(mapped)
      } catch (err) {
        console.error('Failed to load tasks:', err)
        setTasks([])
      }

      setLoading(false)
    }

    loadTasks()
  }, [agentId])

  // Filter tasks by tab, search, and category
  const filteredTasks = useMemo(() => {
    const tabConfig = TAB_CONFIG.find((t) => t.key === activeTab)
    if (!tabConfig) return []

    return tasks.filter((task) => {
      // Tab filter
      if (!tabConfig.statuses.includes(task.status)) return false

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (
          !task.title.toLowerCase().includes(query) &&
          !task.instructions.toLowerCase().includes(query) &&
          !(task.location_hint || '').toLowerCase().includes(query)
        ) {
          return false
        }
      }

      // Category filter
      if (categoryFilter !== 'all' && task.category !== categoryFilter) {
        return false
      }

      return true
    })
  }, [tasks, activeTab, searchQuery, categoryFilter])

  // Tab counts
  const tabCounts = useMemo(() => {
    const counts: Record<TabKey, number> = {
      active: 0,
      pending: 0,
      completed: 0,
      cancelled: 0,
    }

    tasks.forEach((task) => {
      TAB_CONFIG.forEach((tab) => {
        if (tab.statuses.includes(task.status)) {
          counts[tab.key]++
        }
      })
    })

    return counts
  }, [tasks])

  // Cancel task handler
  const handleCancelTask = useCallback(async (taskId: string) => {
    if (!confirm(t('taskMgmt.confirmCancel', 'Are you sure you want to cancel this task? The escrow will be returned.'))) {
      return
    }

    setCancellingTaskId(taskId)

    try {
      await cancelTask({ taskId, agentId, reason: 'Cancelled by agent' })
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: 'cancelled' as TaskStatus } : t))
      )
    } catch (err) {
      console.error('Failed to cancel task:', err)
      alert(t('taskMgmt.cancelError', 'Error cancelling task. Try again.'))
    }

    setCancellingTaskId(null)
  }, [agentId])

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded w-48 animate-pulse" />
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-gray-200 rounded w-24 animate-pulse" />
          ))}
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
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
            <h1 className="text-xl font-bold text-gray-900">{t('taskMgmt.title', 'Manage Tasks')}</h1>
            <p className="text-sm text-gray-500">{tasks.length} {t('taskMgmt.totalTasks', 'total tasks')}</p>
          </div>
        </div>

        {onCreateTask && (
          <button
            onClick={onCreateTask}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {t('taskMgmt.newTask', 'New Task')}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {TAB_CONFIG.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {t(tab.i18nKey)}
              {tabCounts[tab.key] > 0 && (
                <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                  activeTab === tab.key ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {tabCounts[tab.key]}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('taskMgmt.searchPlaceholder', 'Search tasks...')}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Category filter */}
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as TaskCategory | 'all')}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
        >
          <option value="all">{t('taskMgmt.allCategories', 'All categories')}</option>
          {Object.entries(CATEGORY_I18N_KEYS).map(([value, key]) => (
            <option key={value} value={value}>
              {t(key)}
            </option>
          ))}
        </select>
      </div>

      {/* Task List */}
      <div className="space-y-4">
        {filteredTasks.length === 0 ? (
          <EmptyState tab={activeTab} onCreateTask={onCreateTask} />
        ) : (
          filteredTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onView={() => onViewTask?.(task)}
              onEdit={() => onEditTask?.(task)}
              onCancel={() => handleCancelTask(task.id)}
              onViewApplicants={() => onViewApplicants?.(task, task.applicants || [])}
            />
          ))
        )}
      </div>

      {/* Cancelling overlay */}
      {cancellingTaskId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 text-center">
            <svg className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-gray-700">{t('taskMgmt.cancelling', 'Cancelling task...')}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default TaskManagement
