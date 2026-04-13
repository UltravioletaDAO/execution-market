// Execution Market: Evidence Verification Panel
// Reusable component to display auto-check verification results for submissions
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { getCheckLabel } from '../constants/checkLabels'
import { ForensicEventLog } from './ForensicEventLog'
import type { VerificationEvent } from './ForensicEventLog'

// ---------------------------------------------------------------------------
// Ring attempt type — one entry per provider tried
// ---------------------------------------------------------------------------
export interface RingAttempt {
  provider: string
  status: 'success' | 'timeout' | 'error' | 'skipped'
  latency_ms?: number
  error?: string
}

/** Shape of auto_check_details from the backend verification pipeline */
export interface AutoCheckDetails {
  score: number // 0-1
  passed: boolean
  summary?: string
  phase?: string // 'A' | 'AB'
  checks: Array<{
    name: string // 'schema', 'gps', 'timestamp', etc.
    score: number // 0-1
    passed: boolean
    reason?: string
  }>
  warnings?: string[]
  phase_b_status?: 'pending' | 'complete' | 'error'
  phase_b_error?: string

  // Ring 1 — PHOTINT + AI semantic analysis
  ring1_status?: 'pending' | 'running' | 'complete' | 'failed'
  ring1_provider?: string
  ring1_model?: string
  ring1_latency_ms?: number
  ring1_decision?: 'approved' | 'rejected' | 'needs_review'
  ring1_confidence?: number // 0-1
  ring1_attempts?: RingAttempt[]

  // Ring 2 — Arbiter dual-model evaluation
  ring2_status?: 'pending' | 'running' | 'complete' | 'failed'
  ring2_decision?: 'approved' | 'rejected' | 'inconclusive'
  ring2_score?: number // 0-1
  ring2_tier?: 'cheap' | 'standard' | 'max'

  // Arbiter mode (from task config, sometimes echoed here)
  arbiter_mode?: 'manual' | 'auto' | 'hybrid'

  // Forensic event log — granular verification timeline
  verification_events?: VerificationEvent[]
}

interface EvidenceVerificationPanelProps {
  details: Record<string, unknown> | null | undefined
  /**
   * Optional callback to re-fetch the latest submission data.
   * When provided, the panel will auto-poll every 3 s while any ring is
   * still "pending" or "running", calling this function to trigger a refresh.
   */
  onRefresh?: () => void
}

// ---------------------------------------------------------------------------
// Small helper: spinner SVG (reusable)
// ---------------------------------------------------------------------------
function Spinner({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={`${className} animate-spin`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Ring status badge
// ---------------------------------------------------------------------------
function RingStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  switch (status) {
    case 'pending':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
          {t('autoCheck.ring.pending', 'Pending')}
        </span>
      )
    case 'running':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
          <Spinner className="w-3 h-3" />
          {t('autoCheck.ring.running', 'Running...')}
        </span>
      )
    case 'complete':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          {t('autoCheck.ring.complete', 'Complete')}
        </span>
      )
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          {t('autoCheck.ring.failed', 'Failed')}
        </span>
      )
    default:
      return null
  }
}

// ---------------------------------------------------------------------------
// Decision badge (approved / rejected / needs_review / inconclusive)
// ---------------------------------------------------------------------------
function DecisionBadge({ decision }: { decision: string }) {
  const { t } = useTranslation()
  const map: Record<string, { bg: string; text: string; label: string }> = {
    approved: { bg: 'bg-green-100', text: 'text-green-700', label: t('autoCheck.ring.approved', 'Approved') },
    rejected: { bg: 'bg-red-100', text: 'text-red-700', label: t('autoCheck.ring.rejected', 'Rejected') },
    needs_review: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: t('autoCheck.ring.needsReview', 'Needs Review') },
    inconclusive: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: t('autoCheck.ring.inconclusive', 'Inconclusive') },
  }
  const style = map[decision] ?? { bg: 'bg-gray-100', text: 'text-gray-600', label: decision }
  return (
    <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-full ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Ring attempt trail (collapsible)
// ---------------------------------------------------------------------------
function AttemptTrail({ attempts }: { attempts: RingAttempt[] }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const hasFailures = attempts.some((a) => a.status !== 'success')

  if (attempts.length <= 1) return null

  // Compact one-line summary
  const summary = attempts
    .map((a) => {
      const latency = a.latency_ms != null ? `${(a.latency_ms / 1000).toFixed(1)}s` : ''
      const icon = a.status === 'success' ? '\u2713' : '\u2717'
      return `${a.provider}: ${a.status}${latency ? ` (${latency})` : ''} ${icon}`
    })
    .join(' \u2192 ')

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1 text-[11px] text-gray-500 hover:text-gray-700"
      >
        <svg
          className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
        {t('autoCheck.ring.attempts', '{{count}} attempts', { count: attempts.length })}
        {hasFailures && (
          <span className="text-amber-500 text-[10px]">
            ({t('autoCheck.ring.withFallbacks', 'with fallbacks')})
          </span>
        )}
      </button>

      {expanded && (
        <div className="mt-1 ml-3 space-y-0.5">
          {attempts.map((a, i) => (
            <div key={`${a.provider}-${i}`} className="flex items-center gap-2 text-[11px]">
              <span className={a.status === 'success' ? 'text-green-600' : 'text-red-500'}>
                {a.status === 'success' ? '\u2713' : '\u2717'}
              </span>
              <span className="text-gray-600 font-medium">{a.provider}</span>
              <span className="text-gray-400">
                {a.status}{a.latency_ms != null ? ` (${(a.latency_ms / 1000).toFixed(1)}s)` : ''}
              </span>
              {a.error && <span className="text-red-400 truncate max-w-[200px]">{a.error}</span>}
            </div>
          ))}
        </div>
      )}

      {!expanded && hasFailures && (
        <p className="text-[10px] text-gray-400 ml-4 truncate">{summary}</p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function EvidenceVerificationPanel({ details, onRefresh }: EvidenceVerificationPanelProps) {
  const { t } = useTranslation()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const hasDetails = !!details && typeof details === 'object'
  const verification = hasDetails ? (details as unknown as AutoCheckDetails) : ({} as AutoCheckDetails)
  const score = verification.score ?? 0
  const passed = verification.passed ?? score >= 0.7
  const checks = Array.isArray(verification.checks) ? verification.checks : []
  const warnings = Array.isArray(verification.warnings) ? verification.warnings : []

  // Determine if any ring is still in-progress
  const ring1Active = verification.ring1_status === 'pending' || verification.ring1_status === 'running'
  const ring2Active = verification.ring2_status === 'pending' || verification.ring2_status === 'running'
  const anyRingActive = ring1Active || ring2Active
  // Also consider phase_b_status pending (existing behavior)
  const phaseBActive = verification.phase_b_status === 'pending' && verification.phase !== 'AB'

  // Check verification_events for completion (forensic event log)
  const vEvents = Array.isArray(verification.verification_events) ? verification.verification_events : []
  const hasEventLog = vEvents.length > 0
  const ring1EventDone = vEvents.some(
    (e) => e.step === 'ring1_complete' && (e.status === 'complete' || e.status === 'failed'),
  )
  const ring2EventDone = vEvents.some(
    (e) => e.step === 'ring2_complete' && (e.status === 'complete' || e.status === 'failed'),
  )
  const hasRing2Events = vEvents.some((e) => e.ring === 2)
  // If event log is present, use it for polling decisions
  const eventLogComplete = hasEventLog && ring1EventDone && (!hasRing2Events || ring2EventDone)
  const shouldPoll = hasDetails && (eventLogComplete ? false : anyRingActive || phaseBActive)

  // ---------------------------------------------------------------------------
  // Auto-refresh polling (3 s interval while verification is in-progress)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!shouldPoll || !onRefresh) {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
      return
    }

    pollRef.current = setInterval(() => {
      onRefresh()
    }, 3000)

    // Safety: stop polling after 600 s regardless (Ring 1 can take ~300s)
    const timeout = setTimeout(() => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }, 600_000)

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
      clearTimeout(timeout)
    }
  }, [shouldPoll, onRefresh])

  if (!hasDetails) return null

  // No checks and no score — nothing to display
  if (checks.length === 0 && score === 0) return null

  const scorePercent = Math.round(score * 100)
  const scoreColorClass =
    scorePercent >= 70
      ? 'bg-green-100 text-green-700'
      : scorePercent >= 40
        ? 'bg-yellow-100 text-yellow-700'
        : 'bg-red-100 text-red-700'

  const borderClass = passed ? 'border-green-200' : 'border-orange-200'

  // Ring fields
  const hasRing1 = !!verification.ring1_status
  const hasRing2 = !!verification.ring2_status

  return (
    <div className={`bg-white rounded-lg border p-4 ${borderClass}`}>
      {/* Header: title + overall score */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-700">
          {t('autoCheck.title', 'Automatic verification')}
        </span>
        <div className="flex items-center gap-2">
          {shouldPoll && (
            <span className="inline-flex items-center gap-1 text-[10px] text-blue-500">
              <Spinner className="w-3 h-3" />
              {t('autoCheck.ring.polling', 'Updating...')}
            </span>
          )}
          {verification.phase === 'AB' ? (
            <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${scoreColorClass}`}>
              {scorePercent}%
            </span>
          ) : (
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
              {t('autoCheck.ring.running', 'Processing...')}
            </span>
          )}
        </div>
      </div>

      {/* Summary text — hide misleading Phase A summary while Ring 1+2 process */}
      {verification.phase === 'AB' && verification.summary && (
        <p className="text-sm text-gray-600 mb-3">{verification.summary}</p>
      )}
      {(anyRingActive || (verification.phase !== 'AB' && !hasRing1)) && (
        <div className="flex items-start gap-3 rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 mb-3">
          <svg className="w-5 h-5 animate-spin text-blue-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <div>
            <p className="text-sm font-semibold text-blue-800">
              {t('autoCheck.ring.analysisInProgress', 'PHOTINT analysis in progress')}
            </p>
            <p className="text-xs text-blue-600 mt-0.5">
              {t('autoCheck.phaseBPending', 'AI verification in progress. Results will update automatically.')}
            </p>
          </div>
        </div>
      )}

      {/* Individual checks */}
      {checks.length > 0 && (
        <div className="space-y-1">
          {checks.map((check) => (
            <div key={check.name}>
              <div className="flex items-center gap-2 text-xs">
                <span className={check.passed ? 'text-green-600' : 'text-red-500'}>
                  {check.passed ? '\u2713' : '\u2717'}
                </span>
                <span className="text-gray-600 w-28">
                  {getCheckLabel(check.name, t)}
                </span>
                <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${
                      check.score >= 0.7
                        ? 'bg-green-500'
                        : check.score >= 0.4
                          ? 'bg-yellow-500'
                          : 'bg-red-400'
                    }`}
                    style={{ width: `${Math.round(check.score * 100)}%` }}
                  />
                </div>
                <span className="text-gray-400 font-mono w-8 text-right">
                  {Math.round(check.score * 100)}%
                </span>
              </div>
              {check.reason && (
                <p className="text-xs text-gray-400 ml-5 mt-0.5">{check.reason}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-600">
              {w}
            </p>
          ))}
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Ring 1: PHOTINT + AI Semantic Analysis                            */}
      {/* ----------------------------------------------------------------- */}
      {hasRing1 && (
        <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
          <div className="flex items-center justify-between flex-wrap gap-1 mb-1">
            <span className="text-xs font-medium text-gray-700">
              {t('autoCheck.ring1.title', 'Ring 1: PHOTINT Analysis')}
            </span>
            <RingStatusBadge status={verification.ring1_status!} />
          </div>

          {/* Complete: show provider + decision + confidence + latency */}
          {verification.ring1_status === 'complete' && (
            <div className="space-y-1">
              <div className="flex items-center flex-wrap gap-2 text-xs">
                {verification.ring1_provider && (
                  <span className="text-gray-500">
                    {verification.ring1_provider}
                    {verification.ring1_model ? `/${verification.ring1_model}` : ''}
                  </span>
                )}
                {verification.ring1_decision && (
                  <DecisionBadge decision={verification.ring1_decision} />
                )}
                {verification.ring1_confidence != null && (
                  <span className="text-gray-400 font-mono text-[11px]">
                    {t('autoCheck.ring1.confidence', 'confidence')}: {Math.round(verification.ring1_confidence * 100)}%
                  </span>
                )}
                {verification.ring1_latency_ms != null && (
                  <span className="text-gray-400 font-mono text-[11px]">
                    {(verification.ring1_latency_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Failed: show warning */}
          {verification.ring1_status === 'failed' && (
            <p className="text-xs text-red-600 mt-1">
              {t('autoCheck.ring1.allFailed', 'All providers failed. Evidence could not be analyzed by AI.')}
            </p>
          )}

          {/* Attempt trail (collapsible) */}
          {Array.isArray(verification.ring1_attempts) && verification.ring1_attempts.length > 0 && (
            <AttemptTrail attempts={verification.ring1_attempts} />
          )}
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Ring 2: Arbiter Dual-Model Evaluation                             */}
      {/* ----------------------------------------------------------------- */}
      {hasRing2 && (
        <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
          <div className="flex items-center justify-between flex-wrap gap-1 mb-1">
            <span className="text-xs font-medium text-gray-700">
              {t('autoCheck.ring2.title', 'Ring 2: Arbiter Evaluation')}
            </span>
            <RingStatusBadge status={verification.ring2_status!} />
          </div>

          {/* Complete: show decision + score + tier */}
          {verification.ring2_status === 'complete' && (
            <div className="flex items-center flex-wrap gap-2 text-xs">
              {verification.ring2_decision && (
                <DecisionBadge decision={verification.ring2_decision} />
              )}
              {verification.ring2_score != null && (
                <span className="text-gray-400 font-mono text-[11px]">
                  {t('autoCheck.ring2.score', 'score')}: {Math.round(verification.ring2_score * 100)}%
                </span>
              )}
              {verification.ring2_tier && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-gray-200 text-gray-600">
                  {t('autoCheck.ring2.tier', 'tier')}: {verification.ring2_tier}
                </span>
              )}
            </div>
          )}

          {/* Failed */}
          {verification.ring2_status === 'failed' && (
            <p className="text-xs text-red-600 mt-1">
              {t('autoCheck.ring2.failed', 'Arbiter evaluation failed.')}
            </p>
          )}
        </div>
      )}

      {/* Ring 2 not requested (manual mode) */}
      {!hasRing2 && verification.arbiter_mode === 'manual' && (
        <div className="mt-2 rounded-lg border border-gray-100 bg-gray-50 p-2">
          <span className="text-[11px] text-gray-400">
            {t('autoCheck.ring2.notRequested', 'Ring 2: Not requested (manual mode)')}
          </span>
        </div>
      )}

      {/* Forensic Event Log — rich timeline of every verification step */}
      {hasEventLog && (
        <ForensicEventLog events={vEvents} />
      )}

      {/* Phase indicator (existing: phase_b_status pending + not yet AB) */}
      {verification.phase_b_status === 'pending' && verification.phase !== 'AB' && !hasRing1 && (
        <div className="flex items-center gap-2 mt-3 p-2 bg-blue-50 rounded-lg">
          <Spinner className="w-4 h-4 text-blue-500" />
          <div>
            <span className="text-xs font-medium text-blue-700">
              {t('autoCheck.phaseAComplete', 'Phase A complete')}
            </span>
            <span className="text-xs text-blue-500 ml-1">
              — {t('autoCheck.phaseBPending', 'AI verification in progress. Results will update automatically.')}
            </span>
          </div>
        </div>
      )}
      {/* Phase B error */}
      {verification.phase_b_status === 'error' && (
        <div className="flex items-center gap-2 mt-3 p-2 bg-red-50 border border-red-200 rounded-lg">
          <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <div>
            <span className="text-xs font-medium text-red-700">
              {t('autoCheck.phaseBError', 'AI verification failed')}
            </span>
            {!!(verification as unknown as Record<string, unknown>).phase_b_error && (
              <p className="text-xs text-red-500 mt-0.5">
                {String((verification as unknown as Record<string, unknown>).phase_b_error)}
              </p>
            )}
          </div>
        </div>
      )}
      {verification.phase === 'AB' && !hasRing1 && !hasRing2 && (
        <div className="flex items-center gap-2 mt-3 p-2 bg-green-50 rounded-lg">
          <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          <span className="text-xs font-medium text-green-700">
            {t('autoCheck.verificationComplete', 'Verification complete')}
          </span>
        </div>
      )}
    </div>
  )
}
