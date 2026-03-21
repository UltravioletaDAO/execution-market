/**
 * ActivityFeed Component
 *
 * Full activity feed with rich TaskFeedCards showing both participants,
 * transactions, scores, and task details.
 *
 * Two modes:
 *  - 'public'        (default) — compact read-only cards, no filters/realtime
 *  - 'authenticated' — filter tabs, load-more, realtime, full rich cards
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/utils'
import { useTaskFeedCards } from '../../hooks/useTaskFeedCards'
import type { ActivityFilter, ActivityFeedMode } from '../../hooks/useActivityFeed'
import { TaskFeedCard } from './TaskFeedCard'
import { Skeleton } from '../ui/Skeleton'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActivityFeedProps {
  /** Max events per page */
  limit?: number
  /** Hide filter tabs and show minimal compact layout */
  compact?: boolean
  /**
   * 'public'        — lightweight, no realtime, anonymous-safe (landing page)
   * 'authenticated' — full features, realtime, filter tabs, load-more
   */
  mode?: ActivityFeedMode
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

export function ActivityFeed({
  limit,
  compact = false,
  mode = 'public',
  className,
}: ActivityFeedProps) {
  const { t } = useTranslation()
  const isAuthenticated = mode === 'authenticated'

  // Filters only available in authenticated (full) mode
  const [filter, setFilter] = useState<ActivityFilter>('all')

  const { cards, loading, error, hasMore, loadMore, newCardCount, clearNewCards } =
    useTaskFeedCards({ limit, filter, mode })

  // Track which card IDs were present on first render to highlight new ones
  const initialIds = useRef<Set<string>>(new Set())
  const [seenIds, setSeenIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!loading && cards.length > 0 && initialIds.current.size === 0) {
      const ids = new Set(cards.map((c) => c.id))
      initialIds.current = ids
      setSeenIds(ids)
    }
  }, [loading, cards])

  // When user clicks "N new" banner, clear counter and mark all as seen
  const handleShowNew = useCallback(() => {
    clearNewCards()
    setSeenIds(new Set(cards.map((c) => c.id)))
  }, [clearNewCards, cards])

  // Derive display flags
  const showFilters = isAuthenticated && !compact
  const showLoadMore = isAuthenticated && hasMore && !compact
  const showNewBanner = isAuthenticated && newCardCount > 0

  // ------------------------------------------------------------------
  // Loading skeleton
  // ------------------------------------------------------------------
  if (loading && cards.length === 0) {
    return (
      <div className={cn('space-y-3', className)}>
        {showFilters && <FilterTabsSkeleton />}
        {Array.from({ length: compact ? 3 : 5 }).map((_, i) => (
          <FeedCardSkeleton key={i} compact={compact} />
        ))}
      </div>
    )
  }

  // ------------------------------------------------------------------
  // Error state
  // ------------------------------------------------------------------
  if (error && cards.length === 0) {
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
  if (!loading && cards.length === 0) {
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
      {/* Filter tabs (authenticated full-mode only) */}
      {showFilters && (
        <div className="flex items-center gap-1 mb-4 overflow-x-auto pb-1 -mx-1 px-1">
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

      {/* New events banner (authenticated only) */}
      {showNewBanner && (
        <button
          onClick={handleShowNew}
          className={cn(
            'mb-3 py-1.5 px-3 rounded-lg text-xs font-medium text-center transition-colors',
            'bg-blue-50 text-blue-700 hover:bg-blue-100',
            'dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50',
          )}
        >
          {t('feed.newEvents', '{{count}} new events', { count: newCardCount })}
        </button>
      )}

      {/* Cards list */}
      <div className="space-y-3">
        {cards.map((card) => (
          <TaskFeedCard
            key={card.id}
            data={card}
            compact={compact}
            isNew={
              isAuthenticated &&
              !seenIds.has(card.id) &&
              initialIds.current.size > 0
            }
          />
        ))}
      </div>

      {/* Load more (authenticated only) */}
      {showLoadMore && (
        <button
          onClick={loadMore}
          disabled={loading}
          className={cn(
            'mt-4 py-2 px-4 rounded-lg text-sm font-medium transition-colors self-center',
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
    <div className="flex items-center gap-2 mb-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} width={i === 0 ? 50 : 70} height={28} className="rounded-full" />
      ))}
    </div>
  )
}

function FeedCardSkeleton({ compact }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex items-center gap-3 px-3 py-2">
        <Skeleton circle width={28} height={28} />
        <div className="flex-1 space-y-1">
          <Skeleton height={14} width="80%" />
        </div>
        <Skeleton height={12} width={40} />
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="px-4 py-2 bg-slate-50 dark:bg-slate-800/50">
        <Skeleton height={20} width={120} className="rounded-full" />
      </div>
      <div className="flex p-4 gap-4">
        <div className="flex flex-col items-center gap-2 w-28">
          <Skeleton circle width={48} height={48} />
          <Skeleton height={12} width={60} />
          <Skeleton height={10} width={40} />
        </div>
        <div className="flex-1 space-y-2">
          <Skeleton height={16} width="70%" />
          <Skeleton height={12} width="40%" />
          <Skeleton height={10} width="60%" />
        </div>
        <div className="flex flex-col items-center gap-2 w-28">
          <Skeleton circle width={48} height={48} />
          <Skeleton height={12} width={60} />
          <Skeleton height={10} width={40} />
        </div>
      </div>
    </div>
  )
}

export default ActivityFeed
