# City as a Service — Shared Decision Parity Scoreboard

> Last updated: 2026-05-03
> Parent docs:
> - `CITY_AS_A_SERVICE_SHARED_RENDERING_TRUTH_CONTRACT.md`
> - `CITY_AS_A_SERVICE_DECISION_SEAM_ACCEPTANCE_HARNESS.md`
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_TARGET_AND_DECISION_FLYWHEEL.md`
> Status: daytime proof-harness companion

## 1. Why this doc exists

The planning stack already says what should be true:
- one replay-backed city judgment should become one shared decision seam
- every runtime and reuse consumer should preserve the same trust posture
- drift should fail loudly instead of hiding inside formatting differences

What is still missing is one compact scoring surface that daytime can use to prove that parity actually held.
Without that scoreboard, the next build window could still produce:
- a good normalized helper
- several aligned consumers
- a few drift fixtures
- but no single artifact that says whether the full chain stayed semantically identical where it mattered

This doc closes that gap.

> the next proof should end with one scoreboard that grades whether the same judged truth survived replay, runtime carriage, reuse, rebuild, and measurement without trust drift.

## 2. The product question this scoreboard answers

For one replay-backed city case:

> did every consumer preserve the same decision semantics, and did the next dispatch change for the right reason?

That is the shortest pass/fail lens for the current City-as-a-Service flywheel.

## 3. Scoreboard scope

The first scoreboard should compare one shared decision seam across these artifacts and consumers:
- `review_packet.json`
- `city_compact_decision_object.json`
- `city_dispatch_brief.json`
- `morning_pickup_brief.json`
- `city_dispatch_memory_unit.json`
- session rebuild output
- runtime observability row
- reuse observability row
- one dispatch-context reuse output
- one redispatch or worker-instruction output
- mirrored coordination ledger rows for each emitted consumer event

The scoreboard does not replace the underlying artifacts.
It exists so reviewers do not have to infer semantic parity by manually diffing ten outputs.

## 4. Canonical scoreboard questions

The first-pass scoreboard should answer these questions explicitly:
1. Did all consumers preserve the same promotion class?
2. Did all consumers preserve the same guidance tone?
3. Did all consumers preserve the same guidance placement boundary?
4. Did copyability stay conservative across worker-facing outputs?
5. Did pickup/export/rebuild preserve the same anti-overclaim warnings?
6. Did reuse change actual dispatch behavior or only display memory?
7. Did observability rows record the same governing trust posture?
8. Did ledger mirrors preserve the same decision identity and trust fields?
9. Did any consumer require an explicit downgrade?
10. If the next dispatch changed, was that change supported and trust-preserving?

## 5. Required identity and invariant fields

The scoreboard should compare, at minimum:
- `compact_decision_id`
- `coordination_session_id`
- `review_packet_id`
- `summary_judgment`
- `memory_promotion_decision`
- `guidance_mode`
- `target_section_family`
- `copyable_worker_instruction_eligibility`
- `continuity_ready`
- `export_ready`
- `session_rebuild_ready`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`

If any consumer does not surface one of these directly, the scoreboard should require either:
- deterministic derivation from the shared decision seam, or
- an explicit downgrade note

## 6. Score axes

### 6.1 Semantic parity axis
Grades whether the exact same decision semantics survived all consumers.

Possible values:
- `pass` — all required invariant fields matched or were explicitly downgraded without trust strengthening
- `partial` — no dangerous strengthening, but at least one consumer required review-worthy downgrade or omitted a non-critical field
- `fail` — any promotion/tone/placement/copyability/anti-overclaim drift occurred

### 6.2 Behavior-change axis
Grades whether the next dispatch actually changed in an operationally meaningful way.

Possible values:
- `shown_only`
- `routing_changed`
- `instruction_changed`
- `evidence_guidance_changed`
- `redispatch_changed`
- `escalation_changed`
- `fail`

### 6.3 Trust-preservation axis
Grades whether the behavior change stayed within judged trust posture.

Possible values:
- `pass`
- `partial`
- `fail`

A behavior change is not a product win if this axis fails.

### 6.4 Rebuild parity axis
Grades whether the same next move can be reconstructed from compact object + ledger tail alone.

Possible values:
- `pass`
- `partial`
- `fail`

### 6.5 Observability parity axis
Grades whether runtime and reuse rows recorded the same governing trust semantics and behavior-change class.

Possible values:
- `pass`
- `partial`
- `fail`

## 7. Recommended scoreboard shape

```json
{
  "case_id": "city_packet_submission_redirect_20260503_001",
  "compact_decision_id": "cdo_city_packet_submission_20260503_001",
  "review_packet_id": "rp_city_packet_submission_20260503_001",
  "coordination_session_id": "city_packet_submission_miami_dade_20260503_001",
  "semantic_parity": "pass",
  "behavior_change": "routing_changed",
  "trust_preservation": "pass",
  "rebuild_parity": "pass",
  "observability_parity": "pass",
  "consumer_checks": {
    "dispatch_brief": "pass",
    "pickup_brief": "pass",
    "memory_export": "pass",
    "session_rebuild": "pass",
    "runtime_observability": "pass",
    "reuse_observability": "pass",
    "dispatch_reuse": "pass",
    "worker_instruction_or_redispatch": "partial",
    "ledger_mirror": "pass"
  },
  "invariant_field_checks": {
    "guidance_mode": "pass",
    "target_section_family": "pass",
    "copyable_worker_instruction_eligibility": "pass",
    "not_safe_to_claim": "pass",
    "session_rebuild_ready": "pass"
  },
  "downgrades": [
    {
      "consumer": "worker_instruction_or_redispatch",
      "kind": "explicit_downgrade",
      "note": "cautious learning remained non-copyable during worker-instruction rendering"
    }
  ],
  "supported_behavior_change_reason": [
    "reviewed redirect evidence changed the likely first-stop routing recommendation"
  ],
  "failure_triggers": [],
  "next_smallest_proof": [
    "prove the same parity under an appointment-required redispatch case"
  ]
}
```

## 8. How to grade each consumer

### 8.1 Dispatch Brief
Pass only if it preserves:
- guidance mode
- section family
- copyability boundary
- anti-overclaim warnings

Fail if cautious or inspect-only learning appears as top-line doctrine.

### 8.2 Morning Pickup Brief
Pass only if it preserves:
- continuity posture
- rebuild readiness posture
- anti-overclaim posture
- next smallest proof

Fail if `verify_first` or `inspect_only` becomes `action_now` tone.

### 8.3 Memory export
Pass only if export preserves the same trust semantics without re-derivation.

Fail if future retrieval would have to guess promotion or guidance class.

### 8.4 Session rebuild
Pass only if rebuild restores the same next move and trust posture from compact object + ledger tail.

Fail if transcript archaeology is required.

### 8.5 Runtime observability
Pass only if the row records:
- identity fields
- governing trust posture
- behavior-change classification or lack thereof

Fail if the row implies stronger readiness or stronger trust than the shared decision seam allowed.

### 8.6 Reuse observability
Pass only if it records whether memory was shown versus materially used, plus the exact behavior-change class.

### 8.7 Dispatch reuse / redispatch / worker instruction
Pass only if the actual operational change is explainable from the same judged truth.

Fail if the behavior change exceeds trust posture or becomes copyable when the seam forbids it.

### 8.8 Ledger mirror rows
Pass only if mirrored rows preserve identity + trust fields consistently across event types.

Fail if a downstream event loses provenance or silently mutates trust semantics.

## 9. Loud-fail triggers

The scoreboard should mark overall failure if any of these occur:
- promotion drift
- tone drift
- placement drift
- copyability drift
- anti-overclaim loss
- readiness drift
- provenance loss
- observability trust inflation
- rebuild requiring transcript dependency

These should not be buried as low-severity notes.
They mean the shared decision seam is not yet real.

## 10. Relationship to the acceptance harness

The acceptance harness says what artifacts and flows must exist.
This scoreboard says whether they stayed aligned.

Use them together like this:
1. acceptance harness checks presence and required proof flow
2. parity scoreboard checks semantic sameness and behavior-change legitimacy

The daytime build should not claim success if the harness passes but the parity scoreboard is only `partial` or `fail` on a dangerous axis.

## 11. Recommended implementation order

### Step 1
Emit one scoreboard artifact per replay-backed proof case.

### Step 2
Populate invariant field checks directly from the shared decision helper output and each consumer artifact.

### Step 3
Populate behavior-change and trust-preservation checks from reuse outputs plus observability rows.

### Step 4
Mirror scoreboard summary into one coordination-ledger event so later audits can find the final judgment quickly.

### Step 5
Add fixture-backed failure cases that deliberately trigger tone, placement, copyability, anti-overclaim, and rebuild drift.

## 12. Acceptance gate for this scoreboard slice

Do not call the current City-as-a-Service decision seam proven until one replay-backed case can produce a scoreboard artifact showing:
- `semantic_parity=pass`
- behavior change beyond `shown_only`
- `trust_preservation=pass`
- `rebuild_parity=pass`
- `observability_parity=pass`
- no hidden drift behind missing fields or silent downgrades

## 13. Sharp recommendation

**Make the next daytime proof end in one parity scoreboard, not just a pile of aligned artifacts.**

That is the cleanest way to prove the same reviewed truth actually survived the whole City-as-a-Service decision flywheel.