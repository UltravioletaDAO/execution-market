# City as a Service — Daytime Closure-Proof Checklist

> Last updated: 2026-05-05
> Parent docs:
> - `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_04.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_PICKUP_BRIEF_CONTRACT.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md`
> Status: operator-grade daylight closure checklist

## 1. Why this doc exists

The planning stack already says what the closure-proof seam must preserve.
What is still easy to lose in a real daytime block is simple execution discipline:
- forgetting one closure artifact
- reviewing artifacts in the wrong order
- shipping a good scoreboard with a weak pickup brief
- claiming handoff readiness before closure packaging is checked

This checklist compresses the closure-proof seam into one daylight execution card.

> a proof block is not done when the scoreboards pass.
> it is done when closure truth survives manifest, telemetry, and pickup packaging unchanged.

## 2. When to use this checklist

Use this at the end of every replay-backed city proof block that claims any of the following:
- shared decision parity
- behavior-change proof
- pickup continuity readiness
- telemetry carry-forward readiness
- local Acontext/export readiness

If the block cannot clear this checklist, the correct result is `tighten_same_seam` or `fix_drift_before_expand`, not a soft “basically done.”

## 3. Required review order

Review these artifacts in this order:
1. `bundle_manifest.json`
2. `event_summary.json`
3. `review_packet.json`
4. `city_shared_decision_parity_scoreboard.json`
5. `city_reuse_behavior_scoreboard.json` when reuse is in scope
6. proof-block telemetry gate row
7. `morning_pickup_brief.json`

Do not review the pickup brief before the telemetry row.
The pickup brief is a mirror of closure truth, not a replacement for it.

## 4. Closure-proof checklist

### 4.1 Proof block inputs exist
- [ ] manifest exists and declares the required artifacts
- [ ] event summary exists and ordering is deterministic
- [ ] review packet exists and states the reviewed decision compactly
- [ ] parity scoreboard exists
- [ ] reuse behavior scoreboard exists when reuse is in scope
- [ ] telemetry gate row exists
- [ ] pickup brief exists

### 4.2 Combined verdict integrity
- [ ] one combined verdict is explicit: `ship_same_seam`, `tighten_same_seam`, or `fix_drift_before_expand`
- [ ] the combined verdict matches the dangerous-axis reading of the parity scoreboard
- [ ] the combined verdict matches the trust-preservation result of the reuse scorecard
- [ ] behavior-change class is not overstated anywhere in the closure package

### 4.3 Claim-limit preservation
- [ ] `combined_verdict` matches exactly across scoreboards, telemetry, and pickup brief
- [ ] `behavior_change_class` matches exactly across telemetry and pickup brief
- [ ] `trust_preservation_result` matches exactly across telemetry and pickup brief
- [ ] `dangerous_axes_failed[]` is preserved without omission
- [ ] `supported_behavior_change_reason[]` is preserved without stronger wording
- [ ] `do_not_claim_yet[]` remains visible and unchanged in meaning
- [ ] `next_smallest_proof[]` remains concrete enough for the next session to act

### 4.4 Dangerous drift rejection gate
- [ ] no promotion drift
- [ ] no tone drift implying stronger confidence
- [ ] no placement drift into directive/copyable sections beyond promotion class
- [ ] no copyability drift
- [ ] no anti-overclaim loss
- [ ] no readiness inflation
- [ ] no provenance loss that blocks auditability
- [ ] no telemetry packaging drift

If any item above fails, the block must end as `fix_drift_before_expand`.

### 4.5 Closure packaging fidelity
- [ ] telemetry row is compact but not semantically stronger than the scoreboards
- [ ] pickup brief is compact but not semantically stronger than the telemetry row
- [ ] readiness flags stay conservative
- [ ] explicit downgrade count is preserved or deterministically summarized
- [ ] the next session could choose the right next move from the pickup brief alone

## 5. Pass / partial / fail interpretation

### Pass
Use when:
- all required artifacts exist
- dangerous axes remain explicit
- closure package preserves exact verdict and claim limits
- next-smallest-proof guidance is actionable without reopening the full archive

### Partial
Use when:
- closure truth is mostly preserved
- no dangerous inflation occurred
- but the next-step guidance, readiness packaging, or compact continuity object is still too vague

This should usually map to `tighten_same_seam`.

### Fail
Use when:
- any dangerous axis is lost, softened, or upgraded
- pickup language is stronger than telemetry language
- telemetry language is stronger than scoreboard truth
- the next session would inherit unjustified certainty

This should map to `fix_drift_before_expand`.

## 6. Required output of the checklist

Every reviewed closure-proof block should end with one compact daylight note containing:
- `combined_verdict`
- `behavior_change_class`
- `trust_preservation_result`
- `dangerous_axes_failed[]`
- `do_not_claim_yet[]`
- `next_smallest_proof[]`
- checklist result: `pass`, `partial`, or `fail`

That note may live in PR commentary, a review card, or a continuity artifact.
It may not contradict the telemetry row or pickup brief.

## 7. Sharp recommendation

**Use this checklist as the last daylight gate before claiming handoff-safe proof.**

The first City-as-a-Service flywheel becomes real only when:
- the next dispatch got smarter for the right reason
- the scoreboards proved it honestly
- the closure package kept that truth intact for the next session
