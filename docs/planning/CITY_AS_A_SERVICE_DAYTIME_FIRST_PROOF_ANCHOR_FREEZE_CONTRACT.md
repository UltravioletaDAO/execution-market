# City as a Service — Daytime First Proof Anchor Freeze Contract

> Last updated: 2026-05-05 22:35 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_CASE_SELECTION_CARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
> - `CITY_AS_A_SERVICE_DAYTIME_REPLAY_PROOF_RUNBOOK.md`
> - `CITY_AS_A_SERVICE_DECISION_PROJECTION_IMPLEMENTATION_SLICE.md`
> Status: daytime proof-anchor freeze artifact contract

## 1. Why this doc exists

The planning spine now says to choose one replay-backed redirect or rejection case before PR A and keep it stable through PR D.
That is the right rule, but it still leaves one daylight handoff risk:

> a case can be "chosen" in chat or reviewer memory without becoming a durable artifact that later PRs are forced to preserve.

This contract defines the tiny freeze artifact that should exist before the first shared-decision implementation starts.
It turns proof-anchor selection from a recommendation into a reviewable input.

## 2. The freeze question

Before PR A opens, reviewers should be able to inspect one file and answer:

> what exact replay-backed case is frozen, why was it selected, what behavior change is expected, and what may not drift while PR A through PR D advance?

If that file does not exist, PR A is starting with a hidden assumption.

## 3. Required artifact

Create one freeze note for the first ladder:

```text
artifacts/city_ops/proof_anchors/<anchor_id>/proof_anchor_freeze_note.json
```

If the implementation does not yet have an artifact directory, use the equivalent replay-bundle output path, but keep the filename stable.
The important part is not the exact folder; it is that the freeze note travels beside the replay case and is referenced by PR A, PR B, PR C, and PR D.

## 4. Minimal JSON shape

```json
{
  "schema": "city_ops.proof_anchor_freeze_note.v1",
  "anchor_id": "redirect_outdated_packet_001",
  "source_fixture": "fixtures/city_ops_review_cases/redirect_outdated_packet_001.json",
  "selected_at": "2026-05-05T22:35:00-04:00",
  "selected_for_ladder": "first_shared_decision_projection",
  "case_family": "redirect",
  "reviewed_outcome_class": "redirect_or_reject",
  "expected_behavior_change": {
    "class": "routing_or_evidence_guidance_change",
    "plain_language": "The next dispatch should route or instruct differently because reviewed municipal reality proved the old path was wrong or unsafe."
  },
  "compact_decision_expectations": {
    "promotion_class": "conservative_memory_delta",
    "guidance_tone": "cautionary_or_corrective",
    "guidance_placement": "operator_visible_before_worker_copy",
    "copyable_worker_instruction": "limited_by_reviewed_truth",
    "replay_readiness_judgment": "ready_for_projection_rung_only"
  },
  "dangerous_drift_axes": [
    "trust_inflation",
    "worker_copyability_overreach",
    "runtime_consumer_stronger_than_projection",
    "pickup_brief_optimism",
    "reuse_claim_without_behavior_change"
  ],
  "runner_up_rejected": {
    "source_fixture": "fixtures/city_ops_review_cases/example_runner_up.json",
    "reason": "Less useful for proving inspectable next-dispatch behavior change."
  },
  "freeze_invariants": [
    "same anchor_id across PR A through PR D",
    "same reviewed_outcome_class unless fixture is declared invalid",
    "same expected_behavior_change class across parity and reuse scoreboards",
    "same dangerous_drift_axes carried into telemetry and pickup packaging",
    "no consumer may claim stronger trust than the compact decision projection"
  ],
  "allowed_to_change": [
    "field names during PR A if schema review requires it",
    "artifact path if implementation chooses a different replay bundle root",
    "runner-up note if a better rejected candidate is discovered before PR A starts"
  ],
  "requires_reselection_if": [
    "fixture cannot produce a deterministic compact decision object",
    "expected behavior change is only cosmetic",
    "case requires transcript rereads to understand",
    "PR B or PR C needs a different case to demonstrate its checkpoint",
    "dangerous drift axes are too broad to localize"
  ]
}
```

## 5. Review rules

### 5.1 PR A may start only if

- `anchor_id` and `source_fixture` are stable
- expected behavior change is operational, not cosmetic
- dangerous drift axes are explicit
- compact decision expectations are conservative enough to implement without policy debate
- the rejected runner-up explains why this case is better for the first ladder

### 5.2 PR B may start only if

- the same freeze note is referenced by runtime parity fixtures
- runtime consumers are checked against the same drift axes
- any downgrade from the compact decision projection is explicit
- no consumer-specific strengthening appears outside the shared projection owner

### 5.3 PR C may start only if

- reuse behavior is tested against the same expected behavior-change class
- worker-copyability limits still match the freeze note
- `shown_only` is not upgraded unless the next dispatch actually changes for an inspectable reason

### 5.4 PR D may close only if

- parity scoreboard references the freeze note
- reuse behavior scoreboard references the freeze note
- telemetry gate carries the same dangerous drift axes
- pickup brief remains no more optimistic than the freeze note allows
- closure verdict is one of: `ship_same_seam`, `tighten_same_seam`, `fix_drift_before_expand`

## 6. Honest invalidation rule

The freeze note is not a prison.
It is a drift detector.

If the selected anchor proves invalid, daytime should stop and write a short invalidation note before selecting another case:

```json
{
  "schema": "city_ops.proof_anchor_invalidation_note.v1",
  "anchor_id": "redirect_outdated_packet_001",
  "invalidated_at": "2026-05-05T23:00:00-04:00",
  "failed_checkpoint": "PR_A_projection_truth",
  "reason": "The fixture required transcript rereads to understand the reviewed truth.",
  "next_action": "choose_new_anchor_before_implementation_continues"
}
```

Do not silently rotate anchors mid-ladder.
A silent anchor swap makes the proof block look stronger than it is.

## 7. Bottom line

The first shared-decision ladder should not begin with "we picked a case."
It should begin with a frozen, reviewable proof-anchor note.

That note is the contract that keeps PR A through PR D honest: one case, one expected behavior change, one set of drift axes, one closure chain.
