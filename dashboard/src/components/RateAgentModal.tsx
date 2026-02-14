/**
 * RateAgentModal: Multi-step modal for workers to rate agents on-chain.
 *
 * Flow: rating → signing → confirming → complete
 *
 * The worker signs giveFeedback() directly from their wallet.
 * msg.sender on-chain = worker's address (trustless reputation).
 *
 * Star ratings map to the 0-100 backend scale:
 *   1 star = 20, 2 = 40, 3 = 60, 4 = 80, 5 = 100
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useReputationFeedback, type FeedbackStep } from '../hooks/useReputationFeedback'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface RateAgentModalProps {
  /** Task ID associated with this rating */
  taskId: string
  /** Task title for display */
  taskTitle: string
  /** Agent's ERC-8004 token ID (required for on-chain feedback) */
  agentId: number
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

// BaseScan URL for TX links
const BASESCAN_TX_URL = 'https://basescan.org/tx/'

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------

export function RateAgentModal({
  taskId,
  taskTitle,
  agentId,
  agentName,
  onClose,
  onSuccess,
}: RateAgentModalProps) {
  const { t } = useTranslation()
  const modalRef = useRef<HTMLDivElement>(null)

  const [rating, setRating] = useState<number>(0)
  const [hoverRating, setHoverRating] = useState<number>(0)
  const [comment, setComment] = useState('')

  const {
    step,
    txHash,
    error,
    submitFeedback,
    reset,
  } = useReputationFeedback()

  const displayRating = hoverRating || rating
  const isProcessing = step !== 'idle' && step !== 'error' && step !== 'complete'

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

  // ------- Close on Escape (only when not processing) -------
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isProcessing) onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose, isProcessing])

  // ------- Prevent body scroll -------
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  // ------- Auto-close on complete -------
  useEffect(() => {
    if (step === 'complete') {
      const timer = setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [step, onClose, onSuccess])

  // ------- Submit handler -------
  const handleSubmit = useCallback(async () => {
    if (rating === 0) return
    await submitFeedback({
      agentId,
      taskId,
      stars: rating,
      comment: comment.trim() || undefined,
    })
  }, [rating, agentId, taskId, comment, submitFeedback])

  // ------- Retry handler -------
  const handleRetry = useCallback(() => {
    reset()
  }, [reset])

  // ------- Step indicator text -------
  const getStepText = (currentStep: FeedbackStep): string => {
    switch (currentStep) {
      case 'preparing':
        return t('rateAgent.stepPreparing', 'Preparando datos...')
      case 'switching_chain':
        return t('rateAgent.stepSwitchingChain', 'Cambiando a red Base...')
      case 'signing':
        return t('rateAgent.stepSigning', 'Confirma en tu wallet')
      case 'confirming':
        return t('rateAgent.stepConfirming', 'Confirmando transaccion...')
      default:
        return ''
    }
  }

  // ------- Complete state -------
  if (step === 'complete') {
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
            {t('rateAgent.success', 'Calificacion registrada on-chain!')}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {t('rateAgent.successDescription', 'Tu calificacion quedo grabada en la blockchain.')}
          </p>
          {txHash && (
            <a
              href={`${BASESCAN_TX_URL}${txHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-3 text-xs text-blue-600 hover:text-blue-800 underline"
            >
              {t('rateAgent.viewOnBasescan', 'Ver en BaseScan')}
            </a>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={isProcessing ? undefined : onClose}
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
          {!isProcessing && (
            <button
              onClick={onClose}
              aria-label={t('common.close', 'Cerrar')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-5">
          {/* Processing overlay */}
          {isProcessing && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-blue-900">
                    {getStepText(step)}
                  </p>
                  {step === 'signing' && (
                    <p className="text-xs text-blue-600 mt-0.5">
                      {t('rateAgent.gasNote', 'Gas estimado: < $0.01')}
                    </p>
                  )}
                  {step === 'confirming' && txHash && (
                    <a
                      href={`${BASESCAN_TX_URL}${txHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:text-blue-800 underline mt-0.5 inline-block"
                    >
                      {txHash.slice(0, 10)}...{txHash.slice(-6)}
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

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
                  disabled={isProcessing}
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  aria-label={`${star} ${star === 1 ? 'estrella' : 'estrellas'}`}
                  className="p-1 transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded disabled:opacity-50"
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
              disabled={isProcessing}
              placeholder={t(
                'rateAgent.commentPlaceholder',
                'Comparte detalles sobre tu experiencia con este agente...'
              )}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none text-sm disabled:opacity-50"
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
          {error && step === 'error' && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm text-red-700">{error}</p>
                  <button
                    onClick={handleRetry}
                    className="mt-1 text-xs text-red-600 hover:text-red-800 underline"
                  >
                    {t('common.retry', 'Reintentar')}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* On-chain info badge */}
          {step === 'idle' && (
            <div className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
              <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-xs text-gray-500">
                {t('rateAgent.onChainNote', 'Tu calificacion sera registrada en la blockchain de Base. Necesitaras confirmar una transaccion en tu wallet.')}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3">
          {!isProcessing && (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
            >
              {t('rateAgent.skip', 'Omitir')}
            </button>
          )}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={rating === 0 || isProcessing}
            className="flex-1 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          >
            {isProcessing
              ? getStepText(step)
              : t('rateAgent.submit', 'Calificar en Cadena')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default RateAgentModal
