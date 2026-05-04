# City as a Service — Daytime Proof-Block Scoreboard Protocol

> Last updated: 2026-05-04
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_REPLAY_PROOF_RUNBOOK.md`
> - `CITY_AS_A_SERVICE_SHARED_DECISION_PARITY_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_REUSE_BEHAVIOR_PROOF_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_DECISION_DRIFT_TRIAGE_PLAYBOOK.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_REVIEW_CARD.md`
> Status: daytime proof-block judgment protocol

## 1. Why this doc exists

The planning stack already has:
- a strict execution runbook
- a parity scoreboard
- a reuse-behavior scoreboard
- a drift triage playbook
- a first-PR review gate

What is still easy to lose in practice is the **joint reading discipline** between those pieces.
A team can still:
- run a proof block
- emit both scoreboards
- see one `pass` and one `partial`
- then argue informally about whether the seam is “basically done”

This doc closes that gap.

> every daytime proof block should end with one scoreboard verdict protocol that combines semantic parity and behavior proof into one honest ship / no-ship decision.

## 2. The single question

For one replay-backed city case:

> did the same judged truth survive every consumer, and did it change the next dispatch for the right reason strongly enough to justify the next scope move?

That question is stricter than either scoreboard alone.

## 3. Inputs to this protocol

A valid proof-block judgment requires all of these:
- `bundle_manifest.json`
- `event_summary.json`
- `review_packet.json`
- `city_compact_decision_object.json`
- `morning_pickup_brief.json`
- `city_dispatch_brief.json`
- `brief_improvement_scorecard.json`
- `city_shared_decision_parity_scoreboard.json`
- `city_reuse_behavior_scoreboard.json` when reuse is in scope
- any explicit downgrade notes

If either scoreboard is missing when it should exist, the verdict is automatically `partial` at best.

## 4. Combined scoreboard verdicts

The proof block should end in exactly one of these combined verdicts:
- `ship_same_seam`
- `tighten_same_seam`
- `fix_drift_before_expand`

These are intentionally action-oriented rather than descriptive.

## 5. Verdict rules

### 5.1 `ship_same_seam`
Use only when all are true:
- parity scoreboard says `semantic_parity=pass`
- trust-preservation axes pass
- dangerous drift axes all pass
- behavior-change proof is stronger than `shown_only`
- behavior change is explicitly supported by reviewed truth
- pickup brief states no unresolved anti-overclaim blocker for the tested seam

Meaning:
- the team may broaden to the next fixture in the same seam
- or wire the already-proven seam into the next thin consumer/UI surface

### 5.2 `tighten_same_seam`
Use when:
- parity is mostly sound
- no dangerous trust inflation occurred
- but behavior proof is still weak, ambiguous, or only `shown_only`
- or one scoreboard remains `partial` on a non-dangerous axis

Meaning:
- do not broaden scope yet
- tighten projection, fixture strength, or behavior proof on the same seam
- the next move should still be the smallest honest proof step

### 5.3 `fix_drift_before_expand`
Use when any of these are true:
- parity scoreboard fails a dangerous axis
- trust-preservation is `fail`
- copyability, placement, tone, promotion, readiness, provenance, or anti-overclaim drift occurs
- behavior change exceeds judged trust posture
- rebuild or observability implies stronger certainty than the shared decision seam allows

Meaning:
- stop expansion
- run the drift triage playbook immediately
- the next move is bug localization, not more surface area

## 6. Required joint reading order

After the runbook review order is complete, judge the scoreboards in this order:
1. parity scoreboard dangerous axes
2. parity scoreboard downgrade notes
3. reuse behavior class
4. reuse trust-preservation result
5. pickup brief anti-overclaim language
6. final combined verdict

This order matters.
A strong behavior change never overrides a dangerous parity failure.
A clean parity pass is also not enough if the behavior proof is still just “memory was shown.”

## 7. Dangerous-axis override rule

The following always override any otherwise-positive signal and force `fix_drift_before_expand`:
- promotion drift
- tone drift with stronger implied confidence
- placement drift into top-line or copyable worker sections
- copyability drift
- anti-overclaim loss
- readiness inflation
- provenance loss that blocks auditability
- rebuild depending on transcript archaeology when the seam claimed rebuild readiness
- observability trust inflation

No “but the summary looks right” exception.

## 8. Behavior-proof floor

A proof block should not be treated as seam-complete if behavior change is only:
- `shown_only`

That state can still be valuable, but it only earns:
- `tighten_same_seam`

The first real flywheel proof needs one of:
- `routing_changed`
- `instruction_changed`
- `evidence_guidance_changed`
- `redispatch_changed`
- `escalation_changed`

And that change must be explicitly supported by the reviewed city judgment.

## 9. Downgrade interpretation rule

Explicit downgrades are allowed.
Hidden downgrades are not.

Interpretation:
- explicit downgrade with no trust inflation may still allow `ship_same_seam` if the downgraded consumer is not on a dangerous axis and the overall proof remains strong
- repeated or expanding downgrade patterns should push the verdict to `tighten_same_seam`
- silent downgrades force `fix_drift_before_expand`

## 10. Pickup-brief carry-forward rule

The final combined verdict must be echoed into the pickup brief so the next daytime block inherits:
- what was proven
- what is still partial
- what must not be claimed yet
- the next smallest proof

Recommended fields to carry forward:
- `combined_verdict`
- `dangerous_axes_failed[]`
- `supported_behavior_change_reason[]`
- `do_not_claim_yet[]`
- `next_smallest_proof[]`

If the pickup brief cannot state those clearly, the proof block is not packaged tightly enough for handoff.

## 11. Recommended scoreboard-to-action table

| Parity result | Behavior result | Trust preservation | Combined verdict | Next action |
|---|---|---|---|---|
| pass | stronger than `shown_only` | pass | `ship_same_seam` | broaden to next fixture or next thin consumer |
| pass | `shown_only` | pass | `tighten_same_seam` | strengthen behavior proof on same seam |
| partial | stronger than `shown_only` | pass | `tighten_same_seam` | remove downgrade/partial gap before expanding |
| fail on dangerous axis | any | any | `fix_drift_before_expand` | run drift triage and fix root cause |
| pass/partial | stronger than `shown_only` | partial/fail | `fix_drift_before_expand` | fix trust-preservation bug first |

## 12. How this changes daytime review behavior

This protocol should make one practical change:

**stop treating scoreboards as decorative receipts.**

Instead:
- parity scoreboard decides whether semantics held
- reuse scoreboard decides whether behavior improved honestly
- this protocol decides whether the seam can expand

That closes the last daylight loophole where a proof block can look polished while still being operationally weak or semantically unsafe.

## 13. Sharp recommendation

**End every daytime proof block with one combined verdict, not two unrelated scoreboard readings.**

That is the cleanest way to keep City as a Service honest while the first decision flywheel is still being built.
