/**
 * RateAgentModal: Modal for workers to rate agents after task completion.
 *
 * Shows a star rating (1-5), optional comment field, and agent info.
 * Submits to POST /api/v1/reputation/agents/rate.
 *
 * Star ratings map to the 0-100 backend scale:
 *   1 star = 20, 2 = 40, 3 = 60, 4 = 80, 5 = 100
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { rateAgent, starsToScore } from '../services/reputation'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface RateAgentModalProps {
  /** Task ID associated with this rating */
  taskId: string
  /** Task title for display */
  taskTitle: string
  /** Agent identifier (wallet or display name) */
  agentName?: string
  /** Called when modal closes (after submit or cancel) */
  onClose: () => void
  /** Called after successful rating submission */
  onSuccess?: () => void
}

// --------------------------------------------------------------------------
// Star Label Keys (mapped to i18n)
// --------------------------------------------------------------------------

const STAR_LABELS = [
  'rating.stars.1',
  'rating.stars.2',
  'rating.stars.3',
  'rating.stars.4',
  'rating.stars.5',
] as const

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------

export function RateAgentModal({
  taskId,
  taskTitle,
  agentName,
  onClose,
  onSuccess,
}: RateAgentModalProps) {
  const { t } = useTranslation()
  const modalRef = useRef<HTMLDivElement>(null)

  const [rating, setRating] = useState<number>(0)
  const [hoverRating, setHoverRating] = useState<number>(0)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const displayRating = hoverRating || rating

  // ------- Accessibility: Focus trap -------
  useEffect(() => {
    const modal = modalRef.current
    if (!modal) return

    const focusable = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    first?.focus()

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault()
          last?.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first?.focus()
        }
      }
    }

    modal.addEventListener('keydown', handleTab)
    return () => modal.removeEventListener('keydown', handleTab)
  }, [])

  // ------- Close on Escape -------
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose])

  // ------- Prevent body scroll -------
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  // ------- Submit handler -------
  const handleSubmit = useCallback(async () => {
    if (rating === 0) return

    setSubmitting(true)
    setError(null)

    try {
      await rateAgent({
        task_id: taskId,
        score: starsToScore(rating),
        comment: comment.trim() || undefined,
      })

      setSuccess(true)

      // Auto-close after brief success feedback
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1500)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t('errors.generic', 'Ocurrio un error')
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }, [rating, taskId, comment, onClose, onSuccess, t])

  // ------- Success state -------
  if (success) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" aria-hidden="true" />
        <div className="relative w-full max-w-sm mx-4 bg-white rounded-2xl shadow-2xl p-8 text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-gray-900">
            {t('rateAgent.success', 'Calificacion enviada!')}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {t('rateAgent.successDescription', 'Tu opinion ayuda a mejorar la plataforma.')}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="rate-agent-modal-title"
        className="relative w-full max-w-md max-h-[90vh] mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 flex items-center justify-between">
          <h2
            id="rate-agent-modal-title"
            className="text-lg font-bold text-gray-900"
          >
            {t('rateAgent.title', 'Calificar Agente')}
          </h2>
          <button
            onClick={onClose}
            aria-label={t('common.close', 'Cerrar')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-5">
          {/* Agent info */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
            <div className="w-12 h-12 bg-blue-200 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-blue-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-900 truncate">
                {agentName || t('rateAgent.defaultAgentName', 'Agente de IA')}
              </p>
              <span className="text-xs text-gray-400">
                {t('rateAgent.agentLabel', 'Publicador de la tarea')}
              </span>
            </div>
          </div>

          {/* Task reference */}
          <div className="text-sm text-gray-500">
            <span className="font-medium text-gray-700">
              {t('rating.forTask', 'Para la tarea:')}
            </span>{' '}
            {taskTitle}
          </div>

          {/* Star rating */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('rateAgent.ratingLabel', 'Como fue tu experiencia con este agente?')}
            </label>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  aria-label={`${star} ${star === 1 ? 'estrella' : 'estrellas'}`}
                  className="p-1 transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded"
                >
                  <svg
                    className={`w-8 h-8 transition-colors ${
                      star <= displayRating
                        ? 'text-amber-400'
                        : 'text-gray-200'
                    }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                </button>
              ))}
            </div>
            {displayRating > 0 && (
              <p className="text-sm text-gray-500 mt-1">
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {t(STAR_LABELS[displayRating - 1] as any, '')}
              </p>
            )}
          </div>

          {/* Comment */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('rateAgent.commentLabel', 'Comentario')}{' '}
              <span className="text-gray-400 font-normal">
                ({t('common.optional', 'opcional')})
              </span>
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t(
                'rateAgent.commentPlaceholder',
                'Comparte detalles sobre tu experiencia con este agente...'
              )}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none text-sm"
              rows={3}
              maxLength={1000}
            />
            {comment.length > 0 && (
              <p className="text-xs text-gray-400 text-right mt-0.5">
                {comment.length}/1000
              </p>
            )}
          </div>

          {/* Error message */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm text-red-700">{error}</p>
                  <button
                    onClick={() => setError(null)}
                    className="mt-1 text-xs text-red-600 hover:text-red-800 underline"
                  >
                    {t('common.retry', 'Reintentar')}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
          >
            {t('rateAgent.skip', 'Omitir')}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={rating === 0 || submitting}
            className="flex-1 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          >
            {submitting
              ? t('common.submitting', 'Enviando...')
              : t('rateAgent.submit', 'Calificar Agente')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default RateAgentModal
