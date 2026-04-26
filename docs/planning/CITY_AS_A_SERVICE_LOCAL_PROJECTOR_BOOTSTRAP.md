# City as a Service — Local Projector Bootstrap

> Last updated: 2026-04-25
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_OPERATOR_PLAYBOOK.md`
> Status: implementation-oriented planning draft

## 1. Why this doc exists

The planning stack now defines:
- the city-ops templates
- the reviewed result contract
- the operator review model
- the memory bridge into Acontext

What daytime still needs is a **first build surface that can exist before Docker/Acontext wiring is ready**.

This document defines that surface.

The goal is to let Execution Market test the full learning loop locally first:
- reviewed result captured
- reviewed episode artifact emitted
- office/jurisdiction memory updated
- dispatch briefing composed for the next task

That should happen with local files and stable contracts before any heavy infra work.

## 2. Core principle

**Treat the local projector as the dress rehearsal for Acontext.**

If the file-based loop is clean, the later sink swap is an infrastructure task.
If the file-based loop is fuzzy, Acontext wiring will only hide product ambiguity.

## 3. What the bootstrap should produce

For each reviewed city task, the local projector should be able to write:
1. one reviewed result artifact
2. one reviewed episode artifact
3. zero or one office playbook delta
4. zero or one jurisdiction brief delta
5. one dispatch briefing input record

The first practical win is not a beautiful UI.
It is a clean artifact chain.

## 4. Proposed local directory layout

Suggested root inside the EM repo:

```text
docs/planning/examples/city_ops_memory/
  reviewed_results/
  reviewed_episodes/
  office_playbooks/
  jurisdiction_briefs/
  dispatch_briefs/
```

Recommended keying pattern:

```text
city_ops_memory/
  reviewed_results/{jurisdiction_slug}/{workflow_template}/{task_id}.json
  reviewed_episodes/{jurisdiction_slug}/{workflow_template}/{task_id}.json
  office_playbooks/{jurisdiction_slug}/{office_slug}.json
  jurisdiction_briefs/{jurisdiction_slug}.json
  dispatch_briefs/{jurisdiction_slug}/{workflow_template}/{office_slug}.json
```

This does not need to be final production layout.
It only needs to be stable enough for daytime implementation and test fixtures.

## 5. Minimal artifact set

### 5.1 Reviewed result artifact
This should mirror the reviewed result contract as closely as possible.
It is the canonical post-review payload for one task.

### 5.2 Reviewed episode artifact
This should be the reusable learning unit.
It should be compact enough to read at dispatch time and explicit enough to power future summarization.

### 5.3 Office playbook artifact
This should hold the current best-known office guidance for a specific office.
Initially this can be a single merged JSON file updated after reviewed episodes.

### 5.4 Jurisdiction brief artifact
This should summarize cross-office patterns for a metro/jurisdiction.
Early versions can stay extremely small.

### 5.5 Dispatch briefing artifact
This is the operator/agent-facing retrieval output.
It should be composed from the other artifacts rather than authored manually.

## 6. Bootstrap write rules

### 6.1 Always write after review
Never write durable memory artifacts directly from raw worker upload.
The projector should only run after:
- normalized reviewed result exists
- review decision exists
- next-step recommendation exists

### 6.2 Always write reviewed result + reviewed episode
Those two artifacts are the irreducible minimum.
Even if no office playbook changes, those two should still exist.

### 6.3 Write office playbook deltas only on meaningful learning
Examples:
- new redirect pattern
- repeated rejection reason
- evidence restriction discovered
- scope correction for office responsibility
- queue behavior worth remembering

### 6.4 Write jurisdiction deltas conservatively
Jurisdiction briefs should summarize repeated signals, not one noisy episode.
Start conservative.

## 7. Example projector pipeline

### Step 1 — input
Load:
- task envelope
- reviewed result
- review artifact

### Step 2 — emit reviewed episode
Map the reviewed result into the reviewed-episode contract.

### Step 3 — decide memory deltas
Check whether the episode contains:
- redirect learning
- rejection pattern learning
- office scope learning
- queue/policy/evidence learning

### Step 4 — update office playbook
Merge only the compact fields that changed.

### Step 5 — recompute dispatch brief
Generate a briefing artifact for:
- office + workflow template when office known
- jurisdiction + workflow template fallback when office unknown

## 8. Recommended first office playbook shape

The first version should stay small.

```json
{
  "office_name": "[office]",
  "jurisdiction_name": "Miami-Dade County",
  "workflow_templates": ["packet_submission", "counter_question"],
  "top_redirect_targets": ["Window B"],
  "top_rejection_reasons": ["outdated_form_version"],
  "photo_policy": "inconsistent",
  "queue_pattern_note": "Midday queues frequently exceed 20 minutes.",
  "playbook_confidence": "medium",
  "last_reviewed_at": "2026-04-25T10:55:00Z"
}
```

This is enough to improve dispatch without pretending to know everything.

## 9. Recommended first jurisdiction brief shape

```json
{
  "jurisdiction_name": "Miami-Dade County",
  "top_workflow_templates": ["packet_submission", "posting_proof"],
  "common_risk_flags": ["website_stale_risk", "process_drift"],
  "repeat_redirect_patterns": [
    "permit intake often redirected before acceptance review"
  ],
  "brief_confidence": "medium",
  "last_reviewed_at": "2026-04-25T10:55:00Z"
}
```

The jurisdiction brief should remain compressed.
The office playbook should hold the more specific truth.

## 10. Recommended first dispatch-brief composer rules

The first composer does not need embeddings, semantic search, or full Acontext retrieval.
It can be deterministic.

Suggested order:
1. exact office + workflow template brief if present
2. office playbook fallback
3. jurisdiction + workflow template fallback
4. recent reviewed episodes fallback

The output should answer only four questions:
- what is the likely routing trap?
- what evidence failure should be avoided?
- what next-step risk is most likely?
- what fallback instruction should the worker receive?

## 11. Test fixture recommendation

Daytime should create 5-10 fake reviewed episodes covering:
- clean acceptance
- repeated rejection reason
- redirect to new office/window
- evidence restriction at counter
- blocked visit due to closure/appointment requirement

Then run the local projector and inspect whether the generated playbooks/briefs become visibly smarter.

If the files do not become more useful after those fixtures, the contract is still too vague.

## 12. Product implications

This bootstrap suggests a very practical engineering slice:
- save reviewed result JSON
- run a projector function after review closure
- write/update local artifacts
- expose a simple dispatch briefing reader for operators or swarm flows

That would let EM test the memory loop before building city-specific frontends or full Acontext services.

## 13. Strongest daytime recommendation

If the team wants the smallest real build next, do this in order:
1. define local artifact paths and JSON contracts
2. emit reviewed result + reviewed episode after closure
3. merge office playbook deltas
4. compose one deterministic dispatch briefing
5. only then replace local writes with Acontext sinks

## 14. Sharp recommendation

**Do not let Acontext infrastructure become the excuse for not testing the memory loop. Build the file-based projector first and prove that the second city task is better than the first.**
