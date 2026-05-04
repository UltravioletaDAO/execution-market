# City as a Service — Daytime Telemetry-Gate Review Protocol

> Last updated: 2026-05-04
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_DAYTIME_REPLAY_PROOF_RUNBOOK.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_REVIEW_CARD.md`
> Status: proof-block packaging review protocol

## 1. Why this doc exists

The planning stack now already defines:
- how a proof block runs
- how parity and reuse are judged
- how one combined verdict is chosen
- which compact telemetry fields must survive the block

What is still easy to lose in daylight is the **review discipline for the telemetry gate itself**.
A team can still:
- emit a correct combined verdict
- write a telemetry row
- carry some of it into pickup
- but fail to check whether the row actually preserves the same closure truth across pickup, observability, rebuild, and later export readiness

This doc closes that last packaging seam.

> every daytime proof block that emits a telemetry gate row should also be reviewed through one compact protocol before the seam is treated as handoff-ready.

## 2. The single review question

For one replay-backed city proof block:

> does the telemetry gate row preserve the exact closure truth of the scoreboards strongly enough that the next session can trust it without reopening the whole bundle?

If the answer is no, the proof block is still under-packaged even if the scoreboards were correct.

## 3. Inputs required for telemetry-gate review

Review the telemetry gate only after these already exist:
- `bundle_manifest.json`
- `event_summary.json`
- `review_packet.json`
- `city_compact_decision_object.json`
- `morning_pickup_brief.json`
- `city_shared_decision_parity_scoreboard.json`
- `city_reuse_behavior_scoreboard.json` when reuse is in scope
- one emitted telemetry gate row or deterministic equivalent

If the telemetry row exists before those artifacts are stable, treat it as provisional only.

## 4. Mandatory review order

Review in this order only:
1. combined verdict from the scoreboard protocol
2. dangerous-axis failures (or confirmed empty list)
3. behavior-change class
4. trust-preservation result
5. portability fields
6. anti-overclaim carry-forward fields
7. pickup-brief carry-forward wording
8. final telemetry row completeness

This order matters.
A row that looks structurally complete still fails review if it weakens dangerous-axis reporting or overstates portability.

## 5. What must match exactly

The telemetry gate review should verify exact agreement on these fields:
- `combined_verdict`
- `behavior_change_class`
- `trust_preservation_result`
- `dangerous_axes_failed[]`
- `supported_behavior_change_reason[]`
- `do_not_claim_yet[]`
- `next_smallest_proof[]`

These are closure truths, not convenience summaries.
If any are softened, strengthened, or omitted without explicit downgrade handling, the row fails review.

## 6. What may be summarized but not reinterpreted

These fields may be compacted for pickup or observability formatting, but not semantically changed:
- `explicit_downgrade_count`
- `coordination_trace_complete`
- `session_rebuild_ready`
- `acontext_sink_ready`
- `cross_project_event_reusable`

Allowed:
- compact wording
- grouped display
- deterministic aliases

Not allowed:
- inferring readiness from adjacent artifacts
- promoting partial readiness to ready-for-use language
- hiding downgrade count because the rest of the row looks good

## 7. Telemetry-gate pass / partial / fail rules

### 7.1 Pass
Use only when all are true:
- telemetry row matches the scoreboard verdict exactly
- dangerous-axis list is explicit and accurate
- portability fields match real artifact support
- pickup brief preserves the same anti-overclaim posture
- the next session could choose the next move from the telemetry row plus pickup brief without reopening the full replay archive

### 7.2 Partial
Use when:
- core verdict fields are correct
- no dangerous truth was inflated
- but portability or carry-forward packaging is still incomplete or too vague

Examples:
- verdict correct, but `acontext_sink_ready` omitted
- behavior class correct, but `supported_behavior_change_reason[]` too thin for later review
- pickup brief says “tighten seam” without carrying the exact claim limits

### 7.3 Fail
Use when any are true:
- telemetry verdict disagrees with the scoreboard protocol
- dangerous drift happened but the row reports none
- portability fields overstate rebuild/export/reuse readiness
- pickup brief claims more than `do_not_claim_yet[]` allows
- anti-overclaim warnings disappear from the compact closure package

## 8. Dangerous packaging failures

Any of these should force telemetry-gate review failure:
- `ship_same_seam` recorded when scoreboards only supported `tighten_same_seam`
- `shown_only` compressed into wording that implies meaningful dispatch improvement
- `trust_preservation_result=partial|fail` hidden behind positive prose
- `dangerous_axes_failed[]` dropped because “the main path passed”
- `session_rebuild_ready=true` or `acontext_sink_ready=true` without matching proof artifacts
- `do_not_claim_yet[]` removed from pickup continuity even though the telemetry row retained it

These are not wording issues.
They are handoff-trust failures.

## 9. Recommended compact reviewer checklist

A reviewer should be able to answer yes to all of these:
- does the telemetry row say the same verdict as the scoreboards?
- does it preserve whether behavior really changed or was only shown?
- does it keep dangerous-axis failures explicit?
- does it preserve exact claim limits for the next session?
- does it state readiness fields conservatively?
- does the pickup brief carry the same closure truth forward?

If any answer is no, the row is not ready to anchor continuity.

## 10. How this changes daytime review behavior

This protocol makes one practical change:

**do not treat the telemetry gate row as a logging afterthought.**

Instead, treat it as the compact closure artifact that determines whether:
- the next session can trust the verdict
- observability can query the seam honestly
- rebuild/export planning inherit the right caution
- the proof block is actually packaged, not merely reviewed

## 11. Sharp recommendation

**End every daytime proof block with two closure checks, not one:**
1. combined scoreboard verdict is honest
2. telemetry gate row preserves that honesty for handoff

That is the cleanest way to keep the City-as-a-Service proof seam durable across day/night continuity.
