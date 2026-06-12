// Execution Market: Verification contract parser (C-34)
//
// SINGLE place that knows the shape the backend verification pipeline writes
// into `submissions`. Every verification component parses through this module
// instead of casting `auto_check_details` / `arbiter_*` columns ad hoc.
//
// Canonical backend contract (what the backend REALLY writes today):
//   - auto_check_passed (bool), auto_check_score (0-1)
//   - agent_verdict: 'accepted' | 'rejected'  (NEVER 'approved')
//   - auto_check_details (JSONB): {
//       passed, score, checks[{name, passed, score, reason, details}],
//       warnings[], phase: 'A'|'AB', pass_threshold: 0.5,
//       ring1_status: 'running'|'complete'|'error'|'skipped_no_media',
//       ring1_error?, review_required?, ring1_exif?,
//       verification_events?: [{ts(epoch secs), ring: 1|2, step, status, detail}]
//     }
//   - Ring 2 columns: arbiter_verdict ('pass'|'fail'|'inconclusive'|'error'|'skipped'),
//     arbiter_tier, arbiter_score, arbiter_confidence, arbiter_verdict_data
//     (decision/tier/aggregate_score/confidence/ring_scores/grade/summary/check_details),
//     arbiter_evaluated_at
//
// Phantom fields NOBODY writes (do not reintroduce): ring1_decision,
// ring1_provider, ring1_attempts, ring2_status, ring2_decision.

import { AGENT_VERDICT } from '../types/database'

// ---------------------------------------------------------------------------
// Raw contract types
// ---------------------------------------------------------------------------

export type Ring1Status = 'running' | 'complete' | 'error' | 'skipped_no_media'

export type VerificationEventStatus =
  | 'running'
  | 'complete'
  | 'failed'
  | 'error'
  | 'skipped'
  | 'pending'

export interface VerificationEvent {
  ts: number // epoch seconds
  ring: number // 1 | 2
  step: string
  status: VerificationEventStatus
  detail?: Record<string, unknown>
}

export interface VerificationCheck {
  name: string
  passed: boolean
  score: number // 0-1
  reason?: string
  details?: Record<string, unknown>
}

export type ArbiterVerdict = 'pass' | 'fail' | 'inconclusive' | 'error' | 'skipped'
export type ArbiterTier = 'cheap' | 'standard' | 'max'

export interface ArbiterRingScore {
  ring?: string
  provider?: string
  model?: string
  score?: number
  decision?: string
}

/** Backend default when `pass_threshold` is absent (old payloads). */
export const DEFAULT_PASS_THRESHOLD = 0.5

/** Ring 1 'running' with no event activity for longer than this is stale (C-29). */
export const RING1_STALE_SECONDS = 600

// ---------------------------------------------------------------------------
// View models
// ---------------------------------------------------------------------------

export interface Ring1ViewModel {
  /** details was a non-null object */
  hasDetails: boolean
  /** Normalized ring1_status. Legacy 'pending' -> 'running', 'failed' -> 'error'. null = absent. */
  status: Ring1Status | null
  /** Backend's `passed` verbatim — the UI must NEVER recompute this from score (C-28). */
  passed: boolean | null
  score: number | null
  /** pass_threshold from the payload, default 0.5 for old payloads. */
  threshold: number
  phase: string | null
  checks: VerificationCheck[]
  warnings: string[]
  events: VerificationEvent[]
  /** ring1_error message when status === 'error'. */
  error: string | null
  reviewRequired: boolean
  /** epoch seconds of the most recent verification event, if any. */
  lastEventTs: number | null
  /** status is 'running' but the last event is older than RING1_STALE_SECONDS. */
  stale: boolean
  /** Actively verifying (running and not stale). */
  inProgress: boolean
  /** No further updates expected (complete / error / skipped_no_media / stale). */
  terminal: boolean
  /** verification_events show every started ring reached its *_complete summary. */
  eventsComplete: boolean
  /** Legacy Phase B fields (pre-rings payloads still in the DB). */
  summary: string | null
  phaseBStatus: string | null
  phaseBError: string | null
}

export interface Ring2ViewModel {
  verdict: ArbiterVerdict | null
  tier: ArbiterTier | null
  score: number | null
  confidence: number | null
  grade: string | null
  summary: string | null
  reason: string | null
  disagreement: boolean
  ringScores: ArbiterRingScore[]
  evidenceHash: string | null
  evaluatedAt: string | null
}

export interface VerdictViewModel {
  raw: string | null
  accepted: boolean
  rejected: boolean
  decided: boolean
}

export interface VerificationViewModel {
  ring1: Ring1ViewModel
  ring2: Ring2ViewModel
  verdict: VerdictViewModel
  autoCheckPassed: boolean | null
}

// ---------------------------------------------------------------------------
// agent_verdict helpers (C-27) — the ONLY place 'accepted' vs legacy
// 'approved' is reconciled. Components must not compare string literals.
// ---------------------------------------------------------------------------

export function isVerdictAccepted(verdict: string | null | undefined): boolean {
  // 'approved' is a deprecated alias that very old rows may carry; the
  // backend has only ever written 'accepted' going forward.
  return verdict === AGENT_VERDICT.ACCEPTED || verdict === 'approved'
}

export function isVerdictRejected(verdict: string | null | undefined): boolean {
  return verdict === AGENT_VERDICT.REJECTED
}

export function parseVerdict(verdict: string | null | undefined): VerdictViewModel {
  const raw = typeof verdict === 'string' && verdict.length > 0 ? verdict : null
  return {
    raw,
    accepted: isVerdictAccepted(raw),
    rejected: isVerdictRejected(raw),
    decided: raw !== null,
  }
}

// ---------------------------------------------------------------------------
// verification_events helpers — shared "is this done?" logic
// ---------------------------------------------------------------------------

const TERMINAL_EVENT_STATUSES: ReadonlySet<string> = new Set([
  'complete',
  'failed',
  'error',
  'skipped',
])

export function isEventTerminal(status: string | null | undefined): boolean {
  return typeof status === 'string' && TERMINAL_EVENT_STATUSES.has(status)
}

function parseEvents(raw: unknown): VerificationEvent[] {
  if (!Array.isArray(raw)) return []
  const events: VerificationEvent[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const e = item as Record<string, unknown>
    if (typeof e.step !== 'string' || typeof e.status !== 'string') continue
    events.push({
      ts: typeof e.ts === 'number' ? e.ts : 0,
      ring: typeof e.ring === 'number' ? e.ring : 1,
      step: e.step,
      status: e.status as VerificationEventStatus,
      detail:
        e.detail && typeof e.detail === 'object'
          ? (e.detail as Record<string, unknown>)
          : undefined,
    })
  }
  return events
}

/**
 * True when the event log shows every started ring reached its terminal
 * summary event (ring1_complete, and ring2_complete if any ring-2 event exists).
 *
 * When ring1_complete announces `ring2_queued: true`, Ring 2 IS expected even
 * if its events have not arrived yet (the ~5s gap between Ring 1 finishing and
 * Ring 2 starting). In that window we must NOT declare completion, or the
 * dashboard stops polling before the arbiter verdict appears.
 */
export function verificationEventsComplete(rawEvents: unknown): boolean {
  const events = parseEvents(rawEvents)
  if (events.length === 0) return false
  const ring1Complete = events.find(
    (e) => e.step === 'ring1_complete' && isEventTerminal(e.status),
  )
  if (!ring1Complete) return false
  const ring2Queued = ring1Complete.detail?.ring2_queued === true
  const hasRing2 = events.some((e) => e.ring === 2)
  const ring2Done = events.some(
    (e) => e.step === 'ring2_complete' && isEventTerminal(e.status),
  )
  if (ring2Queued) return ring2Done
  return !hasRing2 || ring2Done
}

// ---------------------------------------------------------------------------
// Ring 1 parser (auto_check_details)
// ---------------------------------------------------------------------------

function normalizeRing1Status(raw: unknown): Ring1Status | null {
  switch (raw) {
    case 'running':
    case 'complete':
    case 'error':
    case 'skipped_no_media':
      return raw
    // Legacy payload values
    case 'pending':
      return 'running'
    case 'failed':
      return 'error'
    default:
      return null
  }
}

function parseChecks(raw: unknown): VerificationCheck[] {
  if (!Array.isArray(raw)) return []
  const checks: VerificationCheck[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const c = item as Record<string, unknown>
    if (typeof c.name !== 'string') continue
    checks.push({
      name: c.name,
      passed: c.passed === true,
      score: typeof c.score === 'number' ? c.score : 0,
      reason: typeof c.reason === 'string' ? c.reason : undefined,
      details:
        c.details && typeof c.details === 'object'
          ? (c.details as Record<string, unknown>)
          : undefined,
    })
  }
  return checks
}

export function parseRing1(details: unknown, nowMs: number = Date.now()): Ring1ViewModel {
  const hasDetails = !!details && typeof details === 'object' && !Array.isArray(details)
  const d = hasDetails ? (details as Record<string, unknown>) : {}

  const status = normalizeRing1Status(d.ring1_status)
  const passed = typeof d.passed === 'boolean' ? d.passed : null
  const score = typeof d.score === 'number' ? d.score : null
  const threshold =
    typeof d.pass_threshold === 'number' ? d.pass_threshold : DEFAULT_PASS_THRESHOLD
  const events = parseEvents(d.verification_events)
  const eventsComplete = verificationEventsComplete(events)

  const lastEventTs =
    events.length > 0 ? events.reduce((max, e) => (e.ts > max ? e.ts : max), 0) : null
  const stale =
    status === 'running' &&
    lastEventTs !== null &&
    nowMs / 1000 - lastEventTs > RING1_STALE_SECONDS

  return {
    hasDetails,
    status,
    passed,
    score,
    threshold,
    phase: typeof d.phase === 'string' ? d.phase : null,
    checks: parseChecks(d.checks),
    warnings: Array.isArray(d.warnings) ? d.warnings.map((w) => String(w)) : [],
    events,
    error: typeof d.ring1_error === 'string' ? d.ring1_error : null,
    reviewRequired: d.review_required === true,
    lastEventTs,
    stale,
    inProgress: status === 'running' && !stale,
    terminal:
      status === 'complete' || status === 'error' || status === 'skipped_no_media' || stale,
    eventsComplete,
    summary: typeof d.summary === 'string' ? d.summary : null,
    phaseBStatus: typeof d.phase_b_status === 'string' ? d.phase_b_status : null,
    phaseBError: typeof d.phase_b_error === 'string' ? d.phase_b_error : null,
  }
}

// ---------------------------------------------------------------------------
// Ring 2 parser (arbiter_* columns on the submission row)
// ---------------------------------------------------------------------------

function normalizeArbiterVerdict(raw: unknown): ArbiterVerdict | null {
  switch (raw) {
    case 'pass':
    case 'fail':
    case 'inconclusive':
    case 'error':
    case 'skipped':
      return raw
    default:
      return null
  }
}

export function parseRing2(row: unknown): Ring2ViewModel {
  const r = row && typeof row === 'object' ? (row as Record<string, unknown>) : {}
  const data =
    r.arbiter_verdict_data && typeof r.arbiter_verdict_data === 'object'
      ? (r.arbiter_verdict_data as Record<string, unknown>)
      : {}

  const score =
    typeof r.arbiter_score === 'number'
      ? r.arbiter_score
      : typeof data.aggregate_score === 'number'
        ? data.aggregate_score
        : null
  const confidence =
    typeof r.arbiter_confidence === 'number'
      ? r.arbiter_confidence
      : typeof data.confidence === 'number'
        ? data.confidence
        : null
  const tierRaw = r.arbiter_tier ?? data.tier
  const tier =
    tierRaw === 'cheap' || tierRaw === 'standard' || tierRaw === 'max' ? tierRaw : null

  return {
    verdict: normalizeArbiterVerdict(r.arbiter_verdict ?? data.decision),
    tier,
    score,
    confidence,
    grade: typeof data.grade === 'string' ? data.grade : null,
    summary: typeof data.summary === 'string' ? data.summary : null,
    reason: typeof data.reason === 'string' ? data.reason : null,
    disagreement: data.disagreement === true,
    ringScores: Array.isArray(data.ring_scores)
      ? (data.ring_scores.filter((s) => s && typeof s === 'object') as ArbiterRingScore[])
      : [],
    evidenceHash: typeof r.arbiter_evidence_hash === 'string' ? r.arbiter_evidence_hash : null,
    evaluatedAt: typeof r.arbiter_evaluated_at === 'string' ? r.arbiter_evaluated_at : null,
  }
}

// ---------------------------------------------------------------------------
// Full submission parser
// ---------------------------------------------------------------------------

export function parseVerification(row: unknown, nowMs: number = Date.now()): VerificationViewModel {
  const r = row && typeof row === 'object' ? (row as Record<string, unknown>) : {}
  return {
    ring1: parseRing1(r.auto_check_details, nowMs),
    ring2: parseRing2(r),
    verdict: parseVerdict(typeof r.agent_verdict === 'string' ? r.agent_verdict : null),
    autoCheckPassed: typeof r.auto_check_passed === 'boolean' ? r.auto_check_passed : null,
  }
}
