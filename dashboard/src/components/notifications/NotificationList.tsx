/**
 * NotificationList Component
 *
 * Full notifications list with:
 * - Filter by type (all, unread, task, payment, etc.)
 * - Mark as read/unread
 * - Delete notifications
 * - Infinite scroll for loading more
 */

import { useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNotificationContext } from './NotificationProvider'
import { NotificationItem } from './NotificationItem'
import type { Notification, NotificationFilter } from '../../types/notification'

// ============================================================================
// Filter Configuration
// ============================================================================

interface FilterOption {
  value: NotificationFilter
  label: string
  icon?: React.ReactNode
}

const FILTER_OPTIONS: FilterOption[] = [
  { value: 'all', label: 'All' },
  { value: 'unread', label: 'Unread' },
  { value: 'task_nearby', label: 'Tasks' },
  { value: 'payment_received', label: 'Payments' },
  { value: 'dispute_opened', label: 'Disputes' },
  { value: 'system', label: 'System' },
]

// ============================================================================
// Props
// ============================================================================

interface NotificationListProps {
  onNotificationClick?: (notification: Notification) => void
  showHeader?: boolean
  showFilters?: boolean
  emptyMessage?: string
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function NotificationList({
  onNotificationClick,
  showHeader = true,
  showFilters = true,
  emptyMessage,
  className = '',
}: NotificationListProps) {
  const { t } = useTranslation()
  const {
    notifications,
    unreadCount,
    loading,
    error,
    hasMore,
    filter,
    setFilter,
    loadMore,
    markAsRead,
    markAllAsRead,
    removeNotification,
    refresh,
  } = useNotificationContext()

  // Ref for infinite scroll sentinel
  const sentinelRef = useRef<HTMLDivElement>(null)

  // --------------------------------------------------------------------------
  // Infinite Scroll
  // --------------------------------------------------------------------------

  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loading) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMore()
        }
      },
      { rootMargin: '100px' }
    )

    observer.observe(sentinelRef.current)

    return () => observer.disconnect()
  }, [hasMore, loading, loadMore])

  // --------------------------------------------------------------------------
  // Handlers
  // --------------------------------------------------------------------------

  const handleNotificationClick = useCallback(
    (notification: Notification) => {
      if (!notification.read) {
        markAsRead(notification.id)
      }
      onNotificationClick?.(notification)
    },
    [markAsRead, onNotificationClick]
  )

  const handleMarkAsRead = useCallback(
    (id: string) => {
      markAsRead(id)
    },
    [markAsRead]
  )

  const handleDelete = useCallback(
    (id: string) => {
      removeNotification(id)
    },
    [removeNotification]
  )

  const handleFilterChange = useCallback(
    (newFilter: NotificationFilter) => {
      setFilter(newFilter)
    },
    [setFilter]
  )

  // --------------------------------------------------------------------------
  // Render
  // --------------------------------------------------------------------------

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      {showHeader && (
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-white dark:bg-gray-900">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('notifications.title', 'Notifications')}
            </h2>
            {unreadCount > 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {unreadCount} {t('notifications.unread', 'unread')}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
              >
                {t('notifications.markAllRead', 'Mark all as read')}
              </button>
            )}
            <button
              onClick={refresh}
              className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              title={t('common.refresh', 'Refresh')}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Filters */}
      {showFilters && (
        <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 overflow-x-auto">
          <div className="flex gap-2">
            {FILTER_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => handleFilterChange(option.value)}
                className={`
                  px-3 py-1.5 text-sm font-medium rounded-full whitespace-nowrap
                  transition-all duration-200
                  ${
                    filter === option.value
                      ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }
                `}
              >
                {t(`notifications.filter.${option.value}`, option.label)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto">
        {error ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-red-500 dark:text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <p className="text-gray-600 dark:text-gray-300 font-medium">
              {t('notifications.error', 'Failed to load notifications')}
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{error.message}</p>
            <button
              onClick={refresh}
              className="mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              {t('common.tryAgain', 'Try again')}
            </button>
          </div>
        ) : notifications.length === 0 && !loading ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-gray-400 dark:text-gray-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
            </div>
            <p className="text-gray-600 dark:text-gray-300 font-medium">
              {emptyMessage || t('notifications.empty', 'No notifications')}
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
              {filter === 'unread'
                ? t('notifications.noUnread', "You're all caught up!")
                : t('notifications.emptyDescription', "We'll notify you when something happens")}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {notifications.map((notification: Notification, index: number) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onClick={handleNotificationClick}
                onMarkAsRead={handleMarkAsRead}
                onDelete={handleDelete}
                showActions={true}
                className="animate-fade-in"
                style={{
                  animationDelay: `${index * 30}ms`,
                }}
              />
            ))}

            {/* Loading indicator */}
            {loading && (
              <div className="p-4 flex justify-center">
                <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              </div>
            )}

            {/* Infinite scroll sentinel */}
            {hasMore && !loading && <div ref={sentinelRef} className="h-1" />}

            {/* End of list indicator */}
            {!hasMore && notifications.length > 0 && (
              <div className="py-4 text-center text-sm text-gray-400 dark:text-gray-500">
                {t('notifications.endOfList', "That's all your notifications")}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default NotificationList
