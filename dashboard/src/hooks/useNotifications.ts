/**
 * useNotifications Hook
 *
 * Custom hook for accessing notification context with:
 * - Access to notification state and actions
 * - Helper functions for common notification patterns
 * - Type-safe notification creation
 */

import { useCallback, useMemo } from 'react'
import { useNotificationContext } from '../components/notifications/NotificationProvider'
import type {
  Notification,
  NotificationInsert,
  NotificationType,
  ToastOptions,
  NotificationFilter,
} from '../types/notification'

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseNotificationsReturn {
  // State
  notifications: Notification[]
  unreadCount: number
  loading: boolean
  error: Error | null
  hasMore: boolean
  filter: NotificationFilter

  // Notification management
  addNotification: (notification: NotificationInsert) => Promise<void>
  removeNotification: (id: string) => Promise<void>
  markAsRead: (id: string) => Promise<void>
  markAllAsRead: () => Promise<void>

  // Toast shortcuts
  toast: {
    success: (title: string, message?: string) => string
    error: (title: string, message?: string) => string
    warning: (title: string, message?: string) => string
    info: (title: string, message?: string) => string
  }
  addToast: (options: ToastOptions) => string
  removeToast: (id: string) => void

  // Data management
  refresh: () => Promise<void>
  loadMore: () => Promise<void>
  setFilter: (filter: NotificationFilter) => void

  // Helper functions
  notify: {
    taskNearby: (taskId: string, title: string, message: string) => Promise<void>
    taskApproved: (taskId: string, message?: string) => Promise<void>
    taskRejected: (taskId: string, message?: string) => Promise<void>
    paymentReceived: (taskId: string, amount: number, currency?: string) => Promise<void>
    paymentPending: (taskId: string, message?: string) => Promise<void>
    disputeOpened: (disputeId: string, taskId: string, reason: string) => Promise<void>
    disputeResolved: (disputeId: string, taskId: string, winner: 'agent' | 'executor') => Promise<void>
    reputationChange: (delta: number, newScore: number) => Promise<void>
    system: (title: string, message: string) => Promise<void>
  }

  // Toast with action
  toastWithAction: (
    options: ToastOptions & {
      actionLabel: string
      onAction: () => void
    }
  ) => string
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useNotifications(): UseNotificationsReturn {
  const context = useNotificationContext()

  const {
    notifications,
    unreadCount,
    loading,
    error,
    hasMore,
    filter,
    toasts: _toasts,
    addNotification,
    removeNotification,
    markAsRead,
    markAllAsRead,
    addToast,
    removeToast,
    toast,
    refresh,
    loadMore,
    setFilter,
  } = context

  // --------------------------------------------------------------------------
  // Helper Functions for Common Notifications
  // --------------------------------------------------------------------------

  const notifyTaskNearby = useCallback(
    async (taskId: string, title: string, message: string) => {
      await addNotification({
        type: 'task_nearby',
        title,
        message,
        task_id: taskId,
        action_url: `/tasks/${taskId}`,
        action_label: 'Ver tarea',
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifyTaskApproved = useCallback(
    async (taskId: string, message?: string) => {
      await addNotification({
        type: 'task_approved',
        title: 'Tarea aprobada',
        message: message || 'Tu submission ha sido aprobada. El pago sera procesado pronto.',
        task_id: taskId,
        action_url: `/tasks/${taskId}`,
        action_label: 'Ver detalles',
        priority: 'high',
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifyTaskRejected = useCallback(
    async (taskId: string, message?: string) => {
      await addNotification({
        type: 'task_rejected',
        title: 'Tarea rechazada',
        message: message || 'Tu submission ha sido rechazada. Revisa los comentarios del agente.',
        task_id: taskId,
        action_url: `/tasks/${taskId}`,
        action_label: 'Ver motivo',
        priority: 'high',
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifyPaymentReceived = useCallback(
    async (taskId: string, amount: number, currency: string = 'USDC') => {
      await addNotification({
        type: 'payment_received',
        title: 'Pago recibido',
        message: `Has recibido $${amount.toFixed(2)} ${currency} por tu trabajo.`,
        task_id: taskId,
        action_url: '/payments',
        action_label: 'Ver pagos',
        priority: 'high',
        metadata: { amount, currency },
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifyPaymentPending = useCallback(
    async (taskId: string, message?: string) => {
      await addNotification({
        type: 'payment_pending',
        title: 'Pago en proceso',
        message: message || 'Tu pago esta siendo procesado.',
        task_id: taskId,
        action_url: '/payments',
        action_label: 'Ver estado',
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifyDisputeOpened = useCallback(
    async (disputeId: string, taskId: string, reason: string) => {
      await addNotification({
        type: 'dispute_opened',
        title: 'Disputa abierta',
        message: reason,
        task_id: taskId,
        dispute_id: disputeId,
        action_url: `/disputes/${disputeId}`,
        action_label: 'Ver disputa',
        priority: 'urgent',
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifyDisputeResolved = useCallback(
    async (disputeId: string, taskId: string, winner: 'agent' | 'executor') => {
      await addNotification({
        type: 'dispute_resolved',
        title: 'Disputa resuelta',
        message:
          winner === 'executor'
            ? 'La disputa se resolvio a tu favor. Recibiras el pago.'
            : 'La disputa se resolvio a favor del agente.',
        task_id: taskId,
        dispute_id: disputeId,
        action_url: `/disputes/${disputeId}`,
        action_label: 'Ver resolucion',
        priority: 'high',
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifyReputationChange = useCallback(
    async (delta: number, newScore: number) => {
      const isPositive = delta > 0
      await addNotification({
        type: 'reputation_change',
        title: isPositive ? 'Reputacion aumentada' : 'Reputacion disminuida',
        message: `Tu reputacion ${isPositive ? 'aumento' : 'disminuyo'} ${Math.abs(delta)} puntos. Nueva puntuacion: ${newScore}`,
        action_url: '/profile',
        action_label: 'Ver perfil',
        metadata: { delta, newScore },
      } as NotificationInsert)
    },
    [addNotification]
  )

  const notifySystem = useCallback(
    async (title: string, message: string) => {
      await addNotification({
        type: 'system',
        title,
        message,
      } as NotificationInsert)
    },
    [addNotification]
  )

  // --------------------------------------------------------------------------
  // Toast with Action Helper
  // --------------------------------------------------------------------------

  const toastWithAction = useCallback(
    (
      options: ToastOptions & {
        actionLabel: string
        onAction: () => void
      }
    ): string => {
      const { actionLabel, onAction, ...toastOptions } = options
      return addToast({
        ...toastOptions,
        action: {
          label: actionLabel,
          onClick: onAction,
        },
      })
    },
    [addToast]
  )

  // --------------------------------------------------------------------------
  // Memoized notify object
  // --------------------------------------------------------------------------

  const notify = useMemo(
    () => ({
      taskNearby: notifyTaskNearby,
      taskApproved: notifyTaskApproved,
      taskRejected: notifyTaskRejected,
      paymentReceived: notifyPaymentReceived,
      paymentPending: notifyPaymentPending,
      disputeOpened: notifyDisputeOpened,
      disputeResolved: notifyDisputeResolved,
      reputationChange: notifyReputationChange,
      system: notifySystem,
    }),
    [
      notifyTaskNearby,
      notifyTaskApproved,
      notifyTaskRejected,
      notifyPaymentReceived,
      notifyPaymentPending,
      notifyDisputeOpened,
      notifyDisputeResolved,
      notifyReputationChange,
      notifySystem,
    ]
  )

  // --------------------------------------------------------------------------
  // Return Value
  // --------------------------------------------------------------------------

  return {
    // State
    notifications,
    unreadCount,
    loading,
    error,
    hasMore,
    filter,

    // Notification management
    addNotification,
    removeNotification,
    markAsRead,
    markAllAsRead,

    // Toast shortcuts
    toast,
    addToast,
    removeToast,

    // Data management
    refresh,
    loadMore,
    setFilter,

    // Helper functions
    notify,

    // Toast with action
    toastWithAction,
  }
}

// ============================================================================
// Standalone Toast Hook (for use outside NotificationProvider)
// ============================================================================

export interface UseStandaloneToastsReturn {
  toasts: ToastOptions[]
  addToast: (options: ToastOptions) => string
  removeToast: (id: string) => void
  toast: {
    success: (title: string, message?: string) => string
    error: (title: string, message?: string) => string
    warning: (title: string, message?: string) => string
    info: (title: string, message?: string) => string
  }
}

/**
 * Standalone toast hook for use when NotificationProvider is not available.
 * Manages its own toast state.
 */
export function useStandaloneToasts(): UseStandaloneToastsReturn {
  // This would need to be implemented with local state if you want
  // toasts without the full notification provider.
  // For now, we recommend using the full NotificationProvider.
  throw new Error(
    'useStandaloneToasts is not implemented. Please use NotificationProvider with useNotifications hook.'
  )
}

export default useNotifications
