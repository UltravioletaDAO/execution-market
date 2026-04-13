// Execution Market: Forensic Event Log
// Timeline component showing every forensic verification step as a live checklist
// with collapsible details. Replaces minimal Ring 1/Ring 2 badges with rich event log.
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface VerificationEvent {
  ts: number
  ring: number
  step: string
  status: 'running' | 'complete' | 'failed' | 'pending'
  detail?: Record<string, unknown>
}

interface ForensicEventLogProps {
  events: VerificationEvent[]
}

// ---------------------------------------------------------------------------
// Step label mapping (i18n keys)
// ---------------------------------------------------------------------------

const STEP_I18N_KEYS: Record<string, string> = {
  exif_extraction: 'forensic.steps.exif_extraction',
  tampering: 'forensic.steps.tampering',
  genai_detection: 'forensic.steps.genai_detection',
  ai_semantic: 'forensic.steps.ai_semantic',
  duplicate: 'forensic.steps.duplicate',
  photo_source: 'forensic.steps.photo_source',
  ring1_complete: 'forensic.steps.ring1_complete',
  tier_routing: 'forensic.steps.tier_routing',
  llm_primary: 'forensic.steps.llm_primary',
  llm_secondary: 'forensic.steps.llm_secondary',
  ring2_complete: 'forensic.steps.ring2_complete',
  gps_check: 'forensic.steps.gps_check',
  timestamp_check: 'forensic.steps.timestamp_check',
  schema_check: 'forensic.steps.schema_check',
}

// Default English labels as fallbacks
const STEP_DEFAULTS: Record<string, string> = {
  exif_extraction: 'EXIF Extraction',
  tampering: 'Tampering Detection',
  genai_detection: 'AI-Generated Check',
  ai_semantic: 'AI Semantic Analysis',
  duplicate: 'Duplicate Check',
  photo_source: 'Photo Source',
  ring1_complete: 'Ring 1 Summary',
  tier_routing: 'Tier Routing',
  llm_primary: 'LLM Primary',
  llm_secondary: 'LLM Secondary',
  ring2_complete: 'Ring 2 Summary',
  gps_check: 'GPS Check',
  timestamp_check: 'Timestamp Check',
  schema_check: 'Schema Check',
}

function getStepLabel(step: string, t: ReturnType<typeof useTranslation>['t']): string {
  const key = STEP_I18N_KEYS[step]
  if (key) return t(key, STEP_DEFAULTS[step] || step)
  // Unknown step — capitalize and clean up
  return step.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

// ---------------------------------------------------------------------------
// Spinner SVG
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
// Status icon for each step
// ---------------------------------------------------------------------------

function StepIcon({ status, passed }: { status: string; passed?: boolean }) {
  switch (status) {
    case 'complete':
      if (passed === false) {
        // Completed but flagged (e.g. is_suspicious=true)
        return <span className="text-amber-500 text-sm font-bold">!</span>
      }
      return (
        <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      )
    case 'failed':
      return (
        <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      )
    case 'running':
      return <Spinner className="w-4 h-4 text-blue-500 flex-shrink-0" />
    case 'pending':
    default:
      return (
        <svg className="w-4 h-4 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 20 20">
          <circle cx="10" cy="10" r="7" strokeWidth="2" />
        </svg>
      )
  }
}

// ---------------------------------------------------------------------------
// Compute latency between events (in seconds)
// ---------------------------------------------------------------------------

function computeLatency(event: VerificationEvent, allEvents: VerificationEvent[]): string | null {
  if (event.status !== 'complete' && event.status !== 'failed') return null

  // If the detail has latency_ms, use it directly
  if (event.detail?.latency_ms != null) {
    const ms = Number(event.detail.latency_ms)
    return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
  }

  // Otherwise compute from timestamps: find the previous event for this ring
  const ringEvents = allEvents
    .filter((e) => e.ring === event.ring && e.ts <= event.ts)
    .sort((a, b) => a.ts - b.ts)

  const idx = ringEvents.findIndex((e) => e.ts === event.ts && e.step === event.step)
  if (idx > 0) {
    const delta = event.ts - ringEvents[idx - 1].ts
    if (delta > 0) return `${delta.toFixed(1)}s`
  }

  return null
}

// ---------------------------------------------------------------------------
// Extract a human-readable detail summary from event detail
// ---------------------------------------------------------------------------

function detailSummary(event: VerificationEvent, t: ReturnType<typeof useTranslation>['t']): string | null {
  const d = event.detail
  if (!d) return null

  const { step, status } = event

  // Failed events: show error
  if (status === 'failed') {
    const provider = d.provider ? String(d.provider) : ''
    const error = d.error ? String(d.error) : t('forensic.unknownError', 'unknown error')
    return provider ? `${provider}: ${error}` : error
  }

  // Running events: show provider
  if (status === 'running') {
    const parts: string[] = []
    if (d.provider) parts.push(String(d.provider))
    if (d.tier) parts.push(String(d.tier))
    return parts.length > 0 ? parts.join(' / ') : null
  }

  // Complete events per step type
  switch (step) {
    case 'exif_extraction': {
      const hasExif = d.has_exif
      const stripped = d.stripped
      if (hasExif === true && stripped === false) return t('forensic.detail.exifClean', 'has_exif, no edits')
      if (hasExif === true && stripped === true) return t('forensic.detail.exifStripped', 'has_exif, stripped')
      if (hasExif === false) return t('forensic.detail.noExif', 'no EXIF data')
      return null
    }
    case 'tampering': {
      const suspicious = d.is_suspicious
      const confidence = d.confidence != null ? Math.round(Number(d.confidence) * 100) : null
      if (suspicious === false && confidence != null) return `${t('forensic.detail.clean', 'Clean')} (${confidence}%)`
      if (suspicious === true && confidence != null) return `${t('forensic.detail.suspicious', 'Suspicious')} (${confidence}%)`
      return suspicious === false ? t('forensic.detail.clean', 'Clean') : t('forensic.detail.suspicious', 'Suspicious')
    }
    case 'genai_detection': {
      const aiGen = d.is_ai_generated
      const confidence = d.confidence != null ? Math.round(Number(d.confidence) * 100) : null
      const label = aiGen === false
        ? t('forensic.detail.realPhoto', 'Real photo')
        : t('forensic.detail.aiGenerated', 'AI generated')
      return confidence != null ? `${label} (${confidence}%)` : label
    }
    case 'ai_semantic': {
      const parts: string[] = []
      if (d.provider) {
        const model = d.model ? `/${d.model}` : ''
        parts.push(`${d.provider}${model}`)
      }
      if (d.decision) {
        const conf = d.confidence != null ? ` (${Math.round(Number(d.confidence) * 100)}%)` : ''
        parts.push(`${String(d.decision).charAt(0).toUpperCase() + String(d.decision).slice(1)}${conf}`)
      }
      return parts.length > 0 ? parts.join('  ') : null
    }
    case 'duplicate': {
      const isDup = d.is_duplicate
      const compared = d.compared != null ? Number(d.compared) : null
      if (isDup === false) {
        return compared != null
          ? `${t('forensic.detail.noDupes', 'No dupes')} (${compared})`
          : t('forensic.detail.noDupes', 'No dupes')
      }
      return isDup === true ? t('forensic.detail.duplicateFound', 'Duplicate found') : null
    }
    case 'photo_source': {
      const source = d.source ? String(d.source) : null
      return source ? source.charAt(0).toUpperCase() + source.slice(1) : null
    }
    case 'ring1_complete': {
      const score = d.score != null ? Math.round(Number(d.score) * 100) : null
      const passed = d.checks_passed != null ? Number(d.checks_passed) : null
      const parts: string[] = []
      if (score != null) parts.push(`${t('forensic.detail.score', 'Score')}: ${score}%`)
      if (passed != null) parts.push(`${passed}/${passed} ${t('forensic.detail.checksPassed', 'checks passed')}`)
      return parts.length > 0 ? parts.join(' \u00B7 ') : null
    }
    case 'tier_routing': {
      const tier = d.tier ? String(d.tier) : null
      const reason = d.reason ? String(d.reason) : null
      const parts: string[] = []
      if (tier) parts.push(tier.charAt(0).toUpperCase() + tier.slice(1))
      if (reason) parts.push(reason)
      return parts.length > 0 ? parts.join(' \u2014 ') : null
    }
    case 'llm_primary':
    case 'llm_secondary': {
      const parts: string[] = []
      if (d.provider) {
        const model = d.model ? `/${String(d.model)}` : ''
        parts.push(`${String(d.provider)}${model}`)
      }
      if (d.decision) {
        const conf = d.confidence != null ? ` ${Math.round(Number(d.confidence) * 100)}%` : ''
        const score = d.score != null ? ` (${Math.round(Number(d.score) * 100)}%)` : ''
        parts.push(`${String(d.decision).toUpperCase()}${score}${conf}`)
      }
      // Fallback: if we have latency data but no other fields, show the tier
      if (parts.length === 0 && d.tier) parts.push(String(d.tier))
      return parts.length > 0 ? parts.join('  ') : null
    }
    case 'ring2_complete': {
      const parts: string[] = []
      if (d.verdict) parts.push(`${t('forensic.detail.verdict', 'Verdict')}: ${String(d.verdict).toUpperCase()}`)
      if (d.score != null) parts.push(`${t('forensic.detail.score', 'Score')}: ${Math.round(Number(d.score) * 100)}%`)
      if (d.confidence != null) parts.push(`${t('forensic.detail.confidence', 'Confidence')}: ${Math.round(Number(d.confidence) * 100)}%`)
      if (d.cost_usd != null) parts.push(`${t('forensic.detail.cost', 'Ring 2 cost')}: $${Number(d.cost_usd).toFixed(3)}`)
      return parts.length > 0 ? parts.join(' \u00B7 ') : null
    }
    default: {
      // Generic: try to show a few meaningful keys
      const interesting = Object.entries(d)
        .filter(([k]) => !['ts', 'ring', 'step', 'status'].includes(k))
        .slice(0, 3)
        .map(([k, v]) => `${k}: ${typeof v === 'number' ? (v < 1 ? `${Math.round(v * 100)}%` : v) : String(v)}`)
      return interesting.length > 0 ? interesting.join(', ') : null
    }
  }
}

// ---------------------------------------------------------------------------
// Determine if a "complete" event should show as flagged (not passed)
// ---------------------------------------------------------------------------

function isEventFlagged(event: VerificationEvent): boolean {
  if (event.status !== 'complete') return false
  const d = event.detail
  if (!d) return false

  switch (event.step) {
    case 'tampering':
      return d.is_suspicious === true
    case 'genai_detection':
      return d.is_ai_generated === true
    case 'duplicate':
      return d.is_duplicate === true
    case 'ai_semantic':
      return d.decision === 'rejected'
    case 'llm_primary':
    case 'llm_secondary':
      return d.decision === 'fail' || d.decision === 'rejected'
    case 'ring2_complete':
      return d.verdict === 'fail' || d.verdict === 'rejected'
    default:
      return false
  }
}

// ---------------------------------------------------------------------------
// Group ai_semantic events: multiple events with the same step but different
// statuses (failed + complete) should render as a single row with fallback trail
// ---------------------------------------------------------------------------

interface GroupedStep {
  primary: VerificationEvent
  fallbacks: VerificationEvent[] // failed attempts before the primary
}

function groupStepEvents(events: VerificationEvent[]): GroupedStep[] {
  const groups: GroupedStep[] = []
  const byStep = new Map<string, VerificationEvent[]>()

  // Group by step name, preserving order
  const stepOrder: string[] = []
  for (const ev of events) {
    if (!byStep.has(ev.step)) {
      byStep.set(ev.step, [])
      stepOrder.push(ev.step)
    }
    byStep.get(ev.step)!.push(ev)
  }

  for (const step of stepOrder) {
    const stepEvents = byStep.get(step)!
    // Summary steps (ring1_complete, ring2_complete) — always single row
    if (step.endsWith('_complete')) {
      for (const ev of stepEvents) {
        groups.push({ primary: ev, fallbacks: [] })
      }
      continue
    }

    // For steps with multiple events (e.g. ai_semantic with fallback),
    // the last non-failed event (or the last event) is primary, rest are fallbacks
    if (stepEvents.length === 1) {
      groups.push({ primary: stepEvents[0], fallbacks: [] })
    } else {
      // Find the "final" event: last complete, or last running, or last event
      const complete = stepEvents.filter((e) => e.status === 'complete')
      const running = stepEvents.filter((e) => e.status === 'running')
      const primary = complete.length > 0
        ? complete[complete.length - 1]
        : running.length > 0
          ? running[running.length - 1]
          : stepEvents[stepEvents.length - 1]

      const fallbacks = stepEvents.filter((e) => e !== primary && e.status === 'failed')
      groups.push({ primary, fallbacks })
    }
  }

  return groups
}

// ---------------------------------------------------------------------------
// Ring section component
// ---------------------------------------------------------------------------

function RingSection({
  ringNumber,
  title,
  events,
  allEvents,
}: {
  ringNumber: number
  title: string
  events: VerificationEvent[]
  allEvents: VerificationEvent[]
}) {
  const { t } = useTranslation()
  const grouped = groupStepEvents(events)

  // Find the ring summary event
  const summaryStep = ringNumber === 1 ? 'ring1_complete' : 'ring2_complete'
  const summaryEvent = events.find((e) => e.step === summaryStep && e.status === 'complete')

  // Determine overall ring status
  const hasRunning = events.some((e) => e.status === 'running')
  const hasFailed = events.every((e) => e.status === 'failed')
  const isComplete = !!summaryEvent

  const borderColor = isComplete
    ? 'border-green-200'
    : hasRunning
      ? 'border-blue-200'
      : hasFailed
        ? 'border-red-200'
        : 'border-gray-200'

  return (
    <div className={`rounded-lg border ${borderColor} bg-gray-50 overflow-hidden`}>
      {/* Ring header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 bg-gray-100">
        <span className="text-xs font-semibold text-gray-700">{title}</span>
        {isComplete && (
          <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )}
        {hasRunning && !isComplete && <Spinner className="w-4 h-4 text-blue-500" />}
      </div>

      {/* Step rows */}
      <div className="px-3 py-2 space-y-1.5">
        {grouped.map((group, idx) => {
          // Skip summary steps from the checklist rows — they render as the footer
          if (group.primary.step === summaryStep) return null

          const ev = group.primary
          const latency = computeLatency(ev, allEvents)
          const summary = detailSummary(ev, t)
          const flagged = isEventFlagged(ev)

          return (
            <div key={`${ev.step}-${idx}`}>
              {/* Main step row */}
              <div className="flex items-center gap-2 min-h-[24px]">
                <StepIcon status={ev.status} passed={!flagged} />
                <span className="text-xs text-gray-700 font-medium w-36 sm:w-40 truncate flex-shrink-0">
                  {getStepLabel(ev.step, t)}
                </span>
                {summary && (
                  <span className="text-[11px] text-gray-500 min-w-0 break-words">{summary}</span>
                )}
                {latency && (
                  <span className="text-[11px] text-gray-400 font-mono flex-shrink-0 ml-auto pl-2" title="Inference latency">
                    {latency}
                  </span>
                )}
              </div>

              {/* Fallback trail for steps with retries (e.g. ai_semantic) */}
              {group.fallbacks.length > 0 && (
                <div className="ml-6 space-y-0.5 mt-0.5">
                  {group.fallbacks.map((fb, fbIdx) => {
                    const fbSummary = detailSummary(fb, t)
                    return (
                      <div key={`fb-${fb.step}-${fbIdx}`} className="flex items-center gap-2 text-[11px]">
                        <svg className="w-3 h-3 text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                        <span className="text-red-500">{fbSummary || t('forensic.failedAttempt', 'failed')}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Ring summary footer */}
      {summaryEvent && (
        <div className="px-3 py-2 border-t border-gray-200 bg-gray-100 space-y-1.5">
          <span className="text-[11px] text-gray-600 font-medium">
            {detailSummary(summaryEvent, t)}
          </span>
          {/* Per-check breakdown (only Ring 1, when detail.checks is available) */}
          {ringNumber === 1 && Array.isArray(summaryEvent.detail?.checks) && (summaryEvent.detail.checks as Array<{name: string; passed: boolean; score: number}>).length > 0 && (
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
              {(summaryEvent.detail.checks as Array<{name: string; passed: boolean; score: number}>).map((c) => (
                <div key={c.name} className="flex items-center gap-1.5 text-[11px]">
                  {c.passed
                    ? <svg className="w-2.5 h-2.5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                    : <svg className="w-2.5 h-2.5 text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                  }
                  <span className={`truncate ${c.passed ? 'text-gray-600' : 'text-red-500'}`}>
                    {getStepLabel(c.name, t)}
                  </span>
                  <span className="text-gray-400 font-mono ml-auto pl-1 flex-shrink-0">
                    {Math.round(c.score * 100)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ForensicEventLog({ events }: ForensicEventLogProps) {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)

  if (!events || events.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
        <div className="flex items-center gap-2">
          <Spinner className="w-4 h-4 text-gray-400" />
          <span className="text-xs text-gray-500">
            {t('forensic.waiting', 'Waiting for verification to start...')}
          </span>
        </div>
      </div>
    )
  }

  // Split events by ring
  const ring1Events = events.filter((e) => e.ring === 1).sort((a, b) => a.ts - b.ts)
  const ring2Events = events.filter((e) => e.ring === 2).sort((a, b) => a.ts - b.ts)

  // Determine overall completion
  const ring1Done = ring1Events.some((e) => e.step === 'ring1_complete' && (e.status === 'complete' || e.status === 'failed'))
  const ring2Done = ring2Events.some((e) => e.step === 'ring2_complete' && (e.status === 'complete' || e.status === 'failed'))
  const allDone = (ring1Events.length === 0 || ring1Done) && (ring2Events.length === 0 || ring2Done)

  return (
    <div className="mt-3">
      {/* Section header with collapse toggle */}
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 w-full text-left mb-2 group"
      >
        <svg
          className={`w-3.5 h-3.5 text-gray-400 transition-transform group-hover:text-gray-600 ${collapsed ? '' : 'rotate-90'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
        <span className="text-xs font-semibold text-gray-700">
          {t('forensic.title', 'Forensic Verification Log')}
        </span>
        {allDone && (
          <svg className="w-3.5 h-3.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )}
        {!allDone && (
          <Spinner className="w-3.5 h-3.5 text-blue-500" />
        )}
      </button>

      {!collapsed && (
        <div className="space-y-2">
          {ring1Events.length > 0 && (
            <RingSection
              ringNumber={1}
              title={t('forensic.ring1Title', 'Ring 1: PHOTINT Analysis')}
              events={ring1Events}
              allEvents={events}
            />
          )}
          {ring2Events.length > 0 && (
            <RingSection
              ringNumber={2}
              title={t('forensic.ring2Title', 'Ring 2: Arbiter Evaluation')}
              events={ring2Events}
              allEvents={events}
            />
          )}
        </div>
      )}
    </div>
  )
}
