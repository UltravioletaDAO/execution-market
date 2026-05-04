# City as a Service — Daytime Replay Proof Runbook

> Last updated: 2026-05-04
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_DECISION_SEAM_ACCEPTANCE_HARNESS.md`
> - `CITY_AS_A_SERVICE_SHARED_DECISION_PARITY_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_REUSE_BEHAVIOR_PROOF_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_DECISION_DRIFT_TRIAGE_PLAYBOOK.md`
> Status: daytime operator/developer runbook

## 1. Why this doc exists

The planning stack already says:
- what the replay artifacts are
- how they should be reviewed
- what scoreboards must prove
- how drift should be triaged

What was still missing was one **single execution runbook** that tells daytime exactly how to run a proof block from start to finish without stitching six docs together by hand.

This doc closes that gap.

> use this runbook when the goal is to prove one replay-backed city-ops decision seam end to end.

## 2. What this runbook is for

Use it when daytime wants to do one of these:
- implement the first projection/helper slice
- run or review a replay-proof fixture batch
- judge whether a seam is ready for broader UI wiring
- localize parity or reuse drift quickly

Do not use it for broad strategy, new template ideation, or multi-city planning.

## 3. The one-sentence objective

**Prove that one reviewed municipal outcome makes the next dispatch smarter in a traceable, trust-preserving way.**

## 4. Inputs required before starting

A proof block should not start until these exist:
- one replay-backed fixture or tight fixture batch
- valid `review_packet` inputs
- a known target consumer set
- a clear expected behavior-change class
- a chosen scope id / coordination session id

Minimum fixture set recommendation:
- one redirect case
- one rejection case
- optionally one weak-learning or evidence-restriction case

## 5. Canonical execution order

### Step 1 — choose the proof case
Pick the smallest fixture that can still produce a meaningful next-dispatch change.

Preferred order:
1. redirect case
2. evidence restriction case
3. repeated rejection case
4. appointment-required redispatch case
5. weak-learning hold/suppress case

### Step 2 — emit the proof archive
Generate or verify the replay bundle artifacts:
- `reviewed_result.json`
- `review_artifact.json`
- `reviewed_episode.json`
- `office_playbook_delta.json` when meaningful
- `office_playbook_after.json` when applicable
- `bundle_manifest.json`
- `event_summary.json`
- `review_packet.json`

### Step 3 — emit the shared decision seam
Generate or verify:
- `city_compact_decision_object.json`
- `morning_pickup_brief.json`
- `city_dispatch_brief.json`
- `city_dispatch_memory_unit.json`
- rebuild output / preview
- runtime observability row
- reuse observability row when reuse is in scope
- reuse output (`dispatch_reuse`, `redispatch`, or `worker_instruction`)

### Step 4 — emit the proof receipts
Generate or verify:
- `brief_improvement_scorecard.json`
- `city_shared_decision_parity_scoreboard.json`
- `city_reuse_behavior_scoreboard.json` when behavior reuse is in scope

### Step 5 — review in strict order
Read artifacts in this order only:
1. `bundle_manifest.json`
2. `event_summary.json`
3. `review_packet.json`
4. `city_compact_decision_object.json`
5. `morning_pickup_brief.json`
6. `brief_improvement_scorecard.json`
7. `city_dispatch_brief.json`
8. baseline brief if present
9. scoreboards
10. deeper artifacts only as needed

### Step 6 — classify the outcome
Classify the proof block as:
- `pass`
- `partial`
- `fail`

Also classify:
- learning strength: `weak` / `moderate` / `strong`
- behavior change: `shown_only` / `routing_changed` / `instruction_changed` / `evidence_guidance_changed` / `redispatch_changed` / `escalation_changed`

### Step 7 — decide the next move
Only three honest next moves exist:
- broaden to another fixture in the same seam
- tighten replay/projection/consumer drift
- wire the proven seam into the next consumer/UI surface

If the proof is partial or failed, do not expand scope.

## 6. Pass criteria

A proof block is `pass` only when all are true:
- artifact chain is complete
- event order is compact and clear
- `review_packet` is promotion-safe and legible
- compact decision object makes runtime semantics explicit
- pickup brief states next smallest proof and anti-overclaim warnings
- scorecard shows operational improvement, not just wording growth
- parity scoreboard passes dangerous axes
- reuse scoreboard proves smarter-for-right-reason when reuse is in scope
- surfaced guidance tone and placement match the governing promotion class

## 7. Partial criteria

A proof block is `partial` when:
- artifact chain is mostly valid
- semantics are inspectable
- but one critical bar is not cleared yet

Common partial states:
- behavior change is still `shown_only`
- scorecard improvement is real but weak
- packet is sound but brief tone/placement still flattens confidence classes
- parity preserved but reuse proof not yet meaningful

## 8. Fail criteria

A proof block is `fail` when any of these happen:
- contracts broken or missing required artifacts
- event story unclear
- packet overclaims
- parity scoreboard fails dangerous axes
- cautious/inspect-only learning renders as directive
- non-copyable guidance becomes copyable
- anti-overclaim protections disappear
- rebuild or observability implies stronger readiness than allowed
- behavior change happens without judged support

## 9. Drift response protocol

If the block fails, triage in this order:
1. `review_packet.json`
2. normalized decision projection
3. `city_compact_decision_object.json`
4. affected consumer output
5. ledger rows
6. observability rows
7. scoreboards

Classify drift as one of:
- projection drift
- consumer drift
- downgrade drift
- mirror drift

Then tag the invariant family first:
- promotion
- tone
- placement
- copyability
- anti-overclaim
- readiness
- provenance
- behavior-class

Use `CITY_AS_A_SERVICE_DECISION_DRIFT_TRIAGE_PLAYBOOK.md` as the required debugging companion.

## 10. What to record in the pickup brief

Every proof block should leave behind one compact continuity object that answers:
- what passed
- what failed or stayed partial
- what changed behaviorally
- what the team must not claim yet
- what the next smallest proof is

Required anti-overclaim rule:
If the block is not clearly behavior-improving and trust-preserving, the pickup brief must say so plainly.

## 11. Recommended review questions

A reviewer should be able to answer these quickly:
1. What changed in the next dispatch?
2. Why was that change allowed?
3. Which packet and episode justified it?
4. Did every consumer preserve the same trust posture?
5. What is the next smallest proof if we stop here?

If those answers are not obvious, the seam is not ready to expand.

## 12. Strong recommendation

**Treat every daytime replay-proof block as one mini flight checklist: archive -> decision seam -> proof receipts -> judgment -> next smallest proof.**

That keeps City as a Service moving like an engineering system instead of a pile of planning docs.
