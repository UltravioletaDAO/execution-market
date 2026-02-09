/**
 * NotificationBell Component (NOW-032)
 *
 * Displays notification bell with count badge and dropdown.
 * Types: new tasks nearby, task approvals, payments received, disputes
 *
 * Features:
 * - Real-time notification updates via Supabase
 * - Animated dropdown with smooth transitions
 * - Mark as read (individual and bulk)
 * - Link to full notifications page
 * - Pulse animation on new unread notifications
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'

// Notification types matching NOW-032 requirements
type NotificationType =
  | 'task_nearby'      // New tasks available in executor's area
  | 'task_approved'    // Task submission was approved
  | 'payment_received' // Payment completed
  | 'dispute_opened'   // New dispute or dispute update
  | 'task_assigned'    // Task was assigned to executor
  | 'task_expired'     // Task deadline passed

interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  task_id?: string
  read: boolean
  created_at: string
  metadata?: Record<string, unknown>
}

interface NotificationBellProps {
  executorId: string
  onNotificationClick?: (notification: Notification) => void
  onViewAll?: () => void
}

// Format relative time in a human-friendly way
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Ahora mismo'
  if (diffMins < 60) return `hace ${diffMins}m`
  if (diffHours < 24) return `hace ${diffHours}h`
  if (diffDays === 1) return 'Ayer'
  if (diffDays < 7) return `hace ${diffDays}d`
  return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
}

// Icon configuration for each notification type
const NOTIFICATION_CONFIG: Record<
  NotificationType,
  { bgColor: string; iconColor: string; icon: JSX.Element }
> = {
  task_nearby: {
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600',
    icon: (
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
    ),
  },
  task_approved: {
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  payment_received: {
    bgColor: 'bg-emerald-100',
    iconColor: 'text-emerald-600',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  dispute_opened: {
    bgColor: 'bg-amber-100',
    iconColor: 'text-amber-600',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
  },
  task_assigned: {
    bgColor: 'bg-indigo-100',
    iconColor: 'text-indigo-600',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      </svg>
    ),
  },
  task_expired: {
    bgColor: 'bg-gray-100',
    iconColor: 'text-gray-500',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
}

// Individual notification icon component
function NotificationIcon({ type }: { type: NotificationType }) {
  const config = NOTIFICATION_CONFIG[type] || NOTIFICATION_CONFIG.task_nearby

  return (
    <div
      className={`w-10 h-10 ${config.bgColor} rounded-full flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105`}
    >
      <span className={config.iconColor}>{config.icon}</span>
    </div>
  )
}

export function NotificationBell({
  executorId,
  onNotificationClick,
  onViewAll,
}: NotificationBellProps) {
  const db = supabase as any
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [hasNewNotification, setHasNewNotification] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

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

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    try {
      const { data, error } = await db
        .from('notifications')
        .select('*')
        .eq('executor_id', executorId)
        .order('created_at', { ascending: false })
        .limit(20)

      if (error) throw error

      setNotifications(data || [])
    } catch (err) {
      console.error('Failed to fetch notifications:', err)
    } finally {
      setLoading(false)
    }
  }, [executorId, db])

  // Initial fetch
  useEffect(() => {
    fetchNotifications()
  }, [fetchNotifications])

  // Subscribe to real-time notifications
  useEffect(() => {
    const channel = db
      .channel(`notifications-${executorId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'notifications',
          filter: `executor_id=eq.${executorId}`,
        },
        (payload: any) => {
          const newNotification = payload.new as Notification
          setNotifications((prev) => [newNotification, ...prev])
          setHasNewNotification(true)

          // Reset pulse animation after a few seconds
          setTimeout(() => setHasNewNotification(false), 3000)
        }
      )
      .subscribe()

    return () => {
      db.removeChannel(channel)
    }
  }, [executorId, db])

  // Mark notification as read
  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      await db
        .from('notifications')
        .update({ read: true })
        .eq('id', notificationId)

      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n))
      )
    } catch (err) {
      console.error('Failed to mark notification as read:', err)
    }
  }, [])

  // Mark all as read
  const markAllAsRead = useCallback(async () => {
    try {
      await db
        .from('notifications')
        .update({ read: true })
        .eq('executor_id', executorId)
        .eq('read', false)

      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err)
    }
  }, [executorId])

  // Handle notification click
  const handleNotificationClick = useCallback(
    (notification: Notification) => {
      markAsRead(notification.id)
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

  // Count unread
  const unreadCount = notifications.filter((n) => !n.read).length

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => {
          setIsOpen(!isOpen)
          setHasNewNotification(false)
        }}
        className={`
          relative p-2 rounded-lg transition-all duration-200
          text-gray-500 hover:text-gray-700 hover:bg-gray-100
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${hasNewNotification ? 'animate-pulse' : ''}
        `}
        aria-label={t('notifications.title', 'Notificaciones')}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {/* Bell icon with subtle animation */}
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

        {/* Unread badge with animation */}
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

      {/* Dropdown with smooth animation */}
      <div
        className={`
          absolute right-0 mt-2 w-80 sm:w-96
          bg-white rounded-xl shadow-xl border border-gray-200
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
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            {t('notifications.title', 'Notificaciones')}
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                {unreadCount} {unreadCount === 1 ? 'nueva' : 'nuevas'}
              </span>
            )}
          </h3>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium hover:underline transition-colors"
            >
              {t('notifications.markAllRead', 'Marcar todas como leidas')}
            </button>
          )}
        </div>

        {/* Notifications list */}
        <div className="max-h-[400px] overflow-y-auto overscroll-contain">
          {loading ? (
            <div className="p-8 flex flex-col items-center justify-center">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="mt-2 text-sm text-gray-500">Cargando...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-gray-400"
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
              <p className="text-gray-600 font-medium">
                {t('notifications.empty', 'No hay notificaciones')}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Te avisaremos cuando haya algo nuevo
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {notifications.map((notification, index) => (
                <button
                  key={notification.id}
                  onClick={() => handleNotificationClick(notification)}
                  className={`
                    group w-full px-4 py-3 flex items-start gap-3
                    text-left transition-all duration-150
                    hover:bg-gray-50 focus:bg-gray-50 focus:outline-none
                    ${!notification.read ? 'bg-blue-50/50' : ''}
                  `}
                  style={{
                    animationDelay: `${index * 30}ms`,
                  }}
                  role="menuitem"
                >
                  <NotificationIcon type={notification.type} />

                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm leading-tight ${
                        !notification.read
                          ? 'font-semibold text-gray-900'
                          : 'font-medium text-gray-700'
                      }`}
                    >
                      {notification.title}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-relaxed">
                      {notification.message}
                    </p>
                    <p className="text-xs text-gray-400 mt-1.5 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      {formatRelativeTime(notification.created_at)}
                    </p>
                  </div>

                  {/* Unread indicator */}
                  {!notification.read && (
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer - Link to full notifications page */}
        {notifications.length > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
            <button
              onClick={handleViewAll}
              className="
                w-full py-2 text-center text-sm font-medium
                text-blue-600 hover:text-blue-700
                hover:bg-blue-50 rounded-lg
                transition-colors duration-150
                flex items-center justify-center gap-2
              "
            >
              {t('notifications.viewAll', 'Ver todas las notificaciones')}
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

export type { Notification, NotificationType }
export default NotificationBell
