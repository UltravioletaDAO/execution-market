/**
 * Execution Market: Task Card Component
 * Displays a task summary with category, status, bounty, and deadline
 * Fully internationalized using i18n translations
 */

import { memo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import type { Task, TaskStatus } from '../types/database'
import { useTranslation as useCustomTranslation } from '../i18n/hooks/useTranslation'
import { getWorldIdBountyThreshold } from '../hooks/usePlatformConfig'
import { CATEGORY_ICONS } from '../constants/categories'
import { getNetworkDisplayName } from '../utils/blockchain'
import { NETWORK_BY_KEY, getNetworkLogo } from '../config/networks'
import { AgentMiniCard } from './agents/AgentMiniCard'

interface TaskCardProps {
  task: Task
  onClick?: () => void
}

// Status colors (Tailwind classes)
const STATUS_COLORS: Record<TaskStatus, string> = {
  published: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  accepted: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  in_progress: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  submitted: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  verifying: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
  completed: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  disputed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  expired: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500',
  cancelled: 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500',
}

export const TaskCard = memo(function TaskCard({ task, onClick }: TaskCardProps) {
  const { t } = useTranslation()
  const { formatCurrency, formatTimeRemaining } = useCustomTranslation()

  const isExpiringSoon =
    new Date(task.deadline).getTime() - Date.now() < 24 * 60 * 60 * 1000

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        onClick?.()
      }
    },
    [onClick]
  )

  // Get translated category label
  const categoryLabel = t(`tasks.categories.${task.category}`)

  // Get translated status label
  const statusLabel = t(`tasks.statuses.${task.status}`)

  // Format deadline
  const deadlineText = formatTimeRemaining(task.deadline)

  // Format creation date (YYYY-MM-DD HH:MM)
  const createdDate = task.created_at
    ? new Date(task.created_at).toISOString().slice(0, 16).replace('T', ' ')
    : ''

  // Format bounty
  const bountyText = formatCurrency(task.bounty_usd)

  return (
    <article
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm transition-all cursor-pointer"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden="true">
            {CATEGORY_ICONS[task.category]}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {categoryLabel}
          </span>
        </div>
        <span
          className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[task.status]}`}
        >
          {statusLabel}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2 line-clamp-2">
        {task.title}
      </h3>

      {/* Instructions preview */}
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
        {task.instructions}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
        {/* Bounty */}
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-green-600 dark:text-green-400">
            {bountyText}
          </span>
          <div className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
            <span>{task.payment_token}</span>
            {task.payment_network && (
              <>
                <span>on</span>
                <img
                  src={getNetworkLogo(task.payment_network)}
                  alt={`${getNetworkDisplayName(task.payment_network)} logo`}
                  className="w-4 h-4 rounded-full"
                  onError={(e) => {
                    // Fallback: show network name
                    const target = e.target as HTMLImageElement
                    target.style.display = 'none'
                    const fallback = target.nextElementSibling as HTMLSpanElement
                    if (fallback) {
                      fallback.style.display = 'inline'
                    }
                  }}
                />
                <span className="hidden">
                  {getNetworkDisplayName(task.payment_network)}
                </span>
                <span className="font-medium text-gray-600 dark:text-gray-400">
                  {getNetworkDisplayName(task.payment_network)}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Deadline */}
        <div
          className={`flex items-center gap-1 text-sm ${
            isExpiringSoon
              ? 'text-orange-600 dark:text-orange-400'
              : 'text-gray-500 dark:text-gray-400'
          }`}
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{deadlineText}</span>
        </div>
        {createdDate && (
          <span className="text-xs text-gray-400 dark:text-gray-500" title="Created at">
            {createdDate}
          </span>
        )}
      </div>

      {/* Location badge */}
      {task.location_hint && (
        <div className="mt-3 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path
              fillRule="evenodd"
              d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
              clipRule="evenodd"
            />
          </svg>
          <span className="truncate">{task.location_hint}</span>
        </div>
      )}

      {/* Reputation requirement */}
      {task.min_reputation > 0 && (
        <div className="mt-2 flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          <span>{t('tasks.requiresReputation', { score: task.min_reputation })}</span>
        </div>
      )}

      {/* World ID required badge */}
      {task.bounty_usd >= getWorldIdBountyThreshold() && (
        <div className="mt-2 flex items-center">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {t('worldId.required', 'Requires World ID')}
          </span>
        </div>
      )}

      {/* Skills required */}
      {task.skills_required && task.skills_required.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {task.skills_required.map((skill) => (
            <span
              key={skill}
              className="px-1.5 py-0.5 text-2xs font-medium rounded-full bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400"
            >
              {skill}
            </span>
          ))}
        </div>
      )}

      {/* Task poster */}
      <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        <AgentMiniCard walletAddress={task.agent_id} clickable={false} erc8004AgentIdOverride={task.erc8004_agent_id} agentName={task.agent_name} />
      </div>
    </article>
  )
})

export default TaskCard
