# City as a Service — Typed Validators and Fixture Schema

> Last updated: 2026-04-27
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> - `CITY_AS_A_SERVICE_DAYTIME_BUILD_SPEC.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The CaaS planning stack already says that daytime should start with typed validators and a tiny replay fixture pack.
What is still too easy to leave fuzzy is **what exactly needs validation first and what a replay fixture must contain to test the learning seam without dragging in the whole product**.

This doc narrows that seam.
It defines:
- the minimum object shapes that deserve first-class validators
- validator behavior expectations
- the smallest fixture schema that can prove replay-driven learning
- the first failure modes daytime should catch before UI work grows around them

## 2. Core principle

**If the reviewed-result loop cannot be validated deterministically, the city-ops memory layer will become doctrine by accident.**

Typed validation is not just a cleanup step.
It is the guardrail that keeps:
- ambiguous reviewed results from entering memory
- noisy playbook deltas from looking authoritative
- dispatch briefs from becoming opinionated without provenance

## 3. The first validator set

Daytime should create explicit validators for five artifact types only.
That is enough to prove the loop.

### 3.1 `reviewed_result`
Purpose:
- normalize what happened in one reviewed city task
- provide the shared truth surface for operator UI and projector logic

Must validate:
- required shared fields exist
- enums are constrained
- template-specific `structured_result` shape matches `workflow_template`
- `redirect_target` only appears when routing changed or was clarified
- `rejection_reasons[]` are present when `outcome_status = rejected`
- `confidence_score` is required for `heard`, `mixed`, or `inconclusive` outcomes

### 3.2 `review_artifact`
Purpose:
- capture the operator decision about trust, closure, and memory promotion

Must validate:
- review status is explicit, not inferred
- trust level and closure type are present
- follow-on recommendation is representable without freeform-only logic
- memory-write recommendation is boolean and inspectable
- operator notes remain optional, compact, and non-authoritative compared with structured fields

### 3.3 `reviewed_episode`
Purpose:
- convert one reviewed city task into a replayable memory event

Must validate:
- episode identity and source task linkage
- office/jurisdiction/template context
- compact normalized summary of outcome
- stable learning signals list
- provenance back to `reviewed_result` and `review_artifact`

### 3.4 `office_playbook_delta`
Purpose:
- represent one defensible change to office memory

Must validate:
- delta category is explicit (`rejection_pattern`, `redirect_pattern`, `evidence_restriction`, `access_friction`, `office_scope_correction`, etc.)
- claim is attributable to one or more reviewed episodes
- confidence/freshness exists
- merge behavior is deterministic and does not require LLM interpretation

### 3.5 `dispatch_brief`
Purpose:
- provide compact operational guidance before the next city dispatch

Must validate:
- office summary is present when office context exists
- top risks and fallback guidance are structured
- known rejection reasons and redirect targets are compact, not transcript dumps
- provenance references exist for major claims
- stale or low-confidence claims are marked as such instead of appearing authoritative

## 4. Suggested validation strategy

The first pass does not need a giant framework.
Use any typed/schema approach already natural to the repo, but preserve three behaviors.

### 4.1 Parse-time strictness
- reject unknown enum values
- reject missing required fields
- reject template/result mismatches
- reject invalid replay fixtures early

### 4.2 Deterministic normalization
- sort repeated reason lists if order is not semantically meaningful
- coerce timestamps into one canonical format
- keep optional empty collections consistent
- avoid validator logic that mutates meaning across runs

### 4.3 Explainable failures
Validation errors should help daytime see exactly what is wrong.
Bad example:
- `invalid payload`

Good example:
- `packet_submission reviewed_result missing rejection_reasons for outcome_status=rejected`
- `dispatch_brief claim references unknown reviewed_episode_id`

## 5. Minimum fixture schema

A first replay fixture should be small enough to inspect by eye.
It does not need the whole task system.

```json
{
  "fixture_id": "packet_rejection_outdated_form_v1",
  "task_envelope": {},
  "raw_submission_summary": {},
  "reviewed_result": {},
  "review_artifact": {},
  "expected_outputs": {
    "reviewed_episode": {},
    "office_playbook_delta": {},
    "dispatch_brief_changes": {}
  },
  "expected_events": []
}
```

## 6. Required fixture sections

### 6.1 `fixture_id`
Must be stable, human-readable, and scenario-specific.

### 6.2 `task_envelope`
Should include only the canonical city-task context needed for replay:
- template
- jurisdiction
- office
- required outcome
- time sensitivity if relevant

### 6.3 `raw_submission_summary`
Should preserve only the input facts necessary to justify the reviewed result:
- worker-reported answer/outcome
- proof summary
- notable ambiguity
- routing or evidence constraints

This is not a full attachment dump.
It is the replay seed.

### 6.4 `reviewed_result`
Must already reflect the operator-normalized truth that the projector consumes.

### 6.5 `review_artifact`
Must represent the operator trust/closure decision that allows or blocks learning.

### 6.6 `expected_outputs.reviewed_episode`
Must assert the compact replayable memory artifact that should be produced.

### 6.7 `expected_outputs.office_playbook_delta`
May be null when no durable learning should be promoted.
If present, it must represent one clear office-memory change.

### 6.8 `expected_outputs.dispatch_brief_changes`
Should describe what becomes better for the next dispatch, for example:
- new warning about outdated form version
- new redirect to Window B
- new evidence caution about no-photo counter policy

### 6.9 `expected_events`
Should list the stable event sequence expected from replay.

## 7. First fixture families

The first pack should mirror the replay plan and no more.

### Family A — clean baseline
Proves the contracts work without strong learning pressure.

### Family B — rejection learning
Proves one reviewed rejection changes the next dispatch brief.

### Family C — repeated rejection strengthening
Proves repeated failure reinforces one memory claim instead of duplicating noise.

### Family D — redirect learning
Proves reroute intelligence appears before the next dispatch.

### Family E — evidence restriction
Proves proof expectations can change without corrupting routing guidance.

### Family F — blocked-access realism
Proves office access friction becomes actionable guidance, not just postmortem text.

## 8. Failure modes validators should catch immediately

### 8.1 Contract drift
Example:
- `workflow_template = counter_question` with packet-submission-only fields in `structured_result`

### 8.2 False certainty
Example:
- heard-only result without confidence
- ambiguous redirect written as definite office doctrine

### 8.3 Memory pollution
Example:
- raw worker speculation turned into playbook guidance without reviewed approval
- duplicate rejection facts stored as separate top-level rules

### 8.4 Provenance loss
Example:
- dispatch brief contains a routing warning but cannot point to any reviewed episode

### 8.5 Non-deterministic merges
Example:
- replaying the same repeated rejection changes ranking or wording unpredictably

## 9. Strong recommendation for daytime build order

If the team only has a few focused hours, do this in order:
1. define the five validator shapes
2. create 5-10 tiny JSON fixtures matching those shapes
3. write deterministic replay assertions
4. prove that one rejection and one redirect improve the next dispatch brief
5. only then wire review/brief UI onto those validated artifacts

## 10. What success looks like

This seam is ready when daytime can say:
- every reviewed city fixture either validates cleanly or fails with precise reasons
- replay produces stable `reviewed_episode`, `office_playbook_delta`, and `dispatch_brief` artifacts
- repeated municipal learning strengthens guidance instead of multiplying noise
- the next dispatch brief is visibly smarter than the empty-state brief

That is the smallest proof that CaaS is becoming a real operational memory system instead of a pile of city-task notes.
