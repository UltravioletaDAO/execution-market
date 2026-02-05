/**
 * Toast Component
 *
 * Toast notification with:
 * - Auto-dismiss after configurable duration (default 5 seconds)
 * - Dismiss button
 * - Progress bar showing remaining time
 * - Stacking multiple toasts
 * - Severity variants (success, error, warning, info)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useNotificationContext } from './NotificationProvider'
import type { Toast as ToastType, ToastSeverity } from '../../types/notification'

// ============================================================================
// Configuration
// ============================================================================

interface SeverityConfig {
  bgColor: string
  borderColor: string
  textColor: string
  iconColor: string
  progressColor: string
  Icon: React.FC
}

const SEVERITY_CONFIG: Record<ToastSeverity, SeverityConfig> = {
  success: {
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800',
    textColor: 'text-green-800 dark:text-green-200',
    iconColor: 'text-green-500 dark:text-green-400',
    progressColor: 'bg-green-500',
    Icon: () => (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
  },
  error: {
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
    textColor: 'text-red-800 dark:text-red-200',
    iconColor: 'text-red-500 dark:text-red-400',
    progressColor: 'bg-red-500',
    Icon: () => (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
  },
  warning: {
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-amber-200 dark:border-amber-800',
    textColor: 'text-amber-800 dark:text-amber-200',
    iconColor: 'text-amber-500 dark:text-amber-400',
    progressColor: 'bg-amber-500',
    Icon: () => (
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
  info: {
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800',
    textColor: 'text-blue-800 dark:text-blue-200',
    iconColor: 'text-blue-500 dark:text-blue-400',
    progressColor: 'bg-blue-500',
    Icon: () => (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
}

// ============================================================================
// Single Toast Component
// ============================================================================

interface ToastItemProps {
  toast: ToastType
  onDismiss: (id: string) => void
  index: number
}

function ToastItem({ toast, onDismiss, index }: ToastItemProps) {
  const [isLeaving, setIsLeaving] = useState(false)
  const [progress, setProgress] = useState(100)
  const [isPaused, setIsPaused] = useState(false)
  const startTimeRef = useRef(Date.now())
  const remainingTimeRef = useRef(toast.duration || 5000)

  const config = SEVERITY_CONFIG[toast.severity]
  const { Icon } = config

  // Handle dismiss with animation
  const handleDismiss = useCallback(() => {
    setIsLeaving(true)
    setTimeout(() => {
      onDismiss(toast.id)
    }, 300) // Match animation duration
  }, [onDismiss, toast.id])

  // Progress bar animation
  useEffect(() => {
    if (!toast.progress || !toast.duration || toast.duration <= 0) return
    if (isPaused) return

    const startTime = Date.now()
    const duration = remainingTimeRef.current

    const updateProgress = () => {
      const elapsed = Date.now() - startTime
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100)
      setProgress(remaining)

      if (remaining > 0) {
        requestAnimationFrame(updateProgress)
      }
    }

    const animationId = requestAnimationFrame(updateProgress)

    return () => cancelAnimationFrame(animationId)
  }, [toast.progress, toast.duration, isPaused])

  // Pause on hover
  const handleMouseEnter = useCallback(() => {
    if (!toast.duration || toast.duration <= 0) return
    setIsPaused(true)
    remainingTimeRef.current = (progress / 100) * toast.duration
  }, [progress, toast.duration])

  const handleMouseLeave = useCallback(() => {
    setIsPaused(false)
    startTimeRef.current = Date.now()
  }, [])

  // Handle action click
  const handleAction = useCallback(() => {
    toast.action?.onClick()
    handleDismiss()
  }, [toast.action, handleDismiss])

  return (
    <div
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`
        relative w-full max-w-sm rounded-lg border shadow-lg overflow-hidden
        transform transition-all duration-300 ease-out
        ${config.bgColor} ${config.borderColor}
        ${
          isLeaving
            ? 'opacity-0 translate-x-full scale-95'
            : 'opacity-100 translate-x-0 scale-100'
        }
      `}
      style={{
        animationDelay: `${index * 50}ms`,
      }}
      role="alert"
      aria-live="polite"
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={`flex-shrink-0 ${config.iconColor}`}>
            {toast.icon ?? <Icon />}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className={`text-sm font-medium ${config.textColor}`}>{toast.title}</p>
            {toast.message && (
              <p className={`mt-1 text-sm opacity-80 ${config.textColor}`}>{toast.message}</p>
            )}

            {/* Action button */}
            {toast.action && (
              <button
                onClick={handleAction}
                className={`mt-2 text-sm font-medium underline hover:no-underline ${config.textColor}`}
              >
                {toast.action.label}
              </button>
            )}
          </div>

          {/* Dismiss button */}
          {toast.dismissible !== false && (
            <button
              onClick={handleDismiss}
              className={`flex-shrink-0 p-1 rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors ${config.textColor}`}
              aria-label="Dismiss"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {toast.progress !== false && toast.duration && toast.duration > 0 && (
        <div className="h-1 bg-black/5 dark:bg-white/10">
          <div
            className={`h-full transition-none ${config.progressColor}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Toast Container Component
// ============================================================================

interface ToastContainerProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
  maxToasts?: number
}

export function ToastContainer({
  position = 'top-right',
  maxToasts = 5,
}: ToastContainerProps) {
  const { toasts, removeToast } = useNotificationContext()

  // Limit number of visible toasts
  const visibleToasts = toasts.slice(-maxToasts)

  // Position classes
  const positionClasses: Record<typeof position, string> = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
  }

  // Don't render if no toasts
  if (visibleToasts.length === 0) return null

  return createPortal(
    <div
      className={`fixed ${positionClasses[position]} z-[9999] flex flex-col gap-2 pointer-events-none`}
      aria-label="Notifications"
    >
      {visibleToasts.map((toast, index) => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem
            toast={toast}
            onDismiss={removeToast}
            index={index}
          />
        </div>
      ))}
    </div>,
    document.body
  )
}

// ============================================================================
// Standalone Toast Component (for direct use without provider)
// ============================================================================

interface StandaloneToastProps extends ToastType {
  onDismiss?: () => void
}

export function Toast({ onDismiss, ...toast }: StandaloneToastProps) {
  const handleDismiss = useCallback(() => {
    onDismiss?.()
  }, [onDismiss])

  return (
    <ToastItem
      toast={toast}
      onDismiss={handleDismiss}
      index={0}
    />
  )
}

export default ToastContainer
