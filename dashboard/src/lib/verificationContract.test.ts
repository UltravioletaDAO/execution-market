/**
 * Phase 3 (Rings Verification) — contract tests for lib/verificationContract.
 *
 * Fixtures mirror the canonical shapes the backend REALLY writes today
 * (C-27/C-28/C-29/C-34): auto_check_details with pass_threshold 0.5 +
 * ring1_status running|complete|error|skipped_no_media, agent_verdict
 * 'accepted'/'rejected', and the arbiter_* Ring 2 columns.
 */

import { describe, it, expect } from 'vitest'
import {
  DEFAULT_PASS_THRESHOLD,
  RING1_STALE_SECONDS,
  isVerdictAccepted,
  isVerdictRejected,
  parseVerdict,
  parseRing1,
  parseRing2,
  parseVerification,
  verificationEventsComplete,
  isEventTerminal,
} from './verificationContract'

const NOW_MS = 1_750_000_000_000 // fixed clock for staleness assertions
const NOW_SECS = NOW_MS / 1000

// ---------------------------------------------------------------------------
// Fixtures — canonical backend payloads
// ---------------------------------------------------------------------------

/** Completed run that PASSED at the backend threshold (0.5) with a score the
 *  old UI would have painted amber (< 0.7) — the C-28 regression case. */
const detailsCompletePass = {
  passed: true,
  score: 0.55,
  pass_threshold: 0.5,
  phase: 'AB',
  ring1_status: 'complete',
  checks: [
    { name: 'schema', passed: true, score: 1.0, reason: 'all fields present' },
    { name: 'gps', passed: false, score: 0.2, reason: 'outside radius' },
  ],
  warnings: ['GPS slightly off'],
  verification_events: [
    { ts: NOW_SECS - 120, ring: 1, step: 'exif_extraction', status: 'complete', detail: {} },
    { ts: NOW_SECS - 60, ring: 1, step: 'ring1_complete', status: 'complete', detail: { score: 0.55 } },
  ],
}

const detailsError = {
  passed: false,
  score: 0.3,
  pass_threshold: 0.5,
  phase: 'A',
  ring1_status: 'error',
  ring1_error: 'PHOTINT provider timeout after 3 retries',
  review_required: true,
  checks: [],
  warnings: [],
  verification_events: [
    { ts: NOW_SECS - 30, ring: 1, step: 'tampering', status: 'error', detail: { error: 'timeout' } },
  ],
}

const detailsSkippedNoMedia = {
  passed: true,
  score: 0.8,
  pass_threshold: 0.5,
  phase: 'A',
  ring1_status: 'skipped_no_media',
  checks: [{ name: 'schema', passed: true, score: 1.0 }],
  warnings: [],
}

/** Running but the last event is older than the 10-minute staleness window. */
const detailsRunningStale = {
  passed: false,
  score: 0,
  pass_threshold: 0.5,
  phase: 'A',
  ring1_status: 'running',
  checks: [],
  warnings: [],
  verification_events: [
    { ts: NOW_SECS - (RING1_STALE_SECONDS + 60), ring: 1, step: 'exif_extraction', status: 'running', detail: {} },
  ],
}

const detailsRunningFresh = {
  ...detailsRunningStale,
  verification_events: [
    { ts: NOW_SECS - 30, ring: 1, step: 'exif_extraction', status: 'running', detail: {} },
  ],
}

/** Submission row with an inconclusive Ring 2 arbiter verdict. */
const submissionArbiterInconclusive = {
  agent_verdict: null,
  auto_check_passed: true,
  auto_check_details: detailsCompletePass,
  arbiter_verdict: 'inconclusive',
  arbiter_tier: 'standard',
  arbiter_score: 0.62,
  arbiter_confidence: 0.41,
  arbiter_evaluated_at: '2026-06-11T22:00:00Z',
  arbiter_verdict_data: {
    decision: 'inconclusive',
    tier: 'standard',
    aggregate_score: 0.62,
    confidence: 0.41,
    grade: 'C',
    summary: 'Models disagree on evidence sufficiency',
    ring_scores: [
      { ring: 'L1a', provider: 'google', model: 'gemini', score: 0.8, decision: 'pass' },
      { ring: 'L1b', provider: 'anthropic', model: 'claude', score: 0.45, decision: 'fail' },
    ],
  },
}

// ---------------------------------------------------------------------------
// agent_verdict mapping (C-27): backend writes 'accepted', never 'approved'
// ---------------------------------------------------------------------------

describe('agent_verdict mapping (C-27)', () => {
  it("treats the canonical 'accepted' as accepted", () => {
    expect(isVerdictAccepted('accepted')).toBe(true)
    expect(parseVerdict('accepted')).toEqual({
      raw: 'accepted',
      accepted: true,
      rejected: false,
      decided: true,
    })
  })

  it("tolerates the legacy 'approved' alias through the single helper", () => {
    expect(isVerdictAccepted('approved')).toBe(true)
    expect(parseVerdict('approved').accepted).toBe(true)
  })

  it("maps 'rejected'", () => {
    expect(isVerdictRejected('rejected')).toBe(true)
    expect(isVerdictAccepted('rejected')).toBe(false)
    expect(parseVerdict('rejected')).toEqual({
      raw: 'rejected',
      accepted: false,
      rejected: true,
      decided: true,
    })
  })

  it('maps null/undefined/empty to undecided', () => {
    for (const v of [null, undefined, '']) {
      const vm = parseVerdict(v)
      expect(vm.decided).toBe(false)
      expect(vm.accepted).toBe(false)
      expect(vm.rejected).toBe(false)
    }
  })
})

// ---------------------------------------------------------------------------
// Ring 1 — complete / pass at backend threshold (C-28)
// ---------------------------------------------------------------------------

describe('parseRing1 — complete payload (C-28)', () => {
  it('renders the backend passed verbatim, never recomputing from score', () => {
    const vm = parseRing1(detailsCompletePass, NOW_MS)
    expect(vm.passed).toBe(true) // score 0.55 < 0.7 but backend passed
    expect(vm.score).toBe(0.55)
    expect(vm.threshold).toBe(0.5)
    expect(vm.status).toBe('complete')
    expect(vm.terminal).toBe(true)
    expect(vm.inProgress).toBe(false)
    expect(vm.stale).toBe(false)
    expect(vm.eventsComplete).toBe(true)
  })

  it('badge == backend passed for ANY score (both directions)', () => {
    // High score but backend failed it
    const failedHigh = parseRing1({ ...detailsCompletePass, passed: false, score: 0.9 }, NOW_MS)
    expect(failedHigh.passed).toBe(false)
    // Low score but backend passed it
    const passedLow = parseRing1({ ...detailsCompletePass, passed: true, score: 0.51 }, NOW_MS)
    expect(passedLow.passed).toBe(true)
  })

  it('defaults pass_threshold to 0.5 for old payloads and never invents passed', () => {
    const legacy: Record<string, unknown> = { ...detailsCompletePass }
    delete legacy.pass_threshold
    delete legacy.passed
    const vm = parseRing1(legacy, NOW_MS)
    expect(vm.threshold).toBe(DEFAULT_PASS_THRESHOLD)
    expect(vm.passed).toBeNull()
  })

  it('parses checks and warnings', () => {
    const vm = parseRing1(detailsCompletePass, NOW_MS)
    expect(vm.checks).toHaveLength(2)
    expect(vm.checks[0]).toMatchObject({ name: 'schema', passed: true, score: 1.0 })
    expect(vm.checks[1]).toMatchObject({ name: 'gps', passed: false, score: 0.2 })
    expect(vm.warnings).toEqual(['GPS slightly off'])
  })
})

// ---------------------------------------------------------------------------
// Ring 1 — error / skipped_no_media (C-04)
// ---------------------------------------------------------------------------

describe('parseRing1 — error payload (C-04)', () => {
  it('is terminal with the backend error surfaced', () => {
    const vm = parseRing1(detailsError, NOW_MS)
    expect(vm.status).toBe('error')
    expect(vm.error).toBe('PHOTINT provider timeout after 3 retries')
    expect(vm.reviewRequired).toBe(true)
    expect(vm.terminal).toBe(true)
    expect(vm.inProgress).toBe(false)
  })

  it("normalizes legacy 'failed' to 'error'", () => {
    const vm = parseRing1({ ...detailsError, ring1_status: 'failed' }, NOW_MS)
    expect(vm.status).toBe('error')
  })
})

describe('parseRing1 — skipped_no_media payload', () => {
  it('is terminal and not in progress', () => {
    const vm = parseRing1(detailsSkippedNoMedia, NOW_MS)
    expect(vm.status).toBe('skipped_no_media')
    expect(vm.terminal).toBe(true)
    expect(vm.inProgress).toBe(false)
    expect(vm.stale).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Ring 1 — running / staleness (C-29: no eternal spinners)
// ---------------------------------------------------------------------------

describe('parseRing1 — running payloads (C-29)', () => {
  it('flags running with >10 min of event silence as stale + terminal', () => {
    const vm = parseRing1(detailsRunningStale, NOW_MS)
    expect(vm.status).toBe('running')
    expect(vm.stale).toBe(true)
    expect(vm.inProgress).toBe(false)
    expect(vm.terminal).toBe(true)
  })

  it('keeps fresh running payloads in progress', () => {
    const vm = parseRing1(detailsRunningFresh, NOW_MS)
    expect(vm.stale).toBe(false)
    expect(vm.inProgress).toBe(true)
    expect(vm.terminal).toBe(false)
    expect(vm.lastEventTs).toBe(NOW_SECS - 30)
  })

  it('running with no events cannot be judged stale', () => {
    const vm = parseRing1({ ...detailsRunningStale, verification_events: [] }, NOW_MS)
    expect(vm.stale).toBe(false)
    expect(vm.inProgress).toBe(true)
  })

  it("normalizes legacy 'pending' to 'running'", () => {
    const vm = parseRing1({ ...detailsRunningFresh, ring1_status: 'pending' }, NOW_MS)
    expect(vm.status).toBe('running')
  })
})

describe('parseRing1 — malformed/absent payloads', () => {
  it('handles null/undefined/non-object details', () => {
    for (const d of [null, undefined, 'oops', 42, []]) {
      const vm = parseRing1(d, NOW_MS)
      expect(vm.hasDetails).toBe(false)
      expect(vm.status).toBeNull()
      expect(vm.passed).toBeNull()
      expect(vm.checks).toEqual([])
      expect(vm.terminal).toBe(false)
    }
  })

  it('ignores phantom fields nobody writes (C-34)', () => {
    const vm = parseRing1(
      {
        ...detailsCompletePass,
        ring1_decision: 'approved',
        ring1_provider: 'ghost',
        ring1_attempts: [{ provider: 'x', status: 'success' }],
        ring2_status: 'complete',
        ring2_decision: 'approved',
      },
      NOW_MS,
    )
    // Phantom fields do not leak into the view-model
    expect(vm).not.toHaveProperty('ring1_decision')
    expect(vm).not.toHaveProperty('ring2_status')
    expect(vm.status).toBe('complete')
    expect(vm.passed).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// verification_events helpers
// ---------------------------------------------------------------------------

describe('verificationEventsComplete / isEventTerminal', () => {
  it('treats complete/failed/error/skipped as terminal', () => {
    for (const s of ['complete', 'failed', 'error', 'skipped']) {
      expect(isEventTerminal(s)).toBe(true)
    }
    for (const s of ['running', 'pending', null, undefined]) {
      expect(isEventTerminal(s)).toBe(false)
    }
  })

  it('requires ring1_complete, and ring2_complete only when ring 2 ran', () => {
    expect(verificationEventsComplete(detailsCompletePass.verification_events)).toBe(true)
    expect(verificationEventsComplete(detailsRunningFresh.verification_events)).toBe(false)
    expect(verificationEventsComplete([])).toBe(false)
    expect(verificationEventsComplete(undefined)).toBe(false)
    // Ring 2 started but no summary yet -> incomplete
    expect(
      verificationEventsComplete([
        { ts: 1, ring: 1, step: 'ring1_complete', status: 'complete' },
        { ts: 2, ring: 2, step: 'llm_primary', status: 'running' },
      ]),
    ).toBe(false)
    // Ring 2 reached an error summary -> complete (terminal)
    expect(
      verificationEventsComplete([
        { ts: 1, ring: 1, step: 'ring1_complete', status: 'complete' },
        { ts: 2, ring: 2, step: 'ring2_complete', status: 'error' },
      ]),
    ).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Ring 2 — arbiter columns
// ---------------------------------------------------------------------------

describe('parseRing2 — arbiter verdict (inconclusive fixture)', () => {
  it('produces the typed view-model from the arbiter_* columns', () => {
    const vm = parseRing2(submissionArbiterInconclusive)
    expect(vm.verdict).toBe('inconclusive')
    expect(vm.tier).toBe('standard')
    expect(vm.score).toBe(0.62)
    expect(vm.confidence).toBe(0.41)
    expect(vm.grade).toBe('C')
    expect(vm.summary).toBe('Models disagree on evidence sufficiency')
    expect(vm.ringScores).toHaveLength(2)
    expect(vm.evaluatedAt).toBe('2026-06-11T22:00:00Z')
  })

  it('accepts every contract verdict value, including error', () => {
    for (const v of ['pass', 'fail', 'inconclusive', 'error', 'skipped']) {
      expect(parseRing2({ arbiter_verdict: v }).verdict).toBe(v)
    }
    expect(parseRing2({ arbiter_verdict: 'bogus' }).verdict).toBeNull()
    expect(parseRing2({}).verdict).toBeNull()
    expect(parseRing2(null).verdict).toBeNull()
  })

  it('falls back to verdict_data aggregate_score/confidence when columns absent', () => {
    const vm = parseRing2({
      arbiter_verdict: 'pass',
      arbiter_verdict_data: { aggregate_score: 0.91, confidence: 0.88, tier: 'cheap' },
    })
    expect(vm.score).toBe(0.91)
    expect(vm.confidence).toBe(0.88)
    expect(vm.tier).toBe('cheap')
  })
})

// ---------------------------------------------------------------------------
// Full submission parse
// ---------------------------------------------------------------------------

describe('parseVerification — full row', () => {
  it('combines ring1 + ring2 + verdict + auto_check_passed', () => {
    const vm = parseVerification(submissionArbiterInconclusive, NOW_MS)
    expect(vm.autoCheckPassed).toBe(true)
    expect(vm.ring1.status).toBe('complete')
    expect(vm.ring1.passed).toBe(true)
    expect(vm.ring2.verdict).toBe('inconclusive')
    expect(vm.verdict.decided).toBe(false)
  })

  it('survives an empty row', () => {
    const vm = parseVerification({}, NOW_MS)
    expect(vm.autoCheckPassed).toBeNull()
    expect(vm.ring1.hasDetails).toBe(false)
    expect(vm.ring2.verdict).toBeNull()
    expect(vm.verdict.decided).toBe(false)
  })
})
