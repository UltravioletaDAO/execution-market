/**
 * RateAgentModal: Modal for workers to rate agents via REST API.
 *
 * Uses POST /api/v1/reputation/agents/rate (same as mobile app).
 * The backend handles on-chain ERC-8004 feedback registration.
 *
 * Score is 0-100 scale with quick presets at 20, 40, 60, 80, 100.
 */

import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

interface RateAgentModalProps {
  taskId: string
  taskTitle: string
  agentId: number
  agentName?: string
  onClose: () => void
  onSuccess?: () => void
}

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

  const [score, setScore] = useState(80)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const scoreTextClass =
    score >= 80 ? 'text-zinc-900' : score >= 50 ? 'text-amber-700' : 'text-red-700'
  const scoreAccentColor =
    score >= 80 ? '#18181b' : score >= 50 ? '#b45309' : '#b91c1c'

  // Close on Escape
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose, submitting])

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  async function handleSubmit() {
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/reputation/agents/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          task_id: taskId,
          score,
          comment: comment.trim() || undefined,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Error ${res.status}`)
      }
      setSuccess(true)
      // Brief delay so user sees the success state, then notify parent.
      // Parent handles closing + query invalidation via onSuccess.
      setTimeout(() => {
        onSuccess?.()
      }, 1500)
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Unknown error'
      const friendlyMessages: [RegExp, string][] = [
        [/does not match/, t('ratings.errorAgentMismatch', 'Unable to rate this agent. Please refresh the page and try again.')],
        [/already submitted|already rated/i, t('ratings.errorAlreadyRated', 'You have already rated this agent for this task.')],
        [/cannot be rated/i, t('ratings.errorNotReady', 'This task cannot be rated yet.')],
        [/not found/i, t('ratings.errorNotFound', 'Agent or task not found.')],
        [/503|unavailable/i, t('ratings.errorUnavailable', 'Rating service is temporarily unavailable. Please try again later.')],
      ]
      const friendly = friendlyMessages.find(([re]) => re.test(errorMsg))?.[1]
      setError(friendly || errorMsg)
    } finally {
      setSubmitting(false)
    }
  }

  // Success state
  if (success) {
    return createPortal(
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" aria-hidden="true" />
        <div className="relative w-full max-w-sm mx-4 bg-white rounded-2xl shadow-2xl p-8 text-center">
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 bg-green-50">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-zinc-900">
            {t('rateAgent.success', 'Rating submitted!')}
          </h3>
          <p className="text-sm text-zinc-500 mt-1">
            {t('rateAgent.successDescription', 'Your rating has been recorded on-chain via ERC-8004.')}
          </p>
        </div>
      </div>,
      document.body
    )
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={submitting ? undefined : onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-md max-h-[90vh] mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-zinc-900">
              {t('rateAgent.title', 'Rate Agent')}
            </h2>
            {agentName && (
              <p className="text-sm text-zinc-500">{agentName}</p>
            )}
          </div>
          {!submitting && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="p-2 hover:bg-zinc-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-5">
          {/* Task reference */}
          <p className="text-sm text-zinc-500">
            <span className="font-medium text-zinc-700">{t('rating.forTask', 'Task:')}</span>{' '}
            {taskTitle}
          </p>

          {/* Score display */}
          <div className="text-center">
            <span className={`text-5xl font-extrabold ${scoreTextClass}`}>{score}</span>
            <span className="text-lg text-zinc-500">/100</span>
          </div>

          {/* Slider */}
          <div className="px-2">
            <input
              type="range"
              min={0}
              max={100}
              value={score}
              onChange={(e) => setScore(Number(e.target.value))}
              disabled={submitting}
              className="w-full h-2 rounded-lg appearance-none cursor-pointer"
              style={{ accentColor: scoreAccentColor }}
            />
            <div className="flex justify-between text-xs text-zinc-500 mt-1">
              <span>0</span>
              <span>50</span>
              <span>100</span>
            </div>
          </div>

          {/* Quick presets */}
          <div className="flex justify-center gap-2">
            {[20, 40, 60, 80, 100].map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => setScore(preset)}
                disabled={submitting}
                className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
                  score === preset
                    ? 'bg-zinc-900 text-white'
                    : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200'
                } disabled:bg-zinc-100 disabled:text-zinc-400 disabled:cursor-not-allowed`}
              >
                {preset}
              </button>
            ))}
          </div>

          {/* Comment */}
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={submitting}
            placeholder={t('rateAgent.commentPlaceholder', 'Optional comment about your experience...')}
            className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-500 focus:border-zinc-500 outline-none resize-none text-sm disabled:bg-zinc-100 disabled:text-zinc-400 disabled:cursor-not-allowed"
            rows={3}
            maxLength={1000}
          />

          {/* Error */}
          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-300">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-zinc-200 bg-zinc-50 flex gap-3">
          {!submitting && (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-medium text-zinc-600 hover:text-zinc-900 transition-colors"
            >
              {t('common.cancel', 'Cancel')}
            </button>
          )}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 py-2.5 bg-zinc-900 text-white font-semibold rounded-xl hover:bg-zinc-800 disabled:bg-zinc-100 disabled:text-zinc-400 disabled:cursor-not-allowed transition-colors text-sm"
          >
            {submitting
              ? t('rateAgent.submitting', 'Submitting...')
              : t('rateAgent.submit', 'Submit Rating')}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

export default RateAgentModal
