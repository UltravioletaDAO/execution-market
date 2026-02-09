/**
 * NotificationBell Component
 *
 * Header bell icon with:
 * - Unread count badge
 * - Dropdown with recent notifications
 * - Mark all as read
 * - Link to full notifications page
 * - Pulse animation on new unread notifications
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNotificationContext } from './NotificationProvider'
import { NotificationItem } from './NotificationItem'
import type { Notification } from '../../types/notification'

// ============================================================================
// Props
// ============================================================================

interface NotificationBellProps {
  onNotificationClick?: (notification: Notification) => void
  onViewAll?: () => void
  maxItems?: number
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function NotificationBell({
  onNotificationClick,
  onViewAll,
  maxItems = 5,
  className = '',
}: NotificationBellProps) {
  const { t } = useTranslation()
  const {
    notifications,
    unreadCount,
    loading,
    markAsRead,
    markAllAsRead,
  } = useNotificationContext()

  const [isOpen, setIsOpen] = useState(false)
  const [hasNewNotification, setHasNewNotification] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const prevUnreadCount = useRef(unreadCount)

  // Track new notifications for pulse animation
  useEffect(() => {
    if (unreadCount > prevUnreadCount.current) {
      setHasNewNotification(true)
      const timer = setTimeout(() => setHasNewNotification(false), 3000)
      return () => clearTimeout(timer)
    }
    prevUnreadCount.current = unreadCount
  }, [unreadCount])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close dropdown on escape key
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [])

  // Handle notification click
  const handleNotificationClick = useCallback(
    (notification: Notification) => {
      if (!notification.read) {
        markAsRead(notification.id)
      }
      onNotificationClick?.(notification)
      setIsOpen(false)
    },
    [markAsRead, onNotificationClick]
  )

  // Handle view all click
  const handleViewAll = useCallback(() => {
    onViewAll?.()
    setIsOpen(false)
  }, [onViewAll])

  // Handle mark all as read
  const handleMarkAllAsRead = useCallback(() => {
    markAllAsRead()
  }, [markAllAsRead])

  // Toggle dropdown
  const toggleDropdown = useCallback(() => {
    setIsOpen((prev) => !prev)
    setHasNewNotification(false)
  }, [])

  // Get recent notifications for dropdown
  const recentNotifications = notifications.slice(0, maxItems)

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={toggleDropdown}
        className={`
          relative p-2 rounded-lg transition-all duration-200
          text-gray-500 dark:text-gray-400
          hover:text-gray-700 dark:hover:text-gray-200
          hover:bg-gray-100 dark:hover:bg-gray-800
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          dark:focus:ring-offset-gray-900
          ${hasNewNotification ? 'animate-pulse' : ''}
        `}
        aria-label={t('notifications.title', 'Notifications')}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {/* Bell icon */}
        <svg
          className={`w-6 h-6 transition-transform ${isOpen ? 'scale-110' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            className={`
              absolute -top-1 -right-1 min-w-[20px] h-5 px-1
              bg-red-500 text-white text-xs font-bold
              rounded-full flex items-center justify-center
              transform transition-all duration-300
              ${hasNewNotification ? 'scale-125 animate-bounce' : 'scale-100'}
            `}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      <div
        className={`
          absolute right-0 mt-2 w-80 sm:w-96
          bg-white dark:bg-gray-900 rounded-xl
          shadow-xl border border-gray-200 dark:border-gray-700
          z-50 overflow-hidden
          transform transition-all duration-200 ease-out origin-top-right
          ${
            isOpen
              ? 'opacity-100 scale-100 translate-y-0'
              : 'opacity-0 scale-95 -translate-y-2 pointer-events-none'
          }
        `}
        role="menu"
        aria-orientation="vertical"
      >
        {/* Header */}
        <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            {t('notifications.title', 'Notifications')}
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs font-medium rounded-full">
                {unreadCount} {unreadCount === 1 ? t('notifications.new', 'new') : t('notifications.newPlural', 'new')}
              </span>
            )}
          </h3>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllAsRead}
              className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium hover:underline transition-colors"
            >
              {t('notifications.markAllRead', 'Mark all as read')}
            </button>
          )}
        </div>

        {/* Notifications list */}
        <div className="max-h-[400px] overflow-y-auto overscroll-contain">
          {loading ? (
            <div className="p-8 flex flex-col items-center justify-center">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {t('common.loading', 'Loading...')}
              </p>
            </div>
          ) : recentNotifications.length === 0 ? (
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
                {t('notifications.empty', 'No notifications')}
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                {t('notifications.emptyDescription', "We'll notify you when something happens")}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {recentNotifications.map((notification: Notification, index: number) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onClick={handleNotificationClick}
                  compact={true}
                  className={`
                    animate-fade-in
                  `}
                  style={{
                    animationDelay: `${index * 30}ms`,
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer - Link to full notifications page */}
        {recentNotifications.length > 0 && onViewAll && (
          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
            <button
              onClick={handleViewAll}
              className="
                w-full py-2 text-center text-sm font-medium
                text-blue-600 dark:text-blue-400
                hover:text-blue-700 dark:hover:text-blue-300
                hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg
                transition-colors duration-150
                flex items-center justify-center gap-2
              "
            >
              {t('notifications.viewAll', 'View all notifications')}
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default NotificationBell
