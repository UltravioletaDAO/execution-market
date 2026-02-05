/**
 * NotificationItem Component
 *
 * Single notification display with:
 * - Icon by type (task, payment, system)
 * - Title and message
 * - Time ago
 * - Action button if applicable
 */

import { useCallback, type MouseEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { Notification, NotificationType } from '../../types/notification'

// ============================================================================
// Icon Components
// ============================================================================

function TaskNearbyIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  )
}

function TaskApprovedIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function TaskRejectedIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function PaymentIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function DisputeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  )
}

function TaskAssignedIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
      />
    </svg>
  )
}

function TaskExpiredIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function ReminderIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
      />
    </svg>
  )
}

function ReputationIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
      />
    </svg>
  )
}

function SystemIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function AchievementIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  )
}

// ============================================================================
// Configuration
// ============================================================================

interface TypeConfig {
  bgColor: string
  iconColor: string
  darkBgColor: string
  darkIconColor: string
  Icon: React.FC
}

const NOTIFICATION_CONFIG: Record<NotificationType, TypeConfig> = {
  task_nearby: {
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600',
    darkBgColor: 'dark:bg-blue-900/30',
    darkIconColor: 'dark:text-blue-400',
    Icon: TaskNearbyIcon,
  },
  task_approved: {
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600',
    darkBgColor: 'dark:bg-green-900/30',
    darkIconColor: 'dark:text-green-400',
    Icon: TaskApprovedIcon,
  },
  task_rejected: {
    bgColor: 'bg-red-100',
    iconColor: 'text-red-600',
    darkBgColor: 'dark:bg-red-900/30',
    darkIconColor: 'dark:text-red-400',
    Icon: TaskRejectedIcon,
  },
  payment_received: {
    bgColor: 'bg-emerald-100',
    iconColor: 'text-emerald-600',
    darkBgColor: 'dark:bg-emerald-900/30',
    darkIconColor: 'dark:text-emerald-400',
    Icon: PaymentIcon,
  },
  payment_pending: {
    bgColor: 'bg-yellow-100',
    iconColor: 'text-yellow-600',
    darkBgColor: 'dark:bg-yellow-900/30',
    darkIconColor: 'dark:text-yellow-400',
    Icon: PaymentIcon,
  },
  dispute_opened: {
    bgColor: 'bg-amber-100',
    iconColor: 'text-amber-600',
    darkBgColor: 'dark:bg-amber-900/30',
    darkIconColor: 'dark:text-amber-400',
    Icon: DisputeIcon,
  },
  dispute_update: {
    bgColor: 'bg-amber-100',
    iconColor: 'text-amber-600',
    darkBgColor: 'dark:bg-amber-900/30',
    darkIconColor: 'dark:text-amber-400',
    Icon: DisputeIcon,
  },
  dispute_resolved: {
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600',
    darkBgColor: 'dark:bg-green-900/30',
    darkIconColor: 'dark:text-green-400',
    Icon: DisputeIcon,
  },
  task_assigned: {
    bgColor: 'bg-indigo-100',
    iconColor: 'text-indigo-600',
    darkBgColor: 'dark:bg-indigo-900/30',
    darkIconColor: 'dark:text-indigo-400',
    Icon: TaskAssignedIcon,
  },
  task_expired: {
    bgColor: 'bg-gray-100',
    iconColor: 'text-gray-500',
    darkBgColor: 'dark:bg-gray-800',
    darkIconColor: 'dark:text-gray-400',
    Icon: TaskExpiredIcon,
  },
  task_reminder: {
    bgColor: 'bg-orange-100',
    iconColor: 'text-orange-600',
    darkBgColor: 'dark:bg-orange-900/30',
    darkIconColor: 'dark:text-orange-400',
    Icon: ReminderIcon,
  },
  reputation_change: {
    bgColor: 'bg-violet-100',
    iconColor: 'text-violet-600',
    darkBgColor: 'dark:bg-violet-900/30',
    darkIconColor: 'dark:text-violet-400',
    Icon: ReputationIcon,
  },
  system: {
    bgColor: 'bg-slate-100',
    iconColor: 'text-slate-600',
    darkBgColor: 'dark:bg-slate-800',
    darkIconColor: 'dark:text-slate-400',
    Icon: SystemIcon,
  },
  achievement: {
    bgColor: 'bg-purple-100',
    iconColor: 'text-purple-600',
    darkBgColor: 'dark:bg-purple-900/30',
    darkIconColor: 'dark:text-purple-400',
    Icon: AchievementIcon,
  },
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatRelativeTime(dateStr: string, locale: string = 'es'): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (locale === 'es') {
    if (diffMins < 1) return 'Ahora mismo'
    if (diffMins < 60) return `hace ${diffMins}m`
    if (diffHours < 24) return `hace ${diffHours}h`
    if (diffDays === 1) return 'Ayer'
    if (diffDays < 7) return `hace ${diffDays}d`
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
  }

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })
}

// ============================================================================
// Props
// ============================================================================

export interface NotificationItemProps {
  notification: Notification
  onClick?: (notification: Notification) => void
  onAction?: (notification: Notification) => void
  onMarkAsRead?: (id: string) => void
  onDelete?: (id: string) => void
  showActions?: boolean
  compact?: boolean
  className?: string
  style?: React.CSSProperties
}

// ============================================================================
// Component
// ============================================================================

export function NotificationItem({
  notification,
  onClick,
  onAction,
  onMarkAsRead,
  onDelete,
  showActions = false,
  compact = false,
  className = '',
  style,
}: NotificationItemProps) {
  const { i18n, t } = useTranslation()
  const config = NOTIFICATION_CONFIG[notification.type] || NOTIFICATION_CONFIG.system
  const { Icon } = config

  const handleClick = useCallback(() => {
    onClick?.(notification)
  }, [notification, onClick])

  const handleAction = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      onAction?.(notification)
    },
    [notification, onAction]
  )

  const handleMarkAsRead = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      onMarkAsRead?.(notification.id)
    },
    [notification.id, onMarkAsRead]
  )

  const handleDelete = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      onDelete?.(notification.id)
    },
    [notification.id, onDelete]
  )

  if (compact) {
    return (
      <button
        onClick={handleClick}
        style={style}
        className={`
          w-full px-3 py-2 flex items-center gap-2
          text-left transition-colors duration-150
          hover:bg-gray-50 dark:hover:bg-gray-800
          ${!notification.read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''}
          ${className}
        `}
      >
        <div
          className={`
            w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
            ${config.bgColor} ${config.darkBgColor}
          `}
        >
          <span className={`${config.iconColor} ${config.darkIconColor}`}>
            <Icon />
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <p
            className={`text-sm truncate ${
              !notification.read
                ? 'font-semibold text-gray-900 dark:text-white'
                : 'font-medium text-gray-700 dark:text-gray-300'
            }`}
          >
            {notification.title}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {formatRelativeTime(notification.created_at, i18n.language)}
          </p>
        </div>

        {!notification.read && (
          <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
        )}
      </button>
    )
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
      style={style}
      className={`
        group w-full px-4 py-3 flex items-start gap-3
        text-left transition-all duration-150 cursor-pointer
        hover:bg-gray-50 dark:hover:bg-gray-800
        focus:outline-none focus:bg-gray-50 dark:focus:bg-gray-800
        ${!notification.read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''}
        ${className}
      `}
    >
      {/* Icon */}
      <div
        className={`
          w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0
          transition-transform group-hover:scale-105
          ${config.bgColor} ${config.darkBgColor}
        `}
      >
        <span className={`${config.iconColor} ${config.darkIconColor}`}>
          <Icon />
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm leading-tight ${
            !notification.read
              ? 'font-semibold text-gray-900 dark:text-white'
              : 'font-medium text-gray-700 dark:text-gray-300'
          }`}
        >
          {notification.title}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">
          {notification.message}
        </p>

        {/* Footer: Time and Action */}
        <div className="mt-1.5 flex items-center gap-3">
          <span className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {formatRelativeTime(notification.created_at, i18n.language)}
          </span>

          {notification.action_label && notification.action_url && (
            <button
              onClick={handleAction}
              className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
            >
              {notification.action_label}
            </button>
          )}
        </div>
      </div>

      {/* Right side: Unread indicator and actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {showActions && (
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
            {!notification.read && onMarkAsRead && (
              <button
                onClick={handleMarkAsRead}
                className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded transition-colors"
                title={t('notifications.markAsRead', 'Mark as read')}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>
            )}
            {onDelete && (
              <button
                onClick={handleDelete}
                className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded transition-colors"
                title={t('notifications.delete', 'Delete')}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            )}
          </div>
        )}

        {!notification.read && (
          <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse" />
        )}
      </div>
    </div>
  )
}

export default NotificationItem
