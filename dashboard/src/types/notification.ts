/**
 * Execution Market Notification Types
 *
 * Type definitions for the notification system including:
 * - Toast notifications (transient)
 * - Persistent notifications (stored in database)
 * - WebSocket events
 */

// ============================================================================
// Notification Types
// ============================================================================

/**
 * Core notification type categories
 */
export type NotificationType =
  | 'task_nearby'       // New tasks available in executor's area
  | 'task_approved'     // Task submission was approved
  | 'task_rejected'     // Task submission was rejected
  | 'payment_received'  // Payment completed
  | 'payment_pending'   // Payment is being processed
  | 'dispute_opened'    // New dispute created
  | 'dispute_update'    // Dispute status changed
  | 'dispute_resolved'  // Dispute has been resolved
  | 'task_assigned'     // Task was assigned to executor
  | 'task_expired'      // Task deadline passed
  | 'task_reminder'     // Reminder about upcoming deadline
  | 'reputation_change' // Reputation score changed
  | 'system'            // System announcements
  | 'achievement'       // Achievement unlocked

/**
 * Toast notification severity levels
 */
export type ToastSeverity = 'success' | 'error' | 'warning' | 'info'

/**
 * Notification priority levels
 */
export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'

// ============================================================================
// Core Notification Interface
// ============================================================================

/**
 * Base notification interface
 */
export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  read: boolean
  created_at: string
  // Optional fields
  task_id?: string
  submission_id?: string
  dispute_id?: string
  action_url?: string
  action_label?: string
  priority?: NotificationPriority
  metadata?: Record<string, unknown>
  expires_at?: string
}

/**
 * Notification as stored in database
 */
export interface NotificationRow extends Notification {
  executor_id: string
  updated_at: string
  deleted_at?: string
}

/**
 * Insert type for creating notifications
 */
export interface NotificationInsert {
  executor_id: string
  type: NotificationType
  title: string
  message: string
  task_id?: string
  submission_id?: string
  dispute_id?: string
  action_url?: string
  action_label?: string
  priority?: NotificationPriority
  metadata?: Record<string, unknown>
  expires_at?: string
}

// ============================================================================
// Toast Notification Types
// ============================================================================

/**
 * Toast notification (transient, not persisted)
 */
export interface Toast {
  id: string
  title: string
  message?: string
  severity: ToastSeverity
  duration?: number       // Auto-dismiss duration in ms (default 5000)
  dismissible?: boolean   // Can be manually dismissed (default true)
  action?: ToastAction
  progress?: boolean      // Show progress bar (default true)
  icon?: React.ReactNode  // Custom icon
}

/**
 * Optional action for toast notifications
 */
export interface ToastAction {
  label: string
  onClick: () => void
}

/**
 * Options for creating a toast
 */
export interface ToastOptions {
  title: string
  message?: string
  severity?: ToastSeverity
  duration?: number
  dismissible?: boolean
  action?: ToastAction
  progress?: boolean
  icon?: React.ReactNode
}

// ============================================================================
// Notification Context Types
// ============================================================================

/**
 * Filter options for notification list
 */
export type NotificationFilter = 'all' | 'unread' | NotificationType

/**
 * Notification context state
 */
export interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  loading: boolean
  error: Error | null
  hasMore: boolean
  filter: NotificationFilter
}

/**
 * Notification context actions
 */
export interface NotificationActions {
  // Notification management
  addNotification: (notification: NotificationInsert) => Promise<void>
  removeNotification: (id: string) => Promise<void>
  markAsRead: (id: string) => Promise<void>
  markAllAsRead: () => Promise<void>

  // Toast management
  addToast: (options: ToastOptions) => string
  removeToast: (id: string) => void

  // Convenience toast methods
  toast: {
    success: (title: string, message?: string) => string
    error: (title: string, message?: string) => string
    warning: (title: string, message?: string) => string
    info: (title: string, message?: string) => string
  }

  // Data fetching
  refresh: () => Promise<void>
  loadMore: () => Promise<void>
  setFilter: (filter: NotificationFilter) => void
}

/**
 * Complete notification context value
 */
export interface NotificationContextValue extends NotificationState, NotificationActions {
  toasts: Toast[]
}

// ============================================================================
// WebSocket Event Types
// ============================================================================

/**
 * WebSocket notification event
 */
export interface NotificationEvent {
  type: 'notification'
  payload: Notification
}

/**
 * WebSocket connection status
 */
export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

// ============================================================================
// Notification Configuration
// ============================================================================

/**
 * Configuration for notification icons and colors
 */
export interface NotificationTypeConfig {
  bgColor: string
  iconColor: string
  darkBgColor: string
  darkIconColor: string
  icon: string // Icon name or key
}

/**
 * Map of notification types to their visual configuration
 */
export type NotificationTypeConfigMap = Record<NotificationType, NotificationTypeConfig>

// ============================================================================
// Helper Types
// ============================================================================

/**
 * Props for notification components that need executor context
 */
export interface NotificationComponentProps {
  executorId: string
}

/**
 * Callback for notification click events
 */
export type OnNotificationClick = (notification: Notification) => void

/**
 * Pagination params for fetching notifications
 */
export interface NotificationPaginationParams {
  limit?: number
  offset?: number
  filter?: NotificationFilter
}
