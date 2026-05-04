# City as a Service — Daytime Proof-Block Telemetry Gate

> Last updated: 2026-05-04
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_REPLAY_PROOF_RUNBOOK.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`
> - `CITY_AS_A_SERVICE_COMPACT_DECISION_OBJECT_AND_COORDINATION_LEDGER_SLICE.md`
> Status: daytime proof/measurement closure gate

## 1. Why this doc exists

The planning stack now has a strong execution loop:
- one replay-proof runbook
- one shared decision seam
- one parity scoreboard
- one behavior scoreboard
- one combined verdict protocol

But one daylight risk still remains:
- run a proof block
- classify it correctly in review
- yet fail to emit the telemetry fields that would let later sessions prove the seam stayed honest in runtime conditions

That leaves daytime with a polished proof receipt and weak operational memory.
This doc closes that gap.

> every proof block that claims progress should also emit one compact telemetry gate row proving the same judged truth is queryable across replay, continuity, observability, and next-session pickup.

## 2. The single question

For one replay-backed city case:

> did we emit enough compact telemetry to prove not only what the verdict was, but why it was safe, how behavior changed, and whether the same seam is restart-safe and export-ready?

If the answer is no, the proof block is still under-instrumented even if the review looked clean.

## 3. Required telemetry gate outputs

Every proof block should end with one compact telemetry package containing:
- `coordination_session_id`
- `review_packet_id`
- `compact_decision_id`
- `combined_verdict`
- `behavior_change_class`
- `trust_preservation_result`
- `dangerous_axes_failed[]`
- `explicit_downgrade_count`
- `coordination_trace_complete`
- `session_rebuild_ready`
- `acontext_sink_ready`
- `cross_project_event_reusable`
- `supported_behavior_change_reason[]`
- `do_not_claim_yet[]`
- `next_smallest_proof[]`

This package may live as:
- one JSON row in a proof-block scoreboard ledger
- one deterministic extension of the pickup brief
- one observability row emitted beside the parity/reuse scoreboards

The exact file path can vary.
The field contract should not.

## 4. Why these fields are the minimum honest set

### 4.1 Identity and join fields
These make the proof queryable later instead of becoming another isolated artifact:
- `coordination_session_id`
- `review_packet_id`
- `compact_decision_id`

### 4.2 Judgment fields
These preserve the real decision, not just raw pass/fail summaries:
- `combined_verdict`
- `behavior_change_class`
- `trust_preservation_result`
- `dangerous_axes_failed[]`
- `explicit_downgrade_count`

### 4.3 Portability fields
These prove whether the seam can survive beyond replay review:
- `coordination_trace_complete`
- `session_rebuild_ready`
- `acontext_sink_ready`
- `cross_project_event_reusable`

### 4.4 Anti-overclaim carry-forward fields
These protect the next session from inheriting fake certainty:
- `supported_behavior_change_reason[]`
- `do_not_claim_yet[]`
- `next_smallest_proof[]`

## 5. Required emission moment in the runbook

Add this gate after scoreboards are judged and before the proof block is considered packaged.

Canonical order becomes:
1. choose case
2. emit proof archive
3. emit shared decision seam
4. emit proof receipts
5. review in strict order
6. classify pass / partial / fail
7. apply combined scoreboard verdict
8. emit telemetry gate row
9. carry the same gate fields into pickup continuity
10. choose next smallest honest move

If step 8 is skipped, the block is not fully closed.

## 6. Telemetry gate acceptance rules

A proof block telemetry package passes only when:
- all join fields are present
- combined verdict exactly matches the scoreboard protocol result
- behavior class is explicit, never implied from prose
- dangerous-axis failures are listed explicitly or confirmed empty
- rebuild/export/portability fields reflect real artifact readiness, not optimism
- anti-overclaim carry-forward fields match pickup brief wording

A telemetry package is partial when:
- verdict exists but portability fields are missing
- behavior class exists but justification is vague
- downgrade count is missing while downgrade notes exist elsewhere

A telemetry package fails when:
- verdict in telemetry disagrees with scoreboards
- dangerous drift happened but no dangerous axis was recorded
- rebuild or Acontext readiness is marked true without matching artifact support
- pickup brief claims more than the telemetry gate allows

## 7. Recommended compact row shape

```json
{
  "proof_block_version": "v1",
  "coordination_session_id": "city_packet_submission_2026_05_04_001",
  "review_packet_id": "rp_2026_05_04_001",
  "compact_decision_id": "cdo_2026_05_04_001",
  "combined_verdict": "tighten_same_seam",
  "behavior_change_class": "shown_only",
  "trust_preservation_result": "pass",
  "dangerous_axes_failed": [],
  "explicit_downgrade_count": 1,
  "coordination_trace_complete": true,
  "session_rebuild_ready": true,
  "acontext_sink_ready": false,
  "cross_project_event_reusable": true,
  "supported_behavior_change_reason": [
    "redirect guidance was preserved with verify-first posture"
  ],
  "do_not_claim_yet": [
    "next dispatch is smarter beyond shown-only evidence"
  ],
  "next_smallest_proof": [
    "upgrade one redirect case from shown_only to routing_changed without trust drift"
  ]
}
```

## 8. How this strengthens the broader system themes

This gate is the smallest planning addition that directly ties together tonight’s focus areas:

### 8.1 Memory ↔ Acontext integration planning
The gate makes export readiness explicit instead of assuming replay correctness implies sink readiness.

### 8.2 IRC/session management enhancement
The gate makes `coordination_session_id` and rebuild readiness mandatory proof-block outputs.

### 8.3 Cross-project decision support systems
The gate forces one explicit `cross_project_event_reusable` judgment so the event seam is evaluated as infrastructure, not just local success.

### 8.4 Agent observability and success metrics
The gate turns review outcomes into one compact queryable row that can survive night/day handoffs and support later success dashboards.

## 9. Required doc-threading changes

Any daytime seam that claims proof completeness should reference this gate alongside:
- the replay proof runbook
- the combined scoreboard protocol
- the pickup brief continuity contract
- observability scorecard/reporting docs

This keeps proof closure, continuity, and telemetry from drifting into separate interpretations.

## 10. Sharp recommendation

**Do not let a proof block end at “scoreboards look good.”**

Make it emit one compact telemetry gate row that says:
- what was proven
- what changed
- what remained unsafe to claim
- whether the seam is rebuild-safe, export-safe, and reusable beyond the immediate replay window

That is the missing step between a strong review artifact and a durable operational learning loop.
