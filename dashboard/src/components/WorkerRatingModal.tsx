/**
 * WorkerRatingModal: Modal for agents to rate workers after task completion.
 *
 * Shows a star rating (1-5), optional comment field, and worker info.
 * Submits to POST /api/v1/reputation/workers/rate.
 *
 * Star ratings map to the 0-100 backend scale:
 *   1 star = 20, 2 = 40, 3 = 60, 4 = 80, 5 = 100
 */

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { rateWorker, starsToScore } from '../services/reputation'
import { WorkerReputationBadge } from './WorkerReputationBadge'
import { safeSrc } from '../lib/safeHref'
import { Modal } from './ui/Modal'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface WorkerInfo {
  id: string
  display_name: string | null
  reputation_score: number
  avatar_url: string | null
  wallet_address: string
}

interface WorkerRatingModalProps {
  /** Task ID associated with this rating */
  taskId: string
  /** Task title for display */
  taskTitle: string
  /** Worker being rated */
  worker: WorkerInfo
  /** Payment transaction hash (for verified on-chain feedback) */
  proofTx?: string | null
  /** Called when modal closes (after submit or cancel) */
  onClose: () => void
  /** Called after successful rating submission */
  onSuccess?: () => void
}

// --------------------------------------------------------------------------
// Star Label Keys (mapped to i18n)
// --------------------------------------------------------------------------

const STAR_LABELS = [
  'rating.stars.1', // Poor
  'rating.stars.2', // Below Average
  'rating.stars.3', // Average
  'rating.stars.4', // Good
  'rating.stars.5', // Excellent
] as const

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------

export function WorkerRatingModal({
  taskId,
  taskTitle,
  worker,
  proofTx,
  onClose,
  onSuccess,
}: WorkerRatingModalProps) {
  const { t } = useTranslation()

  const [rating, setRating] = useState<number>(0)
  const [hoverRating, setHoverRating] = useState<number>(0)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const displayRating = hoverRating || rating
  const workerName = worker.display_name || t('profile.anonymous', 'Anonymous')

  const handleSubmit = useCallback(async () => {
    if (rating === 0) return

    setSubmitting(true)
    setError(null)

    try {
      await rateWorker({
        task_id: taskId,
        score: starsToScore(rating),
        comment: comment.trim() || undefined,
        proof_tx: proofTx || undefined,
        worker_address: worker.wallet_address || undefined,
      })

      setSuccess(true)

      // Auto-close after brief success feedback
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1500)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t('errors.generic', 'An error occurred')
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }, [rating, taskId, comment, proofTx, worker.wallet_address, onClose, onSuccess, t])

  // ------- Success state -------
  if (success) {
    return (
      <Modal
        open
        onClose={onClose}
        size="sm"
        ariaLabel={t('rating.success', 'Rating submitted!')}
      >
        <Modal.Body className="p-8 text-center">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-zinc-900">
            {t('rating.success', 'Rating submitted!')}
          </h3>
          <p className="text-sm text-zinc-500 mt-1">
            {t('rating.successDescription', 'Your feedback helps build a better marketplace.')}
          </p>
        </Modal.Body>
      </Modal>
    )
  }

  return (
    <Modal
      open
      onClose={onClose}
      size="md"
      labelledBy="rating-modal-title"
      dismissOnEsc={!submitting}
      dismissOnBackdrop={!submitting}
    >
      <Modal.Header onClose={submitting ? undefined : onClose}>
        <h2 id="rating-modal-title" className="text-lg font-bold text-zinc-900">
          {t('rating.title', 'Rate Worker')}
        </h2>
      </Modal.Header>

      <Modal.Body className="space-y-5">
        {/* Worker info */}
        <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-xl">
          <div className="w-12 h-12 bg-zinc-900 rounded-full flex items-center justify-center flex-shrink-0">
            {worker.avatar_url ? (
              <img
                src={safeSrc(worker.avatar_url)}
                alt={workerName}
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              <span className="text-white font-bold text-lg">
                {workerName[0].toUpperCase()}
              </span>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-zinc-900 truncate">{workerName}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <WorkerReputationBadge score={worker.reputation_score} />
              <span className="text-xs text-zinc-400 truncate">
                {worker.wallet_address.slice(0, 6)}...{worker.wallet_address.slice(-4)}
              </span>
            </div>
          </div>
        </div>

        {/* Task reference */}
        <div className="text-sm text-zinc-500">
          <span className="font-medium text-zinc-700">
            {t('rating.forTask', 'For task:')}
          </span>{' '}
          {taskTitle}
        </div>

        {/* Star rating */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 mb-2">
            {t('rating.ratingLabel', 'How did this worker perform?')}
          </label>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRating(star)}
                onMouseEnter={() => setHoverRating(star)}
                onMouseLeave={() => setHoverRating(0)}
                aria-label={`${star} ${star === 1 ? 'star' : 'stars'}`}
                className="p-1 transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-1 rounded"
              >
                <svg
                  className={`w-8 h-8 transition-colors ${
                    star <= displayRating ? 'text-amber-400' : 'text-zinc-200'
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
            <p className="text-sm text-zinc-500 mt-1">
              {t(STAR_LABELS[displayRating - 1], '')}
            </p>
          )}
        </div>

        {/* Comment */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 mb-1">
            {t('rating.commentLabel', 'Feedback')}{' '}
            <span className="text-zinc-400 font-normal">
              ({t('common.optional', 'optional')})
            </span>
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t(
              'rating.commentPlaceholder',
              'Share details about the worker\'s performance...'
            )}
            className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none resize-none text-sm"
            rows={3}
            maxLength={1000}
          />
          {comment.length > 0 && (
            <p className="text-xs text-zinc-400 text-right mt-0.5">
              {comment.length}/1000
            </p>
          )}
        </div>

        {/* On-chain info */}
        {proofTx && (
          <div className="flex items-center gap-2 p-2 bg-zinc-50 border border-zinc-200 rounded-lg">
            <svg
              className="w-4 h-4 text-zinc-700 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-xs text-zinc-700">
              {t('rating.onChainVerified', 'This rating will be recorded on-chain via ERC-8004')}
            </span>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-2">
              <svg
                className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-sm text-red-700">{error}</p>
                <button
                  onClick={() => setError(null)}
                  className="mt-1 text-xs text-red-600 hover:text-red-800 underline"
                >
                  {t('common.retry', 'Retry')}
                </button>
              </div>
            </div>
          </div>
        )}
      </Modal.Body>

      <Modal.Footer className="bg-zinc-50">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2.5 text-sm font-medium text-zinc-700 hover:text-zinc-900 transition-colors"
        >
          {t('rating.skip', 'Skip')}
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={rating === 0 || submitting}
          className="flex-1 py-2.5 bg-zinc-900 text-white font-semibold rounded-xl hover:bg-zinc-800 disabled:bg-zinc-100 disabled:text-zinc-400 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {submitting
            ? t('common.submitting', 'Submitting...')
            : t('rating.submit', 'Submit Rating')}
        </button>
      </Modal.Footer>
    </Modal>
  )
}

export default WorkerRatingModal
