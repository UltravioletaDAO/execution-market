// Execution Market: AI Analysis Details
// Expandable component showing AI's PHOTINT analysis of submitted evidence
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export interface AIAnalysisResult {
  score?: number
  passed?: boolean
  reason?: string
  details?: {
    decision?: string // 'approved' | 'rejected' | 'needs_human'
    confidence?: number // 0-1
    explanation?: string // AI's full analysis text
    issues?: string[] // List of issues found
    task_specific_checks?: Record<string, unknown>
    provider?: string // 'anthropic', 'openai', etc.
    model?: string // 'claude-sonnet-4-6', etc.
  }
}

interface AIAnalysisDetailsProps {
  result: AIAnalysisResult | null | undefined
}

export function AIAnalysisDetails({ result }: AIAnalysisDetailsProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  if (!result?.details) return null

  const { decision, confidence, explanation, issues, model } = result.details

  // B&W with semantic accents: zinc-900 for approved (terminal positive), amber for needs_human (warning), red for rejected (error)
  const decisionConfig = {
    approved: {
      label: t('aiAnalysis.approved', 'Approved'),
      bg: 'bg-zinc-900 text-white',
      note: null as string | null,
    },
    needs_human: {
      label: t('aiAnalysis.escalated', 'Escalated to Ring 2'),
      bg: 'bg-amber-50 text-amber-800 border border-amber-300',
      note: t('aiAnalysis.escalatedNote', 'Ring 1 confidence below threshold — forwarded to Ring 2 for deeper analysis.'),
    },
    rejected: {
      label: t('aiAnalysis.rejected', 'Rejected'),
      bg: 'bg-red-100 text-red-800 border border-red-300',
      note: null as string | null,
    },
  }
  const config =
    decisionConfig[decision as keyof typeof decisionConfig] ||
    decisionConfig.needs_human

  return (
    <div className="border border-zinc-200 rounded-lg overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-zinc-50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${config.bg}`}
          >
            {config.label}
          </span>
          {confidence != null && confidence > 0 && (
            <span className="text-xs text-zinc-500">
              {Math.round(confidence * 100)}%{' '}
              {t('aiAnalysis.confidence', 'confidence')}
            </span>
          )}
          {model && <span className="text-xs text-zinc-500 truncate">{model}</span>}
        </div>
        <svg
          className={`w-4 h-4 text-zinc-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="p-3 pt-0 border-t border-zinc-200 space-y-3">
          {config.note && (
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1.5">
              {config.note}
            </p>
          )}
          {explanation && (
            <div>
              <h4 className="text-xs font-medium text-zinc-500 uppercase mb-1">
                {t('aiAnalysis.analysis', 'Analysis')}
              </h4>
              <p className="text-sm text-zinc-700 whitespace-pre-wrap">
                {explanation}
              </p>
            </div>
          )}
          {issues && issues.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-zinc-500 uppercase mb-1">
                {t('aiAnalysis.issues', 'Issues')}
              </h4>
              <ul className="list-disc list-inside text-sm text-zinc-600 space-y-0.5">
                {issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
