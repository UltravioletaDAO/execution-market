import { useState } from 'react'
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
import {
  getWorldIdBountyThreshold,
  getVeryAiBountyFloor,
} from '../hooks/usePlatformConfig'
import { isVeryAiEnabled } from '../utils/featureFlags'
import { Pill } from './ui/Pill'
import { Modal } from './ui/Modal'

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

  const handleSubmit = async () => {
    if (!executor) return

    // Pre-check tier (Task 3.4): tasks in T1 band ($50 - <$500) need either
    // VeryAI palm OR World ID Orb. Show dual-CTA upfront when VeryAI is on
    // and the worker has neither — fastest path wins. T2 (>=$500) stays a
    // single-Orb CTA, handled reactively by the backend's world_id_required.
    const t2Threshold = getWorldIdBountyThreshold()
    const t1Floor = getVeryAiBountyFloor()
    const inT1Band = task.bounty_usd >= t1Floor && task.bounty_usd < t2Threshold
    const hasOrb =
      executor.world_id_verified === true && executor.world_id_level === 'orb'
    const hasPalm = executor.veryai_verified === true
    if (inT1Band && isVeryAiEnabled() && !hasOrb && !hasPalm) {
      setResultState('blocked_t1_dual')
      return
    }

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
      const isHighValue = task.bounty_usd >= t2Threshold
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
    <Modal
      open
      onClose={onClose}
      size="md"
      labelledBy="application-modal-title"
      className="max-w-lg"
    >
      <Modal.Header onClose={onClose}>
        <h2 id="application-modal-title" className="text-xl font-bold text-zinc-900">
          {t('application.title', 'Apply to Task')}
        </h2>
      </Modal.Header>

      {/* Content — show result view OR application form */}
      {resultState ? (
        <Modal.Body>
          <ApplicationResultView
            state={resultState}
            worldIdThreshold={getWorldIdBountyThreshold()}
            veryAiFloor={getVeryAiBountyFloor()}
            errorMessage={error || undefined}
            onClose={onClose}
            onRetry={handleRetry}
          />
        </Modal.Body>
      ) : (
        <>
          <Modal.Body className="space-y-5">
              {/* Task summary */}
              <div className="bg-zinc-50 rounded-xl p-4">
                <h3 className="font-semibold text-zinc-900 mb-2">{task.title}</h3>
                <div className="flex items-center gap-4 text-sm">
                  <span className="font-bold text-zinc-900">{formatCurrency(task.bounty_usd)}</span>
                  <span className="text-zinc-400">|</span>
                  <span className="text-zinc-600">{formatTimeRemaining(task.deadline)}</span>
                  <span className="text-zinc-400">|</span>
                  <span className="text-zinc-600">{t(`tasks.categories.${task.category}`)}</span>
                </div>
              </div>

              {/* Profile preview */}
              <div>
                <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-3">
                  {t('application.yourProfile', 'Your Profile')}
                </h4>
                <div className="bg-white border border-zinc-200 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-zinc-900 rounded-full flex items-center justify-center text-white font-bold text-lg">
                      {(executor.display_name || 'U')[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-zinc-900 truncate flex items-center gap-1.5">
                        {executor.display_name || t('profile.anonymous', 'Anonymous')}
                        <WorldHumanBadge worldHumanId={executor.world_human_id} />
                        <ENSBadge ensName={executor.ens_name || executor.ens_subname} size="sm" />
                      </div>
                      <div className="flex items-center gap-2 text-sm text-zinc-600">
                        <span className="flex items-center gap-1">
                          <svg className="w-3.5 h-3.5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          {executor.reputation_score}
                        </span>
                        {executor.world_id_verified && (
                          <WorldIdBadge level={executor.world_id_level || 'device'} size="sm" />
                        )}
                        {location && (
                          <>
                            <span className="text-zinc-400">|</span>
                            <span>{location}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {executor.bio && (
                    <p className="text-sm text-zinc-700 mt-3 line-clamp-2">{executor.bio}</p>
                  )}

                  {executor.skills && executor.skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {executor.skills.slice(0, 6).map((skill: string) => (
                        <Pill key={skill} variant="default" size="sm" asSpan>
                          {skill.replace(/_/g, ' ')}
                        </Pill>
                      ))}
                      {executor.skills.length > 6 && (
                        <Pill variant="default" size="sm" asSpan>
                          +{executor.skills.length - 6}
                        </Pill>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Message */}
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-1">
                  {t('application.message', 'Message to Agent')}{' '}
                  <span className="text-zinc-500 font-normal">({t('common.optional', 'optional')})</span>
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={t(
                    'application.messagePlaceholder',
                    'Why are you a good fit for this task?'
                  )}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none resize-none"
                  rows={3}
                  maxLength={500}
                />
              </div>
          </Modal.Body>

          <Modal.Footer className="bg-zinc-50">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-medium text-zinc-700 hover:text-zinc-900 transition-colors"
            >
              {t('common.cancel', 'Cancel')}
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="flex-1 py-2.5 bg-zinc-900 text-white font-semibold rounded-xl hover:bg-zinc-800 disabled:bg-zinc-100 disabled:text-zinc-400 disabled:cursor-not-allowed transition-colors"
            >
              {submitting
                ? t('common.submitting', 'Submitting...')
                : t('application.submit', 'Submit Application')}
            </button>
          </Modal.Footer>
        </>
      )}
    </Modal>
  )
}
