import { useState, useEffect, forwardRef, memo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAvailableTasks } from '../../hooks/useTasks'
import { useAuth } from '../../context/AuthContext'
import { CategoryFilter } from '../TaskList'
import { TaskDetailPanel } from './TaskDetailPanel'
import { TaskApplicationModal } from '../TaskApplicationModal'
import { getMyApplicationTaskIds } from '../../services/tasks'
import type { Task, TaskCategory } from '../../types/database'
import { useTranslation as useCustomTranslation } from '../../i18n/hooks/useTranslation'
import { CATEGORY_ICONS } from '../../constants/categories'

interface PublicTaskBrowserProps {
  onAuthRequired: () => void
}

// Inline job card that shows bounty prominently with Apply button
const JobCard = memo(function JobCard({ task, onClick, hasApplied }: { task: Task; onClick: () => void; hasApplied?: boolean }) {
  const { t } = useTranslation()
  const { formatCurrency, formatTimeRemaining } = useCustomTranslation()

  const deadlineText = formatTimeRemaining(task.deadline)
  const isExpiring = new Date(task.deadline).getTime() - Date.now() < 24 * 60 * 60 * 1000
  const isExpired = task.status === 'expired'

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        onClick()
      }
    },
    [onClick]
  )

  return (
    <article
      className="bg-white rounded-xl border border-gray-200 hover:border-emerald-300 hover:shadow-md transition-all cursor-pointer group"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <div className="p-4">
        {/* Top row: category + deadline */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <span>{CATEGORY_ICONS[task.category]}</span>
            <span>{t(`tasks.categories.${task.category}`)}</span>
          </div>
          <span className={`text-xs ${isExpiring ? 'text-orange-500 font-medium' : 'text-gray-400'}`}>
            {deadlineText}
          </span>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-gray-900 mb-1.5 line-clamp-2 group-hover:text-emerald-700 transition-colors">
          {task.title}
        </h3>

        {/* Instructions preview */}
        <p className="text-sm text-gray-500 mb-3 line-clamp-2">
          {task.instructions}
        </p>

        {/* Location if available */}
        {task.location_hint && (
          <div className="flex items-center gap-1 text-xs text-gray-400 mb-3">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            <span className="truncate">{task.location_hint}</span>
          </div>
        )}

        {/* Bottom: bounty + apply CTA */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <div className="text-xl font-black text-emerald-600">
            {formatCurrency(task.bounty_usd)}
          </div>
          {hasApplied ? (
            <span className="px-4 py-1.5 text-sm font-semibold rounded-lg bg-blue-100 text-blue-700">
              {t('tasks.applied', 'Applied')}
            </span>
          ) : (
            <span className={`px-4 py-1.5 text-sm font-semibold rounded-lg transition-colors ${
              isExpired
                ? 'bg-gray-200 text-gray-600'
                : 'bg-emerald-600 text-white group-hover:bg-emerald-500'
            }`}>
              {isExpired ? t('tasks.expired', 'Expired') : t('tasks.apply', 'Apply')}
            </span>
          )}
        </div>
      </div>
    </article>
  )
})

export const PublicTaskBrowser = forwardRef<HTMLElement, PublicTaskBrowserProps>(
  function PublicTaskBrowser({ onAuthRequired }, ref) {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const { isAuthenticated, executor } = useAuth()
    const [category, setCategory] = useState<TaskCategory | null>(null)
    const [selectedTask, setSelectedTask] = useState<Task | null>(null)
    const [applyingTask, setApplyingTask] = useState<Task | null>(null)

    const { tasks, loading, error, refetch, removeTask } = useAvailableTasks({
      category: category ?? undefined,
      includeExpiredFallback: true,
      executorId: executor?.id,
    })

    // Track which tasks the current executor has already applied to
    const [appliedTaskIds, setAppliedTaskIds] = useState<Set<string>>(new Set())
    useEffect(() => {
      if (!executor?.id) return
      getMyApplicationTaskIds(executor.id).then(setAppliedTaskIds)
    }, [executor?.id])

    const handleTaskClick = (task: Task) => {
      setSelectedTask(task)
    }

    const handleApply = () => {
      if (!isAuthenticated || !executor) {
        setSelectedTask(null)
        onAuthRequired()
      } else if (selectedTask) {
        setApplyingTask(selectedTask)
        setSelectedTask(null)
      }
    }

    const handleApplicationSuccess = () => {
      // Update applied IDs + remove from grid, but do NOT close modal or navigate.
      // The modal's ApplicationResultView shows the success/World ID upsell screen
      // and lets the user dismiss it via "View my tasks" or "Close".
      if (applyingTask) {
        setAppliedTaskIds(prev => new Set(prev).add(applyingTask.id))
        removeTask(applyingTask.id)
      }
      refetch()
    }

    return (
      <section ref={ref} className="py-8">
        {/* Section header with count */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <h2 className="text-xl md:text-2xl font-black text-gray-900">
              {t('landing.availableJobs', 'Available Jobs')}
            </h2>
            {!loading && tasks.length > 0 && (
              <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-700 text-sm font-bold rounded-full">
                {tasks.length}
              </span>
            )}
          </div>
        </div>

        {/* Category filter */}
        <div className="mb-5 overflow-x-auto pb-1 -mx-4 px-4">
          <CategoryFilter selected={category} onChange={setCategory} />
        </div>

        {/* Task grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 animate-pulse">
                <div className="flex justify-between mb-3">
                  <div className="w-20 h-3 bg-gray-200 rounded" />
                  <div className="w-16 h-3 bg-gray-200 rounded" />
                </div>
                <div className="w-3/4 h-5 bg-gray-200 rounded mb-2" />
                <div className="w-full h-4 bg-gray-200 rounded mb-1" />
                <div className="w-2/3 h-4 bg-gray-200 rounded mb-4" />
                <div className="flex justify-between pt-3 border-t border-gray-100">
                  <div className="w-16 h-6 bg-gray-200 rounded" />
                  <div className="w-20 h-8 bg-gray-200 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-orange-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">
              {t('tasks.loadError', 'Unable to load jobs right now')}
            </h3>
            <p className="text-gray-500 text-sm mb-4">
              {t('tasks.loadErrorHint', 'Please try again in a moment')}
            </p>
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-500 transition-colors"
            >
              {t('common.retry', 'Retry')}
            </button>
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">{t('tasks.noTasks', 'No tasks available')}</h3>
            <p className="text-gray-500 text-sm">{t('tasks.emptyHint', 'Check back soon for new jobs')}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tasks.map((task) => (
              <JobCard key={task.id} task={task} onClick={() => handleTaskClick(task)} hasApplied={appliedTaskIds.has(task.id)} />
            ))}
          </div>
        )}

        {/* Modals */}
        {selectedTask && (
          <TaskDetailPanel
            task={selectedTask}
            isAuthenticated={isAuthenticated}
            onClose={() => setSelectedTask(null)}
            onApply={handleApply}
          />
        )}

        {applyingTask && (
          <TaskApplicationModal
            task={applyingTask}
            hasAlreadyApplied={appliedTaskIds.has(applyingTask.id)}
            onClose={() => setApplyingTask(null)}
            onSuccess={handleApplicationSuccess}
          />
        )}
      </section>
    )
  }
)
