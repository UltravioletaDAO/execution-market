// Execution Market: Evidence Verification Panel
// Reusable component to display auto-check verification results for submissions
import { useTranslation } from 'react-i18next'
import { getCheckLabel } from '../constants/checkLabels'

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
}

interface EvidenceVerificationPanelProps {
  details: Record<string, unknown> | null | undefined
}

export function EvidenceVerificationPanel({ details }: EvidenceVerificationPanelProps) {
  const { t } = useTranslation()

  if (!details || typeof details !== 'object') return null

  const verification = details as unknown as AutoCheckDetails
  const score = verification.score ?? 0
  const passed = verification.passed ?? score >= 0.7
  const checks = Array.isArray(verification.checks) ? verification.checks : []
  const warnings = Array.isArray(verification.warnings) ? verification.warnings : []

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

  return (
    <div className={`bg-white rounded-lg border p-4 ${borderClass}`}>
      {/* Header: title + overall score */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-700">
          {t('autoCheck.title', 'Automatic verification')}
        </span>
        <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${scoreColorClass}`}>
          {scorePercent}%
        </span>
      </div>

      {/* Summary text */}
      {verification.summary && (
        <p className="text-sm text-gray-600 mb-3">{verification.summary}</p>
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

      {/* Phase indicator */}
      {verification.phase_b_status === 'pending' && verification.phase !== 'AB' && (
        <div className="flex items-center gap-2 mt-3 p-2 bg-blue-50 rounded-lg">
          <svg className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
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
            {(verification as unknown as Record<string, unknown>).phase_b_error && (
              <p className="text-xs text-red-500 mt-0.5">
                {String((verification as unknown as Record<string, unknown>).phase_b_error)}
              </p>
            )}
          </div>
        </div>
      )}
      {verification.phase === 'AB' && (
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
