import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useTranslation as useCustomTranslation } from '../i18n/hooks/useTranslation'
import { useAuth } from '../context/AuthContext'
import { WorldHumanBadge } from './agents/WorldHumanBadge'
import { ENSBadge } from './agents/ENSBadge'
import { WorldIdBadge } from './WorldIdVerification'
import { ApplicationResultView } from './ApplicationResultView'
import type { ApplicationResultState } from './ApplicationResultView'
import { applyToTask, ApplicationError } from '../services/tasks'
import type { Task } from '../types/database'
import { getWorldIdBountyThreshold } from '../hooks/usePlatformConfig'

interface TaskApplicationModalProps {
  task: Task
  /** When true, skip the form and show "already applied" state directly */
  hasAlreadyApplied?: boolean
  onClose: () => void
  onSuccess: () => void
}

export function TaskApplicationModal({ task, hasAlreadyApplied, onClose, onSuccess }: TaskApplicationModalProps) {
  const { t } = useTranslation()
  const { formatCurrency, formatTimeRemaining } = useCustomTranslation()
  const { executor } = useAuth()

  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resultState, setResultState] = useState<ApplicationResultState | null>(
    hasAlreadyApplied ? 'already_applied' : null
  )
  const modalRef = useRef<HTMLDivElement>(null)

  // Focus trap - keep focus within modal
  useEffect(() => {
    const modal = modalRef.current
    if (!modal) return

    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    // Focus first element on mount
    firstElement?.focus()

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault()
          lastElement?.focus()
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault()
          firstElement?.focus()
        }
      }
    }

    modal.addEventListener('keydown', handleTabKey)
    return () => modal.removeEventListener('keydown', handleTabKey)
  }, [])

  // Close on escape
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose])

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  const handleSubmit = async () => {
    if (!executor) return

    setSubmitting(true)
    setError(null)

    try {
      // Always go through REST API — enforces World ID, ERC-8004, rate limits
      await applyToTask({
        taskId: task.id,
        executorId: executor.id,
        message: message.trim() || undefined,
      })

      // Determine success state based on World ID status and bounty
      const isHighValue = task.bounty_usd >= getWorldIdBountyThreshold()
      const isWorldIdVerified = executor.world_id_verified === true

      if (!isWorldIdVerified && !isHighValue) {
        setResultState('success_suggest_worldid')
      } else {
        setResultState('success')
      }

      // Notify parent so it can refresh task list
      onSuccess()
    } catch (err) {
      if (err instanceof ApplicationError) {
        if (err.type === 'world_id_required') {
          setResultState('blocked_worldid')
          return
        }
        if (err.type === 'already_applied') {
          setResultState('already_applied')
          return
        }
        setError(err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Failed to apply')
      }
      setResultState('error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRetry = () => {
    setResultState(null)
    setError(null)
  }

  if (!executor) return null

  const location = [executor.location_city, executor.location_country].filter(Boolean).join(', ')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />

      {/* Modal */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="application-modal-title"
        className="relative w-full max-w-lg max-h-[90vh] mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 flex items-center justify-between">
          <h2 id="application-modal-title" className="text-xl font-bold text-gray-900">
            {t('application.title', 'Apply to Task')}
          </h2>
          <button
            onClick={onClose}
            aria-label={t('common.close', 'Close modal')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content — show result view OR application form */}
        {resultState ? (
          <div className="flex-1 overflow-y-auto px-6 pb-4">
            <ApplicationResultView
              state={resultState}
              worldIdThreshold={getWorldIdBountyThreshold()}
              errorMessage={error || undefined}
              onClose={onClose}
              onRetry={handleRetry}
            />
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-5">
              {/* Task summary */}
              <div className="bg-gray-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-900 mb-2">{task.title}</h3>
                <div className="flex items-center gap-4 text-sm">
                  <span className="font-bold text-green-600">{formatCurrency(task.bounty_usd)}</span>
                  <span className="text-gray-400">|</span>
                  <span className="text-gray-500">{formatTimeRemaining(task.deadline)}</span>
                  <span className="text-gray-400">|</span>
                  <span className="text-gray-500">{t(`tasks.categories.${task.category}`)}</span>
                </div>
              </div>

              {/* Profile preview */}
              <div>
                <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
                  {t('application.yourProfile', 'Your Profile')}
                </h4>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
                      {(executor.display_name || 'U')[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-gray-900 truncate flex items-center gap-1.5">
                        {executor.display_name || t('profile.anonymous', 'Anonymous')}
                        <WorldHumanBadge worldHumanId={executor.world_human_id} />
                        <ENSBadge ensName={executor.ens_name || executor.ens_subname} size="sm" />
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <svg className="w-3.5 h-3.5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          {executor.reputation_score}
                        </span>
                        {executor.world_id_verified && (
                          <WorldIdBadge level={executor.world_id_level || 'device'} size="sm" />
                        )}
                        {location && (
                          <>
                            <span className="text-gray-300">|</span>
                            <span>{location}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {executor.bio && (
                    <p className="text-sm text-gray-600 mt-3 line-clamp-2">{executor.bio}</p>
                  )}

                  {executor.skills && executor.skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {executor.skills.slice(0, 6).map((skill: string) => (
                        <span
                          key={skill}
                          className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full"
                        >
                          {skill.replace(/_/g, ' ')}
                        </span>
                      ))}
                      {executor.skills.length > 6 && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">
                          +{executor.skills.length - 6}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Message */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('application.message', 'Message to Agent')}{' '}
                  <span className="text-gray-400 font-normal">({t('common.optional', 'optional')})</span>
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={t(
                    'application.messagePlaceholder',
                    'Why are you a good fit for this task?'
                  )}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
                  rows={3}
                  maxLength={500}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
              >
                {t('common.cancel', 'Cancel')}
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 py-2.5 bg-green-600 text-white font-semibold rounded-xl hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting
                  ? t('common.submitting', 'Submitting...')
                  : t('application.submit', 'Submit Application')}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
