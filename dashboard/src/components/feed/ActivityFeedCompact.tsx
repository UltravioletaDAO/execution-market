/**
 * ActivityFeedCompact Component
 *
 * Compact version of the activity feed for landing page / sidebar.
 * Shows last N events with a "View all activity →" link.
 */

import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { cn } from '../../lib/utils'
import { ActivityFeed } from './ActivityFeed'

export interface ActivityFeedCompactProps {
  /** Number of events to show (default 8) */
  limit?: number
  /** Additional CSS */
  className?: string
}

export function ActivityFeedCompact({ limit = 8, className }: ActivityFeedCompactProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div className={cn('flex flex-col', className)}>
      <ActivityFeed limit={limit} compact />

      {/* View all link */}
      <button
        onClick={() => navigate('/activity')}
        className={cn(
          'mt-3 self-center flex items-center gap-1.5',
          'text-sm font-medium transition-colors',
          'text-blue-600 hover:text-blue-700',
          'dark:text-blue-400 dark:hover:text-blue-300',
        )}
      >
        {t('feed.viewAll', 'View all activity')}
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  )
}

export default ActivityFeedCompact
