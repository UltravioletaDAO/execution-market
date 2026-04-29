/**
 * SubmissionReviewModal: Modal for agents to review, approve, or reject submissions.
 *
 * Shows submission evidence, worker info, and provides actions:
 * - Approve (triggers payment via API)
 * - Reject (with feedback)
 * - Request More Info
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { getCheckLabel } from '../constants/checkLabels'
import { getSubmission, approveSubmission, rejectSubmission, requestMoreInfo } from '../services/submissions'
import { AIAnalysisDetails } from './AIAnalysisDetails'
import type { AIAnalysisResult } from './AIAnalysisDetails'
import type { SubmissionWithDetails } from '../services/types'
import { ArbiterVerdictBadge } from './ArbiterVerdictBadge'
import { ForensicEventLog } from './ForensicEventLog'
import type { VerificationEvent } from './ForensicEventLog'
import { safeHref, safeSrc } from '../lib/safeHref'
import { Modal } from './ui/Modal'

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface SubmissionReviewModalProps {
  submissionId: string
  onClose: () => void
  onSuccess?: () => void
}

type ReviewAction = 'idle' | 'approving' | 'rejecting' | 'requesting_info'

interface AutoCheckDetails {
  score?: number
  phase?: string
  checks?: Record<string, boolean>
  verification_events?: VerificationEvent[]
  [key: string]: unknown
}

// --------------------------------------------------------------------------
// GPS Badge — hides coordinates behind a toggle (PII protection for streams)
// --------------------------------------------------------------------------

function GpsBadge({ gps }: { gps: { latitude?: number; lat?: number; longitude?: number; lng?: number } }) {
  const { t } = useTranslation()
  const [show, setShow] = useState(false)
  const lat = Number(gps.latitude || gps.lat)
  const lng = Number(gps.longitude || gps.lng)
  return show ? (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700">
        GPS: {lat.toFixed(4)}, {lng.toFixed(4)}
      </span>
      <button
        type="button"
        onClick={() => setShow(false)}
        className="inline-flex items-center gap-0.5 text-zinc-700 hover:underline"
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
        </svg>
        {t('gps.hideCoordinates', 'Hide coordinates')}
      </button>
    </span>
  ) : (
    <button
      type="button"
      onClick={() => setShow(true)}
      className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 hover:bg-zinc-200 transition-colors"
    >
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
      </svg>
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
      {t('gps.showCoordinates', 'Show coordinates')}
    </button>
  )
}

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------

export function SubmissionReviewModal({ submissionId, onClose, onSuccess }: SubmissionReviewModalProps) {
  const { t } = useTranslation()
  const { executor } = useAuth()
  const [submission, setSubmission] = useState<SubmissionWithDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState<ReviewAction>('idle')
  const [feedback, setFeedback] = useState('')
  const [approveNotes, setApproveNotes] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [showInfoForm, setShowInfoForm] = useState(false)
  const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Load submission data
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        setError(null)
        const data = await getSubmission(submissionId)
        if (!cancelled) {
          if (!data) {
            setError('Submission not found')
          } else {
            setSubmission(data)
          }
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load submission')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [submissionId])

  // Poll for Phase B completion (auto_check_details.phase transitions from "A" to "AB")
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const currentPhase = (submission?.auto_check_details as { phase?: string } | null)?.phase
  const hasVerdict = submission?.agent_verdict
  const hasAiResult = submission?.ai_verification_result

  // Check forensic event log completion
  const forensicEvents = (submission?.auto_check_details as AutoCheckDetails | null)?.verification_events
  const forensicComplete = Array.isArray(forensicEvents) && forensicEvents.length > 0 &&
    forensicEvents.some((e) => e.step === 'ring1_complete' && (e.status === 'complete' || e.status === 'failed')) &&
    (!forensicEvents.some((e) => e.ring === 2) ||
      forensicEvents.some((e) => e.step === 'ring2_complete' && (e.status === 'complete' || e.status === 'failed')))

  useEffect(() => {
    if (!submission) return
    // Stop polling if Phase B is already complete, submission has verdict, or forensic events are done
    if (currentPhase === 'AB' || hasVerdict || hasAiResult || forensicComplete) return

    pollingRef.current = setInterval(async () => {
      try {
        const updated = await getSubmission(submissionId)
        if (!updated) return
        setSubmission(updated)
        const updatedPhase = (updated.auto_check_details as { phase?: string } | null)?.phase
        const updatedEvents = (updated.auto_check_details as AutoCheckDetails | null)?.verification_events
        const updatedForensicDone = Array.isArray(updatedEvents) && updatedEvents.length > 0 &&
          updatedEvents.some((e) => e.step === 'ring1_complete' && (e.status === 'complete' || e.status === 'failed')) &&
          (!updatedEvents.some((e) => e.ring === 2) ||
            updatedEvents.some((e) => e.step === 'ring2_complete' && (e.status === 'complete' || e.status === 'failed')))
        if (updatedPhase === 'AB' || updated.ai_verification_result || updatedForensicDone) {
          if (pollingRef.current) clearInterval(pollingRef.current)
        }
      } catch {
        // Silently ignore polling errors
      }
    }, 5000)

    const timeout = setTimeout(() => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }, 60000) // stop after 60s

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
      clearTimeout(timeout)
    }
  }, [submission, currentPhase, hasVerdict, hasAiResult, submissionId])

  const handleApprove = useCallback(async () => {
    if (!executor?.id || !submission) return
    setAction('approving')
    setResult(null)
    try {
      await approveSubmission({
        submissionId: submission.id,
        agentId: executor.id,
        verdict: 'accepted',
        notes: approveNotes || undefined,
      })
      setResult({ type: 'success', message: 'Submission approved. Payment is being processed.' })
      onSuccess?.()
    } catch (err: unknown) {
      setResult({ type: 'error', message: err instanceof Error ? err.message : 'Failed to approve submission' })
    } finally {
      setAction('idle')
    }
  }, [executor?.id, submission, approveNotes, onSuccess])

  const handleReject = useCallback(async () => {
    if (!executor?.id || !submission || !feedback.trim()) return
    setAction('rejecting')
    setResult(null)
    try {
      await rejectSubmission({
        submissionId: submission.id,
        agentId: executor.id,
        feedback: feedback.trim(),
      })
      setResult({ type: 'success', message: 'Submission rejected.' })
      onSuccess?.()
    } catch (err: unknown) {
      setResult({ type: 'error', message: err instanceof Error ? err.message : 'Failed to reject submission' })
    } finally {
      setAction('idle')
    }
  }, [executor?.id, submission, feedback, onSuccess])

  const handleRequestInfo = useCallback(async () => {
    if (!executor?.id || !submission || !feedback.trim()) return
    setAction('requesting_info')
    setResult(null)
    try {
      await requestMoreInfo(submission.id, executor.id, feedback.trim())
      setResult({ type: 'success', message: 'More information requested. Worker will be notified.' })
      onSuccess?.()
    } catch (err: unknown) {
      setResult({ type: 'error', message: err instanceof Error ? err.message : 'Failed to request more info' })
    } finally {
      setAction('idle')
    }
  }, [executor?.id, submission, feedback, onSuccess])

  const isProcessing = action !== 'idle'

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      labelledBy="submission-review-title"
      dismissOnEsc={!isProcessing}
      dismissOnBackdrop={!isProcessing}
    >
      <Modal.Header onClose={isProcessing ? undefined : onClose}>
        <h2 id="submission-review-title" className="text-lg font-semibold text-zinc-900">
          {t('submissionReview.title', 'Review Submission')}
        </h2>
      </Modal.Header>

      <Modal.Body className="space-y-5">
          {/* Loading state */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <svg className="animate-spin h-6 w-6 text-zinc-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="ml-3 text-zinc-500">{t('submissionReview.loading', 'Loading submission...')}</span>
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {/* Submission content */}
          {submission && !loading && (
            <>
              {/* Task info */}
              <div className="bg-zinc-50 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">{t('submissionReview.task', 'Task')}</p>
                    <p className="font-medium text-zinc-900">{submission.task?.title || 'Unknown Task'}</p>
                    {submission.task?.bounty_usd && (
                      <p className="text-sm text-zinc-900 font-semibold mt-1">
                        ${submission.task.bounty_usd.toFixed(2)} USDC
                      </p>
                    )}
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    submission.agent_verdict === 'accepted'
                      ? 'bg-zinc-900 text-white'
                      : submission.agent_verdict === 'disputed'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-amber-100 text-amber-800'
                  }`}>
                    {submission.agent_verdict || t('status.pending')}
                  </span>
                </div>
              </div>

              {/* Worker info */}
              {submission.executor && (
                <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg">
                  <div className="w-10 h-10 bg-zinc-900 rounded-full flex items-center justify-center text-white font-bold text-sm">
                    {submission.executor.display_name?.[0]?.toUpperCase() || 'W'}
                  </div>
                  <div>
                    <p className="font-medium text-zinc-900 text-sm">
                      {submission.executor.display_name || 'Anonymous Worker'}
                    </p>
                    <p className="text-xs text-zinc-500">
                      Rep: {submission.executor.reputation_score ?? 0} | {submission.executor.wallet_address?.slice(0, 6)}...{submission.executor.wallet_address?.slice(-4)}
                    </p>
                  </div>
                </div>
              )}

              {/* Evidence */}
              <div>
                <h3 className="text-sm font-medium text-zinc-700 mb-2">{t('tasks.evidence')}</h3>
                {submission.evidence && typeof submission.evidence === 'object' ? (
                  <div className="space-y-3">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {Object.entries(submission.evidence as Record<string, any>).map(([key, ev]) => (
                      <div key={key} className="border border-zinc-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-zinc-500 uppercase tracking-wide">{key}</p>
                          {ev?.type && (
                            <span className="text-xs bg-zinc-100 text-zinc-500 px-1.5 py-0.5 rounded">
                              {ev.type}
                            </span>
                          )}
                        </div>
                        {ev?.fileUrl ? (
                          <div>
                            {ev.mimeType?.startsWith('image/') || ev.fileUrl?.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                              <a href={safeHref(ev.fileUrl)} target="_blank" rel="noopener noreferrer">
                                <img
                                  src={safeSrc(ev.fileUrl)}
                                  alt={key}
                                  className="max-w-full max-h-64 rounded-lg object-contain hover:opacity-90 transition-opacity cursor-zoom-in"
                                />
                              </a>
                            ) : ev.mimeType?.startsWith('video/') ? (
                              <video
                                src={safeSrc(ev.fileUrl)}
                                controls
                                className="max-w-full max-h-64 rounded-lg"
                              />
                            ) : (
                              <a
                                href={safeHref(ev.fileUrl)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 text-zinc-900 hover:underline text-sm"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                {ev.filename || t('submissionReview.downloadFile', 'Download file')}
                              </a>
                            )}
                          </div>
                        ) : ev?.value ? (
                          <p className="text-sm text-zinc-700 whitespace-pre-wrap bg-zinc-50 rounded p-2">{ev.value}</p>
                        ) : (
                          <p className="text-sm text-zinc-500 italic">
                            {typeof ev === 'string' ? ev : JSON.stringify(ev)}
                          </p>
                        )}
                        {/* Metadata badges */}
                        {ev?.metadata && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {ev.metadata.gps && <GpsBadge gps={ev.metadata.gps} />}
                            {ev.metadata.captureTimestamp && (
                              <span className="text-xs bg-zinc-100 text-zinc-700 px-2 py-0.5 rounded-full">
                                {new Date(ev.metadata.captureTimestamp).toLocaleString()}
                              </span>
                            )}
                            {ev.metadata.source && (
                              <span className="text-xs bg-zinc-100 text-zinc-700 px-2 py-0.5 rounded-full">
                                {ev.metadata.source === 'camera' ? t('submissionReview.sourceCamera', 'Camera') : ev.metadata.source === 'gallery' ? t('submissionReview.sourceGallery', 'Gallery') : ev.metadata.source}
                              </span>
                            )}
                            {ev.metadata.deviceInfo?.model && (
                              <span className="text-xs bg-zinc-100 text-zinc-700 px-2 py-0.5 rounded-full">
                                {ev.metadata.deviceInfo.model}
                              </span>
                            )}
                            {ev.metadata.size && (
                              <span className="text-xs bg-zinc-100 text-zinc-500 px-2 py-0.5 rounded-full">
                                {ev.metadata.size > 1048576
                                  ? `${(ev.metadata.size / 1048576).toFixed(1)} MB`
                                  : `${Math.round(ev.metadata.size / 1024)} KB`}
                              </span>
                            )}
                            {ev.metadata.checksum && (
                              <span className="text-xs bg-zinc-100 text-zinc-900 px-2 py-0.5 rounded-full" title={ev.metadata.checksum}>
                                SHA: {String(ev.metadata.checksum).slice(0, 8)}...
                              </span>
                            )}
                            {ev.metadata.ai_verification?.verified !== undefined && (
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                ev.metadata.ai_verification.verified
                                  ? 'bg-zinc-100 text-zinc-900'
                                  : 'bg-amber-100 text-amber-800'
                              }`}>
                                AI: {ev.metadata.ai_verification.verified ? t('submissionReview.aiVerified', 'Verified') : t('submissionReview.aiReview', 'Review')}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500 italic">No evidence provided</p>
                )}
              </div>

              {/* Evidence files */}
              {submission.evidence_files && (submission.evidence_files as string[]).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 mb-2">{t('submissionReview.files', 'Files')}</h3>
                  <div className="flex flex-wrap gap-2">
                    {(submission.evidence_files as string[]).map((url, idx) => (
                      <a
                        key={idx}
                        href={safeHref(url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-zinc-100 hover:bg-zinc-200 rounded-lg text-sm text-zinc-900 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        File {idx + 1}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {submission.agent_notes && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 mb-1">{t('submissionReview.agentNotes', 'Agent Notes')}</h3>
                  <p className="text-sm text-zinc-700 bg-zinc-50 rounded-lg p-3">{submission.agent_notes}</p>
                </div>
              )}

              {/* Auto-check verification results */}
              {submission.auto_check_passed !== null && submission.auto_check_passed !== undefined && (() => {
                const details = submission.auto_check_details as AutoCheckDetails | null
                const score = details?.score ?? 0
                const phase = details?.phase
                return (
                <div className={`rounded-lg border ${
                  submission.auto_check_passed ? 'bg-zinc-50 border-zinc-200' : 'bg-amber-50 border-amber-300'
                }`}>
                  <div className="flex items-center justify-between gap-2 p-3 flex-wrap">
                    <span className={`text-sm font-medium ${
                      submission.auto_check_passed ? 'text-zinc-900' : 'text-amber-800'
                    }`}>
                      {submission.auto_check_passed
                        ? t('autoCheck.passed', 'Automatic verification: Approved')
                        : t('autoCheck.needsReview', 'Automatic verification: Needs review')}
                    </span>
                    <div className="flex items-center gap-2">
                      {phase && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          phase === 'AB'
                            ? 'bg-zinc-100 text-zinc-900'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {phase === 'AB'
                            ? t('autoCheck.phaseComplete', 'Verification complete')
                            : t('autoCheck.phasePartial', 'Partial verification — AI pending')}
                        </span>
                      )}
                      {score !== undefined && (
                        <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                          submission.auto_check_passed ? 'bg-zinc-900 text-white' : 'bg-amber-200 text-amber-900'
                        }`}>
                          Score: {(score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Individual check details */}
                  {Array.isArray(details?.checks) && (
                    <div className="px-3 pb-3 space-y-1">
                      {(details.checks as Array<{name: string; passed: boolean; score: number; reason?: string}>).map((check) => (
                        <div key={check.name}>
                          <div className="flex items-center gap-2 text-xs">
                            <span className={check.passed ? 'text-green-600' : 'text-red-600'}>
                              {check.passed ? '\u2713' : '\u2717'}
                            </span>
                            <span className="text-zinc-700 w-28">{getCheckLabel(check.name, t)}</span>
                            <div className="flex-1 bg-zinc-200 rounded-full h-1.5">
                              <div
                                className={`h-1.5 rounded-full ${
                                  check.score >= 0.7 ? 'bg-zinc-900' : check.score >= 0.4 ? 'bg-amber-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${Math.round(check.score * 100)}%` }}
                              />
                            </div>
                            <span className="text-zinc-700 dark:text-zinc-300 font-mono w-8 text-right">
                              {Math.round(check.score * 100)}%
                            </span>
                          </div>
                          {check.reason && (
                            <p className="text-xs text-zinc-600 dark:text-zinc-400 ml-5 mt-0.5">{check.reason}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {/* Warnings */}
                  {Array.isArray(details?.warnings) &&
                    (details.warnings as string[]).length > 0 && (
                    <div className="px-3 pb-3">
                      {(details.warnings as string[]).map((w: string, i: number) => (
                        <p key={i} className="text-xs text-amber-700">{w}</p>
                      ))}
                    </div>
                  )}
                  {/* Phase B error */}
                  {(details as Record<string, unknown>)?.phase_b_error != null && (
                    <div className="px-3 pb-3">
                      <p className="text-xs text-red-600">
                        {t('autoCheck.phaseBError', 'AI analysis error: {{error}}', {
                          error: String((details as Record<string, unknown>).phase_b_error),
                        })}
                      </p>
                    </div>
                  )}
                  {/* Score guidance */}
                  <div className="px-3 pb-3 text-xs text-zinc-500">
                    {score >= 0.95 ? t('autoCheck.guidanceHigh', 'All checks passed. Safe to approve.') :
                     score >= 0.70 ? t('autoCheck.guidanceMedium', 'Most checks passed. Review warnings before approving.') :
                     score >= 0.40 ? t('autoCheck.guidanceLow', 'Several checks failed. Review evidence carefully.') :
                     t('autoCheck.guidanceVeryLow', 'Low score. Review each check before deciding.')}
                  </div>
                </div>
                )
              })()}

              {/* Forensic Event Log — granular verification timeline */}
              {(() => {
                const details = submission.auto_check_details as AutoCheckDetails | null
                const vEvents = details?.verification_events
                if (!Array.isArray(vEvents) || vEvents.length === 0) return null
                return <ForensicEventLog events={vEvents} />
              })()}

              {/* Ring 1: AI Analysis / PHOTINT (Phase B) */}
              {submission.ai_verification_result ? (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 mb-2">
                    {t('aiAnalysis.title', 'AI Analysis')}
                  </h3>
                  <AIAnalysisDetails
                    result={submission.ai_verification_result as AIAnalysisResult}
                  />
                </div>
              ) : (() => {
                const category = submission.task?.category
                const physicalCategories = ['physical_presence', 'location_based', 'verification', 'sensory', 'data_collection']
                const isPhysical = category && physicalCategories.includes(category)
                const details = submission.auto_check_details as AutoCheckDetails | null
                const phase = details?.phase
                if (!isPhysical) return null
                return (
                  <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
                    <h3 className="text-sm font-medium text-zinc-700 mb-1">
                      {t('aiAnalysis.ring1Title', 'Ring 1: PHOTINT Analysis')}
                    </h3>
                    <p className="text-xs text-zinc-700">
                      {phase === 'AB'
                        ? t('aiAnalysis.ring1NotAvailable', 'PHOTINT: Analysis completed but no AI result produced. Evidence may lack photos.')
                        : t('aiAnalysis.ring1Processing', 'PHOTINT: Processing photo forensics (tampering, GenAI detection, GPS consistency)...')}
                    </p>
                  </div>
                )
              })()}

              {/* Ring 2 Arbiter Verdict */}
              {(() => {
                type ArbiterFields = {
                  arbiter_verdict?: string | null
                  arbiter_tier?: string | null
                  arbiter_score?: number | null
                  arbiter_confidence?: number | null
                  arbiter_evidence_hash?: string | null
                  arbiter_commitment_hash?: string | null
                  arbiter_verdict_data?: {
                    reason?: string | null
                    disagreement?: boolean
                    ring_scores?: Array<{
                      ring?: string
                      provider?: string
                      model?: string
                      score?: number
                      decision?: string
                    }>
                  } | null
                }
                const a = submission as unknown as ArbiterFields

                // When no arbiter verdict exists, show explicit status
                if (!a.arbiter_verdict) {
                  const category = submission.task?.category
                  const physicalCategories = ['physical_presence', 'location_based', 'verification', 'sensory', 'data_collection']
                  const isPhysical = category && physicalCategories.includes(category)
                  // Detect arbiter_mode from task metadata (may not be in TS type but present in DB)
                  const taskAny = submission.task as Record<string, unknown> | undefined
                  const arbiterMode = taskAny?.arbiter_mode as string | null | undefined
                  const arbiterEnabled = taskAny?.arbiter_enabled as boolean | null | undefined

                  let statusMessage: string | null = null
                  let statusBg = 'bg-zinc-50'
                  let statusText = 'text-zinc-500'

                  if (!arbiterMode || arbiterMode === 'manual') {
                    statusMessage = t('arbiter.manualMode', 'Arbiter: Not requested (manual mode). Set arbiter_mode to "auto" or "hybrid" for AI evaluation.')
                  } else if (arbiterEnabled || isPhysical) {
                    statusMessage = t('arbiter.processing', 'Arbiter: Processing AI evaluation...')
                    statusBg = 'bg-zinc-50'
                    statusText = 'text-zinc-700'
                  }

                  if (!statusMessage) return null
                  return (
                    <div className={`rounded-lg border border-zinc-200 ${statusBg} p-3`}>
                      <h3 className="text-sm font-medium text-zinc-700 mb-1">
                        {t('arbiter.title', 'Ring 2 Arbiter Verdict')}
                      </h3>
                      <p className={`text-xs ${statusText}`}>{statusMessage}</p>
                    </div>
                  )
                }

                return (
                  <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 space-y-2">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <h3 className="text-sm font-medium text-zinc-700">
                        {t('arbiter.title', 'Ring 2 Arbiter Verdict')}
                      </h3>
                      <ArbiterVerdictBadge
                        verdict={
                          a.arbiter_verdict as
                            | 'pass'
                            | 'fail'
                            | 'inconclusive'
                            | 'skipped'
                        }
                        tier={
                          a.arbiter_tier as 'cheap' | 'standard' | 'max' | null
                        }
                        score={a.arbiter_score}
                        confidence={a.arbiter_confidence}
                        size="lg"
                      />
                    </div>
                    {a.arbiter_verdict_data?.reason && (
                      <p className="text-xs text-zinc-700">
                        {a.arbiter_verdict_data.reason}
                      </p>
                    )}
                    {a.arbiter_verdict_data?.disagreement && (
                      <p className="text-xs text-amber-700 font-medium">
                        {t(
                          'arbiter.disagreement',
                          'Ring disagreement detected — escalated to L2'
                        )}
                      </p>
                    )}
                    {Array.isArray(a.arbiter_verdict_data?.ring_scores) &&
                      a.arbiter_verdict_data.ring_scores.length > 0 && (
                        <div className="pt-1 border-t border-zinc-200 space-y-1">
                          {a.arbiter_verdict_data.ring_scores.map((rs, i) => (
                            <div
                              key={`${rs.ring}-${i}`}
                              className="flex items-center justify-between text-xs"
                            >
                              <span className="text-zinc-700">
                                {rs.ring} · {rs.provider ?? '?'}/
                                {rs.model ?? '?'}
                              </span>
                              <span className="font-mono text-zinc-500">
                                {typeof rs.score === 'number'
                                  ? `${Math.round(rs.score * 100)}%`
                                  : '—'}{' '}
                                {rs.decision ? `· ${rs.decision}` : ''}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    {a.arbiter_evidence_hash && (
                      <p className="text-[10px] font-mono text-zinc-500 break-all">
                        hash: {a.arbiter_evidence_hash.slice(0, 10)}…{a.arbiter_evidence_hash.slice(-8)}
                      </p>
                    )}
                  </div>
                )
              })()}

              {/* Result message */}
              {result && (
                <div className={`p-3 rounded-lg ${
                  result.type === 'success'
                    ? 'bg-zinc-50 border border-zinc-200'
                    : 'bg-red-50 border border-red-200'
                }`}>
                  <p className={`text-sm flex items-center gap-2 ${
                    result.type === 'success' ? 'text-zinc-900' : 'text-red-700'
                  }`}>
                    {result.type === 'success' && (
                      <svg className="w-4 h-4 text-green-600 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                    <span>{result.message}</span>
                  </p>
                </div>
              )}

              {/* Actions - only show if no verdict yet */}
              {!submission.agent_verdict && !result?.type && (
                <div className="space-y-3">
                  {/* Reject/Request info forms */}
                  {(showRejectForm || showInfoForm) && (
                    <div>
                      <label className="block text-sm font-medium text-zinc-700 mb-1">
                        {showRejectForm ? t('submissionReview.rejectReason', 'Rejection reason') : t('submissionReview.whatInfoNeeded', 'What information do you need?')}
                      </label>
                      <textarea
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        rows={3}
                        className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none"
                        placeholder={showRejectForm
                          ? t('submissionReview.rejectPlaceholder', 'Explain why you are rejecting this submission...')
                          : t('submissionReview.infoPlaceholder', 'Describe what additional information you need...')}
                      />
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={showRejectForm ? handleReject : handleRequestInfo}
                          disabled={isProcessing || !feedback.trim()}
                          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 ${
                            showRejectForm
                              ? 'bg-red-600 text-white hover:bg-red-700'
                              : 'bg-amber-700 text-white hover:bg-amber-800'
                          }`}
                        >
                          {isProcessing
                            ? t('common.processing')
                            : showRejectForm ? t('submissionReview.confirmReject', 'Confirm Rejection') : t('submissionReview.sendRequest', 'Send Request')}
                        </button>
                        <button
                          onClick={() => { setShowRejectForm(false); setShowInfoForm(false); setFeedback('') }}
                          className="px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors"
                        >
                          {t('common.cancel')}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Main action buttons */}
                  {!showRejectForm && !showInfoForm && (
                    <div>
                      {/* Optional notes for approval */}
                      <div className="mb-3">
                        <input
                          type="text"
                          value={approveNotes}
                          onChange={(e) => setApproveNotes(e.target.value)}
                          placeholder={t('submissionReview.approvalNotes', 'Approval notes (optional)')}
                          className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none"
                        />
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={handleApprove}
                          disabled={isProcessing}
                          className="flex-1 px-4 py-2.5 bg-zinc-900 text-white text-sm font-medium rounded-lg hover:bg-zinc-800 disabled:bg-zinc-100 disabled:text-zinc-400 disabled:cursor-not-allowed transition-colors"
                        >
                          {action === 'approving' ? t('submissionReview.approving', 'Approving...') : t('submissionReview.approveAndPay', 'Approve & Pay')}
                        </button>
                        <button
                          onClick={() => setShowRejectForm(true)}
                          disabled={isProcessing}
                          className="px-4 py-2.5 border border-red-300 text-red-700 bg-white text-sm font-medium rounded-lg hover:bg-red-50 disabled:bg-zinc-50 disabled:text-zinc-400 disabled:border-zinc-200 disabled:cursor-not-allowed transition-colors"
                        >
                          {t('submissionReview.reject', 'Reject')}
                        </button>
                        <button
                          onClick={() => setShowInfoForm(true)}
                          disabled={isProcessing}
                          className="px-4 py-2.5 border border-zinc-300 text-zinc-800 bg-white text-sm font-medium rounded-lg hover:bg-zinc-50 disabled:bg-zinc-50 disabled:text-zinc-400 disabled:border-zinc-200 disabled:cursor-not-allowed transition-colors"
                        >
                          {t('submissionReview.requestInfo', 'Request Info')}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Already decided */}
              {submission.agent_verdict && !result?.type && (
                <div className="bg-zinc-50 rounded-lg p-3">
                  <p className="text-sm text-zinc-700">
                    {t('submissionReview.alreadyDecided', 'This submission was already')}{' '}
                    <span className="font-medium">
                      {submission.agent_verdict === 'accepted' ? t('status.approved') :
                       submission.agent_verdict === 'disputed' ? t('status.rejected') : t('submissionReview.markedForInfo', 'marked for more info')}
                    </span>
                    {submission.agent_notes && <> &mdash; {submission.agent_notes}</>}
                  </p>
                </div>
              )}
            </>
          )}
      </Modal.Body>

      <Modal.Footer className="bg-zinc-50 justify-between">
        <p className="text-xs text-zinc-500">
          ID: {submissionId.slice(0, 8)}...
          {submission?.submitted_at && (
            <> | {new Date(submission.submitted_at).toLocaleString()}</>
          )}
        </p>
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-200 rounded-lg transition-colors"
        >
          {t('common.close')}
        </button>
      </Modal.Footer>
    </Modal>
  )
}
