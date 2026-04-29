# City as a Service — Replay Bundle Spec

> Last updated: 2026-04-28
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_BUILD_SPEC.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> - `CITY_AS_A_SERVICE_BRIEF_IMPROVEMENT_SCORECARD.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The planning stack now says the first daylight proof should end in a compact before/after artifact bundle, not just passing validators or passing replay code.

What is still too easy to leave fuzzy is the exact bundle shape.
If builders produce the artifacts in different layouts every time, the first proof becomes harder to inspect, compare, review, and trust.

This doc defines the smallest standard replay bundle for the first City-as-a-Service learning proof.

The goal is simple:

> one fixture replay should produce one self-explaining bundle that shows whether reviewed city work made the next dispatch better.

## 2. Core principle

**A replay bundle is successful only if a human can inspect it quickly and understand the learning without reading product code.**

The bundle should optimize for:
- legibility
- deterministic structure
- provenance visibility
- before/after comparison
- replay repeatability

It should not optimize for:
- verbose transcript dumps
- unstructured logs
- hidden scoring logic
- UI polish before proof exists

## 3. Required bundle outputs

Each replay bundle should contain exactly these top-level artifacts:

1. `baseline_dispatch_brief`
2. `reviewed_result`
3. `review_artifact`
4. `reviewed_episode`
5. `office_playbook_delta`
6. `office_playbook_after`
7. `improved_dispatch_brief`
8. `brief_improvement_scorecard`
9. `event_summary`
10. `bundle_manifest`
11. `review_packet`

If one of these does not apply, the bundle should still include a placeholder object with a clear reason such as:
- `not_emitted`
- `no_meaningful_learning`
- `not_applicable_for_fixture`

That keeps inspection deterministic.

## 4. What each artifact must answer

### 4.1 `baseline_dispatch_brief`
Must answer:
- what would the operator/worker have seen before this reviewed learning existed?

### 4.2 `reviewed_result`
Must answer:
- what normalized municipal outcome was accepted as reviewed truth?

### 4.3 `review_artifact`
Must answer:
- why was this result trusted, what closure type happened, and should memory promotion occur?

### 4.4 `reviewed_episode`
Must answer:
- what operationally meaningful thing happened that future dispatch should remember?

### 4.5 `office_playbook_delta`
Must answer:
- what changed in office memory because of this episode?

### 4.6 `office_playbook_after`
Must answer:
- what is the merged current office guidance after applying the new delta?

### 4.7 `improved_dispatch_brief`
Must answer:
- what would the next dispatch see now that the reviewed learning exists?

### 4.8 `brief_improvement_scorecard`
Must answer:
- did the brief get better, on which dimensions, and why?

### 4.9 `event_summary`
Must answer:
- what stable replay/review events happened, in what order, and which artifacts did they correspond to?

### 4.10 `bundle_manifest`
Must answer:
- which fixture produced this bundle, which validator or schema versions were used, and whether the bundle passed all replay gates?

### 4.11 `review_packet`
Must answer:
- what the replay means operationally after manifest and scorecard judgment, and how strongly the learned guidance is allowed to influence future dispatch?

## 5. Recommended directory layout

A replay bundle should be written in a deterministic folder layout like this:

```text
city_ops_replay_runs/
  <fixture_id>/
    bundle_manifest.json
    baseline_dispatch_brief.json
    reviewed_result.json
    review_artifact.json
    reviewed_episode.json
    office_playbook_delta.json
    office_playbook_after.json
    improved_dispatch_brief.json
    brief_improvement_scorecard.json
    event_summary.json
    review_packet.json
```

If a markdown summary is useful, it can be added as:
- `README.md`

But JSON artifacts should remain canonical.

## 6. Bundle manifest contract

The manifest should be the first file a reviewer opens.
It should make bundle status obvious.

Recommended shape:

```json
{
  "fixture_id": "packet_rejection_outdated_form_v1",
  "workflow_template": "packet_submission",
  "office_key": "miami_building_dept_counter_a",
  "bundle_version": "v1",
  "validator_version": "v1",
  "projector_version": "v1",
  "scorecard_version": "v1",
  "artifacts": {
    "baseline_dispatch_brief": "present",
    "reviewed_result": "present",
    "review_artifact": "present",
    "reviewed_episode": "present",
    "office_playbook_delta": "present",
    "office_playbook_after": "present",
    "improved_dispatch_brief": "present",
    "brief_improvement_scorecard": "present",
    "event_summary": "present"
  },
  "acceptance": {
    "contracts_valid": true,
    "projector_deterministic": true,
    "playbook_delta_meaningful": true,
    "brief_improvement_visible": true,
    "provenance_traceable": true,
    "events_in_expected_order": true
  },
  "summary_judgment": "pass"
}
```

## 7. Event summary contract

The event summary should stay compact.
It is not a raw event firehose.

Recommended shape:

```json
{
  "fixture_id": "packet_rejection_outdated_form_v1",
  "events": [
    {
      "name": "city_review_completed",
      "sequence": 1,
      "artifact_refs": ["reviewed_result", "review_artifact"]
    },
    {
      "name": "city_reviewed_episode_written",
      "sequence": 2,
      "artifact_refs": ["reviewed_episode"]
    },
    {
      "name": "city_office_playbook_delta_written",
      "sequence": 3,
      "artifact_refs": ["office_playbook_delta", "office_playbook_after"]
    },
    {
      "name": "city_dispatch_brief_composed",
      "sequence": 4,
      "artifact_refs": ["improved_dispatch_brief"]
    }
  ]
}
```

## 8. Review packet requirements inside the bundle

The bundle should include one compact `review_packet` after manifest and scorecard evaluation.
That packet should:
- mirror the manifest `summary_judgment`
- carry `learning_strength`
- make `memory_promotion_decision` explicit
- point back to the canonical proof artifacts
- stay short enough for downstream retrieval or Acontext ingestion without rereading the full archive

## 9. Improvement scorecard requirements inside the bundle

The scorecard should use the five dimensions already established elsewhere:
- routing clarity
- rejection avoidance
- fallback usefulness
- evidence realism
- provenance clarity

The bundle should not pass if the scorecard is omitted.
A before/after brief pair without explicit grading is still too easy to argue by vibe.

## 10. Pass/fail rule for the first daylight proof

A replay bundle should count as a successful proof only if all of the following are true:
- all required artifacts are present or explicitly marked not applicable
- contracts validate
- the event order is stable
- the office playbook change is inspectable
- the improved dispatch brief differs for an operational reason, not only formatting
- the scorecard marks at least one meaningful dimension as `improved`
- provenance for the improved guidance is visible

If the bundle only shows different wording with no operational improvement, the proof should fail.

## 11. Recommended first fixture sequence for bundle generation

The first daylight implementation should generate bundles for at least:
1. one rejection fixture
2. one repeated rejection fixture
3. one redirect fixture

Why this order:
- rejection proves failure-memory capture
- repeated rejection proves merge discipline
- redirect proves routing improvement

That is enough to show whether the city-ops memory seam is becoming genuinely useful.

## 12. Relationship between bundle, manifest, and packet

The bundle should now be read as three layers:
- the artifact set as the proof archive
- the manifest as the headline pass/partial/fail contract
- the review packet as the compact operational judgment and promotion-safety bridge

That distinction keeps the replay seam reviewable without forcing downstream consumers to infer memory policy from raw bundle files.

## 13. Sharp recommendation

**Treat the replay bundle as the operator-readable receipt for CaaS learning.**

If one reviewed city fixture cannot produce a compact, self-explaining bundle, the learning seam is still too vague for broader UI or infra expansion.
