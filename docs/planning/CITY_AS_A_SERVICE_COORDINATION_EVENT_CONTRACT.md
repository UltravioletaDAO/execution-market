# City as a Service — Coordination Event Contract

> Last updated: 2026-04-28
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_REPLAY_BUNDLE_SPEC.md`
> - `CITY_AS_A_SERVICE_MANIFEST_ACCEPTANCE_CONTRACT.md`
> - `CITY_AS_A_SERVICE_LEARNING_STRENGTH_CLASSIFICATION.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The planning stack now has a stronger artifact chain:
- validated replay inputs
- reviewed city outcome
- office-memory delta
- improved dispatch brief
- scorecard judgment
- manifest summary judgment
- learning-strength classification

What is still easy to leave fuzzy is the event seam between those artifacts.
If daytime code emits raw logs, inconsistent lifecycle names, or transcript-shaped noise, the first proof may be technically valid while still being operationally unreadable.

This doc defines the smallest event contract that keeps replay learning compact, ordered, and reviewable.

The goal is simple:

> each replay bundle should include one compact event story that explains what happened, in what order, and which artifacts prove it.

## 2. Core principle

**Coordination events are not transcripts. They are proof-oriented lifecycle markers.**

The first event seam should optimize for:
- deterministic ordering
- compactness
- artifact traceability
- reviewability
- safe future projection into Acontext or IRC summaries

It should not optimize for:
- verbose internal logs
- every micro-step
- unstable timestamps as the only ordering signal
- hidden meaning spread across multiple sinks

## 3. What the event contract must answer

A reviewer opening `event_summary.json` should be able to answer:
- what replay lifecycle stages completed?
- in what order did they complete?
- which artifacts were produced at each stage?
- where did learning become accepted, merged, and visible to the next dispatch?
- did the replay stop at a partial point or reach a full inspectable outcome?

If the event summary cannot answer those questions quickly, the proof seam is too noisy.

## 4. Required top-level shape

Recommended first-pass shape:

```json
{
  "fixture_id": "packet_rejection_outdated_form_v1",
  "workflow_template": "packet_submission",
  "office_key": "miami_building_dept_counter_a",
  "event_contract_version": "v1",
  "summary_status": "complete",
  "events": [
    {
      "sequence": 1,
      "name": "city_review_completed",
      "status": "succeeded",
      "artifact_refs": ["reviewed_result", "review_artifact"],
      "notes": ["review accepted rejection outcome as trusted truth"]
    }
  ]
}
```

Required top-level fields:
- `fixture_id`
- `workflow_template`
- `office_key`
- `event_contract_version`
- `summary_status`
- `events`

Optional but recommended:
- `generated_at`
- `run_id`
- `notes`

## 5. Summary status values

Recommended values:
- `complete`
- `partial`
- `failed`

### 5.1 `complete`
Use when the replay emitted the expected compact lifecycle through improved brief, scorecard, and manifest-ready summary.

### 5.2 `partial`
Use when replay produced a reviewable subset of events, but stopped before the full learning chain completed.

### 5.3 `failed`
Use when the replay did not produce a reliable event story suitable for inspection.

## 6. Event object contract

Each event in `events` should include:
- `sequence`
- `name`
- `status`
- `artifact_refs`

Optional but recommended:
- `from_event`
- `notes`
- `derived_claims`

### 6.1 `sequence`
A small integer expressing stable logical order.
Use explicit sequence values rather than relying on timestamps for ordering.

### 6.2 `name`
A stable lifecycle label.
The first pass should prefer a tiny controlled vocabulary.

### 6.3 `status`
Recommended values:
- `succeeded`
- `skipped`
- `failed`

### 6.4 `artifact_refs`
References to bundle artifacts that prove the event happened.
These should point to canonical artifact names, not arbitrary file paths.

### 6.5 `from_event`
Optional pointer to the immediately preceding event that this event logically depends on.
Useful for partial runs and later graph expansion, but not required for the first pass.

### 6.6 `notes`
Short human-readable bullets only.
Do not dump transcripts here.

### 6.7 `derived_claims`
Optional short list of operational claims this event introduced, such as:
- `outdated_form_rejection_confirmed`
- `counter_b_redirect_rule_added`
- `receipt_photo_required_on_resubmission`

This is useful for future Acontext or observability sinks, but should stay compact.

## 7. Controlled first-pass event vocabulary

The first daylight implementation should stay narrow.
Recommended event names:

1. `city_review_completed`
2. `city_reviewed_episode_written`
3. `city_office_playbook_delta_written`
4. `city_office_playbook_merged`
5. `city_dispatch_brief_composed`
6. `city_brief_scorecard_computed`
7. `city_manifest_evaluated`
8. `city_learning_strength_classified`

This sequence matches the current proof chain closely enough to keep the seam legible.

## 8. Expected event ordering

The normal successful order should be:

1. `city_review_completed`
2. `city_reviewed_episode_written`
3. `city_office_playbook_delta_written`
4. `city_office_playbook_merged`
5. `city_dispatch_brief_composed`
6. `city_brief_scorecard_computed`
7. `city_manifest_evaluated`
8. `city_learning_strength_classified`

If one event is skipped because a fixture is not applicable, the event should still appear with:
- `status: "skipped"`
- a short note explaining why

That preserves deterministic inspection.

## 9. Relationship to the bundle artifacts

The event seam should make the artifact chain explicit.
Recommended mapping:

- `city_review_completed`
  - `reviewed_result`
  - `review_artifact`
- `city_reviewed_episode_written`
  - `reviewed_episode`
- `city_office_playbook_delta_written`
  - `office_playbook_delta`
- `city_office_playbook_merged`
  - `office_playbook_after`
- `city_dispatch_brief_composed`
  - `improved_dispatch_brief`
- `city_brief_scorecard_computed`
  - `brief_improvement_scorecard`
- `city_manifest_evaluated`
  - `bundle_manifest`
- `city_learning_strength_classified`
  - `bundle_manifest`

This keeps `event_summary` from becoming an isolated log blob.
It remains a compact index into the proof bundle.

## 10. Recommended first-pass example

```json
{
  "fixture_id": "packet_rejection_outdated_form_v1",
  "workflow_template": "packet_submission",
  "office_key": "miami_building_dept_counter_a",
  "event_contract_version": "v1",
  "summary_status": "complete",
  "events": [
    {
      "sequence": 1,
      "name": "city_review_completed",
      "status": "succeeded",
      "artifact_refs": ["reviewed_result", "review_artifact"],
      "notes": ["review accepted outdated form rejection as trusted municipal outcome"]
    },
    {
      "sequence": 2,
      "name": "city_reviewed_episode_written",
      "status": "succeeded",
      "artifact_refs": ["reviewed_episode"]
    },
    {
      "sequence": 3,
      "name": "city_office_playbook_delta_written",
      "status": "succeeded",
      "artifact_refs": ["office_playbook_delta"],
      "derived_claims": ["outdated_form_rejection_confirmed"]
    },
    {
      "sequence": 4,
      "name": "city_office_playbook_merged",
      "status": "succeeded",
      "artifact_refs": ["office_playbook_after"]
    },
    {
      "sequence": 5,
      "name": "city_dispatch_brief_composed",
      "status": "succeeded",
      "artifact_refs": ["improved_dispatch_brief"]
    },
    {
      "sequence": 6,
      "name": "city_brief_scorecard_computed",
      "status": "succeeded",
      "artifact_refs": ["brief_improvement_scorecard"]
    },
    {
      "sequence": 7,
      "name": "city_manifest_evaluated",
      "status": "succeeded",
      "artifact_refs": ["bundle_manifest"]
    },
    {
      "sequence": 8,
      "name": "city_learning_strength_classified",
      "status": "succeeded",
      "artifact_refs": ["bundle_manifest"],
      "notes": ["bundle judged pass with moderate reusable office learning"]
    }
  ]
}
```

## 11. Memory-safety rule

The event contract should preserve the distinction between:
- provisional field signal
- review-safe accepted truth
- reusable office memory

Do not let event names imply that raw observations are already durable truth.
That is why the first controlled vocabulary starts with `city_review_completed` and only later emits playbook and learning-strength events.

This distinction matters for future Acontext integration.
If the event seam collapses these states together, downstream systems will turn ambiguous municipal interaction into false certainty.

## 12. Review discipline recommendation

During the first daylight PR, reviewers should inspect in this order:
1. `bundle_manifest`
2. `event_summary`
3. `brief_improvement_scorecard`
4. `improved_dispatch_brief`
5. `office_playbook_delta`

That order keeps the replay proof focused on whether learning is visible, ordered, and operationally reusable.

## 13. Sharp recommendation

**Treat `event_summary` as the compact ordered receipt for the learning lifecycle, not as a debugging dump.**

If one replay bundle cannot emit a short ordered event story that maps directly to the artifact chain, the City-as-a-Service proof seam is still not ready for broader observability or coordination sinks.
