/**
 * ActivityFeed Component
 *
 * Full activity feed with filter tabs, real-time updates, pagination.
 * Supports compact mode for embedding in sidebar/landing.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/utils'
import { useActivityFeed, type ActivityFilter } from '../../hooks/useActivityFeed'
import { ActivityFeedItem } from './ActivityFeedItem'
import { Skeleton } from '../ui/Skeleton'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActivityFeedProps {
  /** Max events per page */
  limit?: number
  /** Hide filter tabs and show minimal layout */
  compact?: boolean
  /** Additional CSS */
  className?: string
}

// ---------------------------------------------------------------------------
// Filter tab config
// ---------------------------------------------------------------------------

interface FilterTab {
  key: ActivityFilter
  labelKey: string
  fallback: string
  icon: string
}

const TABS: FilterTab[] = [
  { key: 'all', labelKey: 'feed.filterAll', fallback: 'All', icon: '📋' },
  { key: 'tasks', labelKey: 'feed.filterTasks', fallback: 'Tasks', icon: '📝' },
  { key: 'reputation', labelKey: 'feed.filterReputation', fallback: 'Reputation', icon: '⭐' },
  { key: 'workers', labelKey: 'feed.filterWorkers', fallback: 'Workers', icon: '👋' },
]

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ActivityFeed({ limit, compact = false, className }: ActivityFeedProps) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<ActivityFilter>('all')

  const { events, loading, error, hasMore, loadMore, newEventCount, clearNewEvents } =
    useActivityFeed({ limit, filter, realtime: true })

  // Track which event IDs were present on first render so we can highlight new ones
  const initialIds = useRef<Set<string>>(new Set())
  const [seenIds, setSeenIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!loading && events.length > 0 && initialIds.current.size === 0) {
      const ids = new Set(events.map((e) => e.id))
      initialIds.current = ids
      setSeenIds(ids)
    }
  }, [loading, events])

  // When user clicks "N new events" banner, clear counter and mark all as seen
  const handleShowNew = useCallback(() => {
    clearNewEvents()
    setSeenIds(new Set(events.map((e) => e.id)))
  }, [clearNewEvents, events])

  // ------------------------------------------------------------------
  // Loading skeleton
  // ------------------------------------------------------------------
  if (loading && events.length === 0) {
    return (
      <div className={cn('space-y-2', className)}>
        {!compact && <FilterTabsSkeleton />}
        {Array.from({ length: compact ? 5 : 8 }).map((_, i) => (
          <FeedItemSkeleton key={i} compact={compact} />
        ))}
      </div>
    )
  }

  // ------------------------------------------------------------------
  // Error state
  // ------------------------------------------------------------------
  if (error && events.length === 0) {
    return (
      <div className={cn('text-center py-8', className)}>
        <p className="text-sm text-red-500 dark:text-red-400">
          {t('feed.error', 'Could not load activity feed.')}
        </p>
      </div>
    )
  }

  // ------------------------------------------------------------------
  // Empty state
  // ------------------------------------------------------------------
  if (!loading && events.length === 0) {
    return (
      <div className={cn('text-center py-10', className)}>
        <span className="text-4xl">🦗</span>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          {t('feed.empty', 'No activity yet. Be the first!')}
        </p>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Filter tabs (full mode only) */}
      {!compact && (
        <div className="flex items-center gap-1 mb-3 overflow-x-auto pb-1 -mx-1 px-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors whitespace-nowrap',
                filter === tab.key
                  ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700',
              )}
            >
              <span aria-hidden>{tab.icon}</span>
              {t(tab.labelKey, tab.fallback)}
            </button>
          ))}
        </div>
      )}

      {/* New events banner */}
      {newEventCount > 0 && (
        <button
          onClick={handleShowNew}
          className={cn(
            'mb-2 py-1.5 px-3 rounded-lg text-xs font-medium text-center transition-colors',
            'bg-blue-50 text-blue-700 hover:bg-blue-100',
            'dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50',
          )}
        >
          {t('feed.newEvents', '{{count}} new events', { count: newEventCount })}
        </button>
      )}

      {/* Events list */}
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {events.map((event) => (
          <ActivityFeedItem
            key={event.id}
            event={event}
            compact={compact}
            isNew={!seenIds.has(event.id) && initialIds.current.size > 0}
          />
        ))}
      </div>

      {/* Load more */}
      {hasMore && !compact && (
        <button
          onClick={loadMore}
          disabled={loading}
          className={cn(
            'mt-3 py-2 px-4 rounded-lg text-sm font-medium transition-colors self-center',
            'bg-slate-100 text-slate-700 hover:bg-slate-200',
            'dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700',
            'disabled:opacity-50',
          )}
        >
          {loading
            ? t('common.loading', 'Loading...')
            : t('feed.loadMore', 'Load more')}
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skeleton helpers
// ---------------------------------------------------------------------------

function FilterTabsSkeleton() {
  return (
    <div className="flex items-center gap-2 mb-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} width={i === 0 ? 50 : 70} height={28} className="rounded-full" />
      ))}
    </div>
  )
}

function FeedItemSkeleton({ compact }: { compact?: boolean }) {
  return (
    <div className={cn('flex items-start gap-3', compact ? 'py-2 px-2' : 'py-2.5 px-3')}>
      <Skeleton circle width={compact ? 28 : 32} height={compact ? 28 : 32} />
      <div className="flex-1 space-y-1.5">
        <Skeleton height={14} width="80%" />
        {!compact && <Skeleton height={12} width="50%" />}
      </div>
      <Skeleton height={12} width={40} />
    </div>
  )
}

export default ActivityFeed
