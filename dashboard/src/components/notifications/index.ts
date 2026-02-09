/**
 * Notifications Components Barrel Export
 *
 * Provides the complete notification system:
 * - NotificationProvider: Context provider for state management
 * - NotificationBell: Header bell icon with dropdown
 * - NotificationList: Full list with filters and infinite scroll
 * - NotificationItem: Single notification display
 * - Toast/ToastContainer: Toast notification system
 */

// Provider
export {
  NotificationProvider,
  NotificationContext,
} from './NotificationProvider'

// Hooks
export { useNotificationContext } from './hooks'

// Components
export { NotificationBell } from './NotificationBell'
export { NotificationList } from './NotificationList'
export { NotificationItem } from './NotificationItem'
export { Toast, ToastContainer } from './Toast'

// Re-export types for convenience
export type {
  Notification,
  NotificationType,
  NotificationInsert,
  NotificationRow,
  NotificationFilter,
  NotificationPriority,
  NotificationContextValue,
  Toast as ToastType,
  ToastSeverity,
  ToastOptions,
  ToastAction,
  OnNotificationClick,
  NotificationComponentProps,
  NotificationPaginationParams,
  WebSocketStatus,
} from '../../types/notification'
