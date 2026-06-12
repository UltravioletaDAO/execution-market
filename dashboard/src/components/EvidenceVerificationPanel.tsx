// Execution Market: Evidence Verification Panel
// Reusable component to display auto-check verification results for submissions.
//
// Contract notes (C-27/C-28/C-29/C-34):
//   - All parsing goes through lib/verificationContract — no ad-hoc casts.
//   - Pass/fail comes from the backend's `passed` verbatim; the UI never
//     recomputes it from the score (backend threshold = pass_threshold, 0.5).
//   - ring1_status 'error' and 'skipped_no_media' are terminal states with
//     their own UI; a 'running' status with no event activity for >10 min is
//     rendered as "unavailable — review manually" instead of an eternal spinner.
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { getCheckLabel } from '../constants/checkLabels'
import { ForensicEventLog } from './ForensicEventLog'
import { parseRing1, RING1_STALE_SECONDS } from '../lib/verificationContract'

interface EvidenceVerificationPanelProps {
  details: Record<string, unknown> | null | undefined
  /**
   * Optional callback to re-fetch the latest submission data.
   * When provided, the panel will auto-poll every 3 s while Ring 1 is
   * still running, calling this function to trigger a refresh.
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
// Ring status badge — covers every status the backend writes plus the
// UI-derived 'unavailable' (stale running) state.
// ---------------------------------------------------------------------------
function RingStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  switch (status) {
    case 'running':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-900">
          <Spinner className="w-3 h-3" />
          {t('autoCheck.ring.running', 'Running...')}
        </span>
      )
    case 'complete':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-900">
          <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          {t('autoCheck.ring.complete', 'Complete')}
        </span>
      )
    case 'error':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          {t('autoCheck.ring.error', 'Error')}
        </span>
      )
    case 'skipped_no_media':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-500">
          {t('autoCheck.ring.skippedNoMedia', 'Skipped — no media')}
        </span>
      )
    case 'unavailable':
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
          {t('autoCheck.ring.unavailable', 'Unavailable')}
        </span>
      )
    default:
      return null
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function EvidenceVerificationPanel({ details, onRefresh }: EvidenceVerificationPanelProps) {
  const { t } = useTranslation()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // Forces a re-render when a 'running' Ring 1 crosses the staleness window,
  // so the stale message appears even if no new data arrives.
  const [, setStaleTick] = useState(0)

  const vm = parseRing1(details)
  const { checks, warnings } = vm
  const score = vm.score ?? 0

  // Legacy Phase B payloads (pre-rings) still poll until phase flips to 'AB'.
  const phaseBActive = vm.phaseBStatus === 'pending' && vm.phase !== 'AB'
  // Keep polling until the event log is fully complete (Ring 1 AND Ring 2),
  // not just while Ring 1 is in-progress. After ring1_complete the arbiter
  // verdict (Ring 2) still lands ~13s later; stopping at Ring 1 froze the
  // panel before Ring 2 appeared.
  const eventsInFlight = vm.events.length > 0 && !vm.eventsComplete
  const shouldPoll =
    vm.hasDetails &&
    !vm.stale &&
    !vm.eventsComplete &&
    (vm.inProgress || phaseBActive || eventsInFlight)

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

  // ---------------------------------------------------------------------------
  // Staleness ticker: schedule a re-render at the moment a running Ring 1
  // would become stale (C-29 — no eternal spinners).
  // ---------------------------------------------------------------------------
  const { inProgress, lastEventTs } = vm
  useEffect(() => {
    if (!inProgress || lastEventTs === null) return
    const msUntilStale = (lastEventTs + RING1_STALE_SECONDS) * 1000 - Date.now()
    if (msUntilStale <= 0) return
    const timer = setTimeout(() => setStaleTick((n) => n + 1), msUntilStale + 1000)
    return () => clearTimeout(timer)
  }, [inProgress, lastEventTs])

  if (!vm.hasDetails) return null

  // Nothing to display: no checks, no score, and no Ring 1 status to report
  if (checks.length === 0 && score === 0 && !vm.status) return null

  const scorePercent = Math.round(score * 100)
  // C-28: colors derive from the backend's `passed`, never from score thresholds
  const scoreColorClass =
    vm.passed === false ? 'bg-amber-100 text-amber-800' : 'bg-zinc-100 text-zinc-900'
  const borderClass = vm.passed === false ? 'border-amber-300' : 'border-zinc-200'

  const hasRing1 = vm.status !== null
  const ring1DisplayStatus = vm.stale ? 'unavailable' : vm.status ?? ''
  // Show the final score chip once verification reached a terminal state (or
  // legacy phase 'AB'); show "Processing..." only while genuinely in-flight.
  const showScoreChip = vm.terminal || vm.phase === 'AB'

  return (
    <div className={`bg-white rounded-lg border p-4 ${borderClass}`}>
      {/* Header: title + overall score */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-zinc-700">
          {t('autoCheck.title', 'Automatic verification')}
        </span>
        <div className="flex items-center gap-2">
          {shouldPoll && (
            <span className="inline-flex items-center gap-1 text-[10px] text-zinc-500">
              <Spinner className="w-3 h-3" />
              {t('autoCheck.ring.polling', 'Updating...')}
            </span>
          )}
          {showScoreChip ? (
            <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${scoreColorClass}`}>
              {scorePercent}%
            </span>
          ) : (
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-900">
              {t('autoCheck.ring.running', 'Processing...')}
            </span>
          )}
        </div>
      </div>

      {/* Summary text — hide misleading Phase A summary while Ring 1 processes */}
      {vm.phase === 'AB' && vm.summary && (
        <p className="text-sm text-zinc-700 mb-3">{vm.summary}</p>
      )}
      {(vm.inProgress || (vm.phase !== 'AB' && !hasRing1 && !vm.eventsComplete)) && (
        <div className="flex items-start gap-3 rounded-lg border border-zinc-300 bg-zinc-50 px-4 py-3 mb-3">
          <svg className="w-5 h-5 animate-spin text-zinc-700 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <div>
            <p className="text-sm font-semibold text-zinc-900">
              {t('autoCheck.ring.analysisInProgress', 'PHOTINT analysis in progress')}
            </p>
            <p className="text-xs text-zinc-700 mt-0.5">
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
                <span className={check.passed ? 'text-green-600' : 'text-red-600'}>
                  {check.passed ? '✓' : '✗'}
                </span>
                <span className="text-zinc-700 w-28">
                  {getCheckLabel(check.name, t)}
                </span>
                <div className="flex-1 bg-zinc-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${check.passed ? 'bg-zinc-900' : 'bg-red-500'}`}
                    style={{ width: `${Math.round(check.score * 100)}%` }}
                  />
                </div>
                <span className="text-zinc-500 font-mono w-8 text-right">
                  {Math.round(check.score * 100)}%
                </span>
              </div>
              {check.reason && (
                <p className="text-xs text-zinc-500 ml-5 mt-0.5">{check.reason}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-700">
              {w}
            </p>
          ))}
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Ring 1: PHOTINT + AI Semantic Analysis                            */}
      {/* ----------------------------------------------------------------- */}
      {hasRing1 && (
        <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50 p-3">
          <div className="flex items-center justify-between flex-wrap gap-1 mb-1">
            <span className="text-xs font-medium text-zinc-700">
              {t('autoCheck.ring1.title', 'Ring 1: PHOTINT Analysis')}
            </span>
            <RingStatusBadge status={ring1DisplayStatus} />
          </div>

          {/* Error: surface the backend error + manual-review note (C-04) */}
          {vm.status === 'error' && (
            <div className="mt-1 space-y-0.5">
              <p className="text-xs text-red-600">
                {vm.error || t('autoCheck.ring1.error', 'Forensic verification failed.')}
              </p>
              <p className="text-xs text-zinc-600">
                {t('autoCheck.ring1.manualReview', 'Review this evidence manually before deciding.')}
              </p>
            </div>
          )}

          {/* Skipped: no media attached — terminal, Ring 2 covers semantics */}
          {vm.status === 'skipped_no_media' && (
            <p className="text-xs text-zinc-600 mt-1">
              {t('autoCheck.ring1.skippedNoMedia', 'No media attached — forensic verification skipped. Semantic evaluation (Ring 2) covers this submission.')}
            </p>
          )}

          {/* Stale: running with no updates for >10 min (C-29) */}
          {vm.stale && (
            <p className="text-xs text-amber-700 mt-1">
              {t('autoCheck.ring1.stale', 'Verification has not updated in over 10 minutes — results unavailable. Review the evidence manually.')}
            </p>
          )}
        </div>
      )}

      {/* Forensic Event Log — rich timeline of every verification step */}
      {vm.events.length > 0 && (
        <ForensicEventLog events={vm.events} />
      )}

      {/* Phase indicator (legacy payloads: phase_b_status pending + not yet AB) */}
      {vm.phaseBStatus === 'pending' && vm.phase !== 'AB' && !hasRing1 && (
        <div className="flex items-center gap-2 mt-3 p-2 bg-zinc-50 rounded-lg">
          <Spinner className="w-4 h-4 text-zinc-700" />
          <div>
            <span className="text-xs font-medium text-zinc-900">
              {t('autoCheck.phaseAComplete', 'Phase A complete')}
            </span>
            <span className="text-xs text-zinc-600 ml-1">
              — {t('autoCheck.phaseBPending', 'AI verification in progress. Results will update automatically.')}
            </span>
          </div>
        </div>
      )}
      {/* Phase B error (legacy payloads) */}
      {vm.phaseBStatus === 'error' && (
        <div className="flex items-center gap-2 mt-3 p-2 bg-red-50 border border-red-200 rounded-lg">
          <svg className="w-4 h-4 text-red-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <div>
            <span className="text-xs font-medium text-red-700">
              {t('autoCheck.phaseBError', 'AI verification failed')}
            </span>
            {vm.phaseBError && (
              <p className="text-xs text-red-600 mt-0.5">{vm.phaseBError}</p>
            )}
          </div>
        </div>
      )}
      {vm.phase === 'AB' && !hasRing1 && (
        <div className="flex items-center gap-2 mt-3 p-2 bg-zinc-50 rounded-lg">
          <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          <span className="text-xs font-medium text-zinc-900">
            {t('autoCheck.verificationComplete', 'Verification complete')}
          </span>
        </div>
      )}
    </div>
  )
}
