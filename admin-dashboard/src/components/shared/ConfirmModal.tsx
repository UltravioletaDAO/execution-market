import { useState, useCallback } from 'react'

interface ConfirmModalProps {
  isOpen: boolean
  onConfirm: () => void | Promise<void>
  onCancel: () => void
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'danger'
}

export default function ConfirmModal({
  isOpen,
  onConfirm,
  onCancel,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
}: ConfirmModalProps) {
  const [loading, setLoading] = useState(false)

  const handleConfirm = useCallback(async () => {
    setLoading(true)
    try {
      await onConfirm()
    } finally {
      setLoading(false)
    }
  }, [onConfirm])

  if (!isOpen) return null

  const confirmButtonClass =
    variant === 'danger'
      ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
      : 'bg-em-600 hover:bg-em-700 focus:ring-em-500'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onCancel}
      />

      {/* Card */}
      <div className="relative bg-gray-800 rounded-lg shadow-xl max-w-md w-full border border-gray-700">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <p className="mt-2 text-sm text-gray-400">{message}</p>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-700">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-gray-700 hover:bg-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={loading}
            className={`px-4 py-2 text-sm font-medium text-white rounded focus:outline-none focus:ring-2 disabled:opacity-50 ${confirmButtonClass}`}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Processing...
              </span>
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
