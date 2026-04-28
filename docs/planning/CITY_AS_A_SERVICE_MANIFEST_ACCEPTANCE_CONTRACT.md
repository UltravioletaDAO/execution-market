# City as a Service — Manifest Acceptance Contract

> Last updated: 2026-04-28
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_REPLAY_BUNDLE_SPEC.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> - `CITY_AS_A_SERVICE_BRIEF_IMPROVEMENT_SCORECARD.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The replay bundle spec already defines which artifacts should exist.
What still needs to be locked down is the exact acceptance contract for the one file that should summarize whether a replay actually proved anything.

This doc defines that contract for `bundle_manifest`.

The goal is simple:

> make one manifest file sufficient to judge whether a replay bundle is a real City-as-a-Service learning proof.

## 2. Core principle

**The manifest is not just an index. It is the first proof object.**

A reviewer should be able to open the manifest first and answer:
- did the replay run complete?
- did the contracts validate?
- did the system produce a meaningful office-memory change?
- did the next dispatch brief get better for an operational reason?
- can the important claims be traced back to reviewed evidence?

If the manifest cannot answer those questions clearly, the proof contract is too weak.

## 3. Minimum manifest fields

The first implementation pass should require these top-level fields:
- `fixture_id`
- `workflow_template`
- `office_key`
- `bundle_version`
- `validator_version`
- `projector_version`
- `scorecard_version`
- `artifacts`
- `acceptance`
- `summary_judgment`

Optional but recommended:
- `generated_at`
- `reviewed_episode_ids`
- `playbook_revision`
- `notes`

## 4. Artifact presence contract

The `artifacts` object should record whether each required output is:
- `present`
- `not_emitted`
- `not_applicable`
- `failed_validation`

Required keys:
- `baseline_dispatch_brief`
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `office_playbook_delta`
- `office_playbook_after`
- `improved_dispatch_brief`
- `brief_improvement_scorecard`
- `event_summary`

The manifest should never force a reviewer to guess whether a missing file was intentional or accidental.

## 5. Acceptance checks

The `acceptance` object should carry the smallest set of explicit pass/fail checks that make the proof auditable.

### 5.1 Required checks
- `contracts_valid`
- `projector_deterministic`
- `playbook_delta_meaningful`
- `brief_improvement_visible`
- `provenance_traceable`
- `events_in_expected_order`

### 5.2 Recommended check semantics

#### `contracts_valid`
True only if every required emitted artifact validates against its expected contract.

#### `projector_deterministic`
True only if rerunning the same fixture produces the same normalized artifacts and the same operational meaning.

#### `playbook_delta_meaningful`
True only if the replay changed office memory for an operational reason, not just formatting or metadata drift.

#### `brief_improvement_visible`
True only if the scorecard marks at least one operational dimension as `improved` and the rationale is inspectable.

#### `provenance_traceable`
True only if important brief claims can be linked back to reviewed episodes or explicit playbook deltas.

#### `events_in_expected_order`
True only if the compact event summary preserves the expected lifecycle ordering for the replay.

## 6. Summary judgment contract

The manifest should end with one of three summary judgments:
- `pass`
- `partial`
- `fail`

### 6.1 `pass`
Use when:
- all required acceptance checks pass
- all required artifacts are present or explicitly marked not applicable
- the scorecard shows real operational improvement or a justified no-change baseline case

### 6.2 `partial`
Use when:
- the replay completed and emitted a reviewable artifact set
- but one important proof bar failed, such as visible brief improvement or provenance clarity

This matters because a partial run can still be useful for daytime debugging and contract tuning.

### 6.3 `fail`
Use when:
- contracts are broken
- determinism fails
- the event sequence is unstable
- key artifacts are missing without explanation
- the run does not support inspection at all

## 7. Recommended first-pass manifest shape

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

## 8. Review discipline recommendation

The first daytime PR should treat the manifest as the headline artifact.
A reviewer should start there, then inspect:
1. `brief_improvement_scorecard`
2. `improved_dispatch_brief`
3. `office_playbook_delta`
4. `reviewed_episode`

That reading order keeps the first proof focused on whether learning became operationally useful.

## 9. Sharp recommendation

**Build the first replay proof so the manifest can serve as a deploy-gate-friendly receipt for learning.**

If the manifest cannot make replay success or failure obvious, the City-as-a-Service seam is still too vague for broader UI or infrastructure expansion.
