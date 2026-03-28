import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import type { ReactNode } from 'react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastItem {
  id: string
  type: ToastType
  message: string
  createdAt: number
}

interface ToastAPI {
  success: (message: string) => void
  error: (message: string) => void
  warning: (message: string) => void
  info: (message: string) => void
}

interface ToastContextValue {
  toast: ToastAPI
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a <ToastProvider>')
  }
  return ctx
}

// ---------------------------------------------------------------------------
// Style helpers
// ---------------------------------------------------------------------------

const DURATION_MS = 5000
const MAX_VISIBLE = 3

const TYPE_STYLES: Record<ToastType, { border: string; bar: string; icon: ReactNode }> = {
  success: {
    border: 'border-l-green-500',
    bar: 'bg-green-500',
    icon: (
      <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    ),
  },
  error: {
    border: 'border-l-red-500',
    bar: 'bg-red-500',
    icon: (
      <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
  },
  warning: {
    border: 'border-l-yellow-500',
    bar: 'bg-yellow-500',
    icon: (
      <svg className="w-5 h-5 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86l-8.58 14.86A1 1 0 002.57 20h18.86a1 1 0 00.86-1.28l-8.58-14.86a1 1 0 00-1.72 0z" />
      </svg>
    ),
  },
  info: {
    border: 'border-l-blue-500',
    bar: 'bg-blue-500',
    icon: (
      <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01" />
        <circle cx="12" cy="12" r="10" strokeWidth={2} fill="none" />
      </svg>
    ),
  },
}

// ---------------------------------------------------------------------------
// Single toast component
// ---------------------------------------------------------------------------

function ToastCard({ item, onDismiss }: { item: ToastItem; onDismiss: (id: string) => void }) {
  const [visible, setVisible] = useState(false)
  const [exiting, setExiting] = useState(false)
  const style = TYPE_STYLES[item.type]

  // Enter animation
  useEffect(() => {
    const frame = requestAnimationFrame(() => setVisible(true))
    return () => cancelAnimationFrame(frame)
  }, [])

  // Auto-dismiss
  useEffect(() => {
    const timeout = setTimeout(() => {
      setExiting(true)
      setTimeout(() => onDismiss(item.id), 300)
    }, DURATION_MS)
    return () => clearTimeout(timeout)
  }, [item.id, onDismiss])

  const handleDismiss = () => {
    setExiting(true)
    setTimeout(() => onDismiss(item.id), 300)
  }

  const translateClass = visible && !exiting
    ? 'translate-x-0 opacity-100'
    : 'translate-x-full opacity-0'

  return (
    <div
      className={`
        relative overflow-hidden rounded-lg border-l-4 bg-gray-800 shadow-lg
        ${style.border}
        transition-all duration-300 ease-in-out
        ${translateClass}
        min-w-[320px] max-w-[420px]
      `}
      role="alert"
    >
      <div className="flex items-start gap-3 px-4 py-3">
        {/* Icon */}
        <div className="flex-shrink-0 mt-0.5">{style.icon}</div>

        {/* Message */}
        <p className="flex-1 text-sm text-white leading-snug">{item.message}</p>

        {/* Dismiss */}
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 text-gray-400 hover:text-white transition-colors"
          aria-label="Dismiss"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-700">
        <div
          className={`h-full ${style.bar}`}
          style={{
            animation: `toast-progress ${DURATION_MS}ms linear forwards`,
          }}
        />
      </div>

      {/* Inline keyframes — injected once via style tag in provider */}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

let idCounter = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const toastsRef = useRef(toasts)
  toastsRef.current = toasts

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = `toast-${++idCounter}-${Date.now()}`
    const item: ToastItem = { id, type, message, createdAt: Date.now() }

    setToasts((prev) => {
      const next = [...prev, item]
      // Keep only the most recent MAX_VISIBLE
      if (next.length > MAX_VISIBLE) {
        return next.slice(next.length - MAX_VISIBLE)
      }
      return next
    })
  }, [])

  const api = useRef<ToastAPI>({
    success: (msg) => addToast('success', msg),
    error: (msg) => addToast('error', msg),
    warning: (msg) => addToast('warning', msg),
    info: (msg) => addToast('info', msg),
  })

  // Keep api callbacks in sync with latest addToast
  useEffect(() => {
    api.current.success = (msg) => addToast('success', msg)
    api.current.error = (msg) => addToast('error', msg)
    api.current.warning = (msg) => addToast('warning', msg)
    api.current.info = (msg) => addToast('info', msg)
  }, [addToast])

  const contextValue = useRef<ToastContextValue>({ toast: api.current })

  return (
    <ToastContext.Provider value={contextValue.current}>
      {children}

      {/* Global keyframes for progress bar animation */}
      <style>{`
        @keyframes toast-progress {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>

      {/* Toast container — top-right, stacked */}
      <div
        className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <ToastCard item={t} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
