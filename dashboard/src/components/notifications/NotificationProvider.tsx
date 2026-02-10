/**
 * NotificationProvider Component
 *
 * Context provider for the notification system:
 * - Toast notifications (success, error, warning, info)
 * - Persistent notifications list from database
 * - WebSocket connection for real-time updates
 * - Methods: addNotification, removeNotification, markAsRead, etc.
 */

import {
  createContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from 'react'
import { supabase } from '../../lib/supabase'
import type { RealtimeChannel, RealtimePostgresChangesPayload } from '@supabase/supabase-js'
import type {
  Notification,
  NotificationInsert,
  NotificationContextValue,
  NotificationFilter,
  Toast,
  ToastOptions,
  ToastSeverity,
  WebSocketStatus,
} from '../../types/notification'

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_TOAST_DURATION = 5000
const NOTIFICATIONS_PER_PAGE = 20
const RECONNECT_DELAY = 3000

// ============================================================================
// Context
// ============================================================================

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined)

// ============================================================================
// Helper Functions
// ============================================================================

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// ============================================================================
// Provider Props
// ============================================================================

interface NotificationProviderProps {
  children: ReactNode
  executorId?: string
  enableWebSocket?: boolean
}

// ============================================================================
// Provider Component
// ============================================================================

export function NotificationProvider({
  children,
  executorId,
  enableWebSocket = true,
}: NotificationProviderProps) {
  const db = supabase

  // State
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [toasts, setToasts] = useState<Toast[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const [filter, setFilter] = useState<NotificationFilter>('all')
  const [, setWsStatus] = useState<WebSocketStatus>('disconnected')

  // Refs
  const channelRef = useRef<RealtimeChannel | null>(null)
  const offsetRef = useRef(0)

  // --------------------------------------------------------------------------
  // Fetch Notifications
  // --------------------------------------------------------------------------

  const fetchNotifications = useCallback(
    async (reset = false) => {
      if (!executorId) {
        setNotifications([])
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        setError(null)

        const offset = reset ? 0 : offsetRef.current

        let query = db
          .from('notifications')
          .select('*')
          .eq('executor_id', executorId)
          .order('created_at', { ascending: false })
          .range(offset, offset + NOTIFICATIONS_PER_PAGE - 1)

        // Apply filter
        if (filter === 'unread') {
          query = query.eq('read', false)
        } else if (filter !== 'all') {
          query = query.eq('type', filter)
        }

        const { data, error: fetchError } = await query

        if (fetchError) throw fetchError

        const newNotifications = data || []

        if (reset) {
          setNotifications(newNotifications)
          offsetRef.current = newNotifications.length
        } else {
          setNotifications((prev) => [...prev, ...newNotifications])
          offsetRef.current += newNotifications.length
        }

        setHasMore(newNotifications.length === NOTIFICATIONS_PER_PAGE)
      } catch (err) {
        console.error('[NotificationProvider] Fetch error:', err)
        setError(err instanceof Error ? err : new Error('Failed to fetch notifications'))
      } finally {
        setLoading(false)
      }
    },
    [executorId, filter, db]
  )

  // --------------------------------------------------------------------------
  // Fetch Unread Count
  // --------------------------------------------------------------------------

  const fetchUnreadCount = useCallback(async () => {
    if (!executorId) {
      setUnreadCount(0)
      return
    }

    try {
      const { count, error: countError } = await db
        .from('notifications')
        .select('*', { count: 'exact', head: true })
        .eq('executor_id', executorId)
        .eq('read', false)

      if (countError) throw countError

      setUnreadCount(count || 0)
    } catch (err) {
      console.error('[NotificationProvider] Count error:', err)
    }
  }, [executorId, db])

  // --------------------------------------------------------------------------
  // WebSocket Subscription
  // --------------------------------------------------------------------------

  useEffect(() => {
    if (!executorId || !enableWebSocket) return

    const setupChannel = () => {
      setWsStatus('connecting')

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
          (payload: RealtimePostgresChangesPayload<Notification>) => {
            const newNotification = payload.new as Notification

            setNotifications((prev) => [newNotification, ...prev])
            setUnreadCount((prev) => prev + 1)

            // Optionally show toast for certain notification types
            if (newNotification.priority === 'urgent' || newNotification.priority === 'high') {
              // Let consuming components handle toast display if needed
            }
          }
        )
        .on(
          'postgres_changes',
          {
            event: 'UPDATE',
            schema: 'public',
            table: 'notifications',
            filter: `executor_id=eq.${executorId}`,
          },
          (payload: RealtimePostgresChangesPayload<Notification>) => {
            const updated = payload.new as Notification

            setNotifications((prev) =>
              prev.map((n) => (n.id === updated.id ? updated : n))
            )

            // Update unread count if read status changed
            if (payload.old && (payload.old as Notification).read !== updated.read) {
              setUnreadCount((prev) => (updated.read ? Math.max(0, prev - 1) : prev + 1))
            }
          }
        )
        .on(
          'postgres_changes',
          {
            event: 'DELETE',
            schema: 'public',
            table: 'notifications',
            filter: `executor_id=eq.${executorId}`,
          },
          (payload: RealtimePostgresChangesPayload<Notification>) => {
            const deleted = payload.old as Notification

            setNotifications((prev) => prev.filter((n) => n.id !== deleted.id))

            if (!deleted.read) {
              setUnreadCount((prev) => Math.max(0, prev - 1))
            }
          }
        )
        .subscribe((status: string) => {
          if (status === 'SUBSCRIBED') {
            setWsStatus('connected')
          } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
            setWsStatus('error')
            // Attempt reconnect
            setTimeout(setupChannel, RECONNECT_DELAY)
          }
        })

      channelRef.current = channel
    }

    setupChannel()

    return () => {
      if (channelRef.current) {
        db.removeChannel(channelRef.current)
        channelRef.current = null
      }
      setWsStatus('disconnected')
    }
  }, [executorId, enableWebSocket, db])

  // --------------------------------------------------------------------------
  // Initial Fetch
  // --------------------------------------------------------------------------

  useEffect(() => {
    fetchNotifications(true)
    fetchUnreadCount()
  }, [fetchNotifications, fetchUnreadCount])

  // --------------------------------------------------------------------------
  // Notification Actions
  // --------------------------------------------------------------------------

  const addNotification = useCallback(
    async (notification: NotificationInsert) => {
      if (!executorId) {
        throw new Error('No executor ID provided')
      }

      try {
        const { error: insertError } = await db
          .from('notifications')
          .insert({ ...notification, executor_id: executorId })

        if (insertError) throw insertError

        // Real-time subscription will handle state update
      } catch (err) {
        console.error('[NotificationProvider] Add error:', err)
        throw err
      }
    },
    [executorId, db]
  )

  const removeNotification = useCallback(async (id: string) => {
    try {
      const { error: deleteError } = await db
        .from('notifications')
        .delete()
        .eq('id', id)

      if (deleteError) throw deleteError

      // Real-time subscription will handle state update
    } catch (err) {
      console.error('[NotificationProvider] Remove error:', err)
      throw err
    }
  }, [db])

  const markAsRead = useCallback(async (id: string) => {
    try {
      const { error: updateError } = await db
        .from('notifications')
        .update({ read: true })
        .eq('id', id)

      if (updateError) throw updateError

      // Optimistic update
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      )
      setUnreadCount((prev) => Math.max(0, prev - 1))
    } catch (err) {
      console.error('[NotificationProvider] Mark as read error:', err)
      throw err
    }
  }, [db])

  const markAllAsRead = useCallback(async () => {
    if (!executorId) return

    try {
      const { error: updateError } = await db
        .from('notifications')
        .update({ read: true })
        .eq('executor_id', executorId)
        .eq('read', false)

      if (updateError) throw updateError

      // Optimistic update
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
      setUnreadCount(0)
    } catch (err) {
      console.error('[NotificationProvider] Mark all as read error:', err)
      throw err
    }
  }, [executorId, db])

  // --------------------------------------------------------------------------
  // Toast Actions
  // --------------------------------------------------------------------------

  const addToast = useCallback((options: ToastOptions): string => {
    const id = generateId()

    const toast: Toast = {
      id,
      title: options.title,
      message: options.message,
      severity: options.severity || 'info',
      duration: options.duration ?? DEFAULT_TOAST_DURATION,
      dismissible: options.dismissible ?? true,
      action: options.action,
      progress: options.progress ?? true,
      icon: options.icon,
    }

    setToasts((prev) => [...prev, toast])

    // Auto-dismiss
    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, toast.duration)
    }

    return id
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  // Convenience toast methods
  const createToastMethod = useCallback(
    (severity: ToastSeverity) => {
      return (title: string, message?: string): string => {
        return addToast({ title, message, severity })
      }
    },
    [addToast]
  )

  const toast = {
    success: createToastMethod('success'),
    error: createToastMethod('error'),
    warning: createToastMethod('warning'),
    info: createToastMethod('info'),
  }

  // --------------------------------------------------------------------------
  // Data Management
  // --------------------------------------------------------------------------

  const refresh = useCallback(async () => {
    offsetRef.current = 0
    await fetchNotifications(true)
    await fetchUnreadCount()
  }, [fetchNotifications, fetchUnreadCount])

  const loadMore = useCallback(async () => {
    if (!hasMore || loading) return
    await fetchNotifications(false)
  }, [fetchNotifications, hasMore, loading])

  const handleSetFilter = useCallback((newFilter: NotificationFilter) => {
    setFilter(newFilter)
    offsetRef.current = 0
  }, [])

  // Re-fetch when filter changes
  useEffect(() => {
    fetchNotifications(true)
  }, [filter, fetchNotifications])

  // --------------------------------------------------------------------------
  // Context Value
  // --------------------------------------------------------------------------

  const value: NotificationContextValue = {
    // State
    notifications,
    toasts,
    unreadCount,
    loading,
    error,
    hasMore,
    filter,

    // Notification actions
    addNotification,
    removeNotification,
    markAsRead,
    markAllAsRead,

    // Toast actions
    addToast,
    removeToast,
    toast,

    // Data management
    refresh,
    loadMore,
    setFilter: handleSetFilter,
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}

// Export context for use in hooks
export { NotificationContext }

// Re-export useNotificationContext hook for backward compatibility
// Note: This re-export is needed for backward compatibility with existing imports
// eslint-disable-next-line react-refresh/only-export-components
export { useNotificationContext } from './hooks'
