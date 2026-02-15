/**
 * ActivityFeedItem Component
 *
 * Single feed event card with icon, actor info, description, and timestamp.
 * Compact one-line design, expandable for details.
 */

import { memo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { cn } from '../../lib/utils'
import { formatRelativeTime } from '../../lib/formatRelativeTime'
import type { ActivityEvent, ActivityEventType } from '../../hooks/useActivityFeed'

// ---------------------------------------------------------------------------
// Event config
// ---------------------------------------------------------------------------

interface EventConfig {
  icon: string
  color: string
  bgColor: string
}

const EVENT_CONFIG: Record<ActivityEventType, EventConfig> = {
  task_created: {
    icon: '📝',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
  },
  task_accepted: {
    icon: '✅',
    color: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
  },
  task_completed: {
    icon: '🎉',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
  },
  feedback_given: {
    icon: '⭐',
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
  },
  worker_joined: {
    icon: '👋',
    color: 'text-teal-600 dark:text-teal-400',
    bgColor: 'bg-teal-50 dark:bg-teal-900/20',
  },
  dispute_opened: {
    icon: '⚠️',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
  },
  dispute_resolved: {
    icon: '⚖️',
    color: 'text-slate-600 dark:text-slate-400',
    bgColor: 'bg-slate-50 dark:bg-slate-800/40',
  },
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function truncateWallet(wallet: string): string {
  if (!wallet) return ''
  if (wallet.includes('.')) return wallet // ENS / basename
  if (wallet.length <= 12) return wallet
  return `${wallet.slice(0, 6)}…${wallet.slice(-4)}`
}

function formatBounty(usd: number): string {
  return `$${usd.toFixed(2)} USDC`
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface ActivityFeedItemProps {
  event: ActivityEvent
  compact?: boolean
  isNew?: boolean
}

export const ActivityFeedItem = memo(function ActivityFeedItem({
  event,
  compact = false,
  isNew = false,
}: ActivityFeedItemProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const config = EVENT_CONFIG[event.event_type] ?? EVENT_CONFIG.task_created

  const actorDisplay = event.actor_name || (event.actor_wallet ? truncateWallet(event.actor_wallet) : null)

  // Build description
  const description = buildDescription(event, actorDisplay, t)

  const handleActorClick = () => {
    if (event.actor_wallet) {
      navigate(`/profile/${event.actor_wallet}`)
    }
  }

  const handleTaskClick = () => {
    if (event.task_id) {
      navigate(`/?task=${event.task_id}`)
    }
  }

  return (
    <div
      className={cn(
        'group flex items-start gap-3 px-3 py-2.5 rounded-lg transition-all duration-300',
        'hover:bg-slate-50 dark:hover:bg-slate-800/50',
        isNew && 'animate-feed-in ring-1 ring-blue-300 dark:ring-blue-600 bg-blue-50/50 dark:bg-blue-900/10',
        compact && 'py-2 px-2',
      )}
    >
      {/* Icon */}
      <span
        className={cn(
          'flex-shrink-0 flex items-center justify-center rounded-full text-sm',
          compact ? 'w-7 h-7' : 'w-8 h-8',
          config.bgColor,
        )}
        aria-hidden
      >
        {config.icon}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className={cn(
          'text-sm text-slate-700 dark:text-slate-300 leading-snug',
          compact && 'text-xs',
        )}>
          {description}
        </p>

        {/* Task link + bounty on a second micro-line for non-compact */}
        {!compact && event.task_title && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">
            <button
              onClick={handleTaskClick}
              className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline transition-colors truncate"
            >
              {event.task_title}
            </button>
            {event.bounty_usd != null && event.bounty_usd > 0 && (
              <span className="ml-1.5 font-medium text-emerald-600 dark:text-emerald-400">
                — {formatBounty(event.bounty_usd)}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Timestamp */}
      <span
        className={cn(
          'flex-shrink-0 text-slate-400 dark:text-slate-500 whitespace-nowrap',
          compact ? 'text-[10px]' : 'text-xs',
        )}
        title={new Date(event.created_at).toLocaleString()}
      >
        {formatRelativeTime(event.created_at)}
      </span>
    </div>
  )
})

// ---------------------------------------------------------------------------
// Build description text per event type
// ---------------------------------------------------------------------------

function buildDescription(
  event: ActivityEvent,
  actorDisplay: string | null,
  t: (key: string, fallback: string, opts?: Record<string, unknown>) => string,
): React.ReactNode {
  const actor = actorDisplay ? (
    <span className="font-medium text-slate-900 dark:text-slate-100">
      {actorDisplay}
    </span>
  ) : null

  const taskSnippet = event.task_title ? (
    <span className="font-medium text-slate-800 dark:text-slate-200">
      &ldquo;{event.task_title.length > 50 ? event.task_title.slice(0, 47) + '…' : event.task_title}&rdquo;
    </span>
  ) : null

  const bountyTag =
    event.bounty_usd != null && event.bounty_usd > 0 ? (
      <span className="font-medium text-emerald-600 dark:text-emerald-400">
        {' '}— {formatBounty(event.bounty_usd)}
      </span>
    ) : null

  switch (event.event_type) {
    case 'task_created':
      return (
        <>
          {actor ?? t('feed.someone', 'Someone')}{' '}
          {t('feed.posted', 'posted')}{' '}
          {taskSnippet}
          {bountyTag}
        </>
      )
    case 'task_accepted':
      return (
        <>
          {actor ?? t('feed.aWorker', 'A worker')}{' '}
          {t('feed.accepted', 'accepted')}{' '}
          {taskSnippet}
        </>
      )
    case 'task_completed':
      return (
        <>
          {t('feed.taskCompleted', 'Task completed')}:{' '}
          {taskSnippet}
          {bountyTag}
        </>
      )
    case 'feedback_given': {
      const rating = (event.metadata as Record<string, unknown>)?.rating as number | undefined
      const stars = rating ? '⭐'.repeat(Math.min(rating, 5)) : '⭐⭐⭐⭐⭐'
      const target = event.target_name || (event.target_wallet ? truncateWallet(event.target_wallet) : null)
      return (
        <>
          {target ? (
            <span className="font-medium text-slate-900 dark:text-slate-100">{target}</span>
          ) : (
            t('feed.aWorker', 'A worker')
          )}{' '}
          {t('feed.received', 'received')}{' '}
          <span>{stars}</span>
          {actor && (
            <>
              {' '}{t('feed.from', 'from')}{' '}{actor}
            </>
          )}
        </>
      )
    }
    case 'worker_joined':
      return (
        <>
          {t('feed.newWorkerJoined', 'New worker joined')}:{' '}
          {actor ?? t('feed.anonymous', 'Anonymous')}
        </>
      )
    case 'dispute_opened':
      return (
        <>
          {t('feed.disputeOpened', 'Dispute opened on')}{' '}
          {taskSnippet ?? t('feed.aTask', 'a task')}
        </>
      )
    case 'dispute_resolved':
      return (
        <>
          {t('feed.disputeResolved', 'Dispute resolved for')}{' '}
          {taskSnippet ?? t('feed.aTask', 'a task')}
        </>
      )
    default:
      return (
        <>
          {actor} — {event.event_type}
        </>
      )
  }
}

export default ActivityFeedItem
