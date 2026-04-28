# City as a Service — Coordination Event Contract

> Last updated: 2026-04-28
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_REPLAY_BUNDLE_SPEC.md`
> Status: implementation-oriented planning draft

## 1. Why this doc exists

The planning stack already says three useful things:
- Execution Market should remain the execution ledger
- IRC/session systems should remain the live coordination layer
- Acontext or a local projector should hold reusable operational memory

What is still under-specified is the contract **between** those layers.
This document defines the narrow event seam that lets city-task coordination become:
- replayable
- observable
- memory-safe
- easy to swap from local files to Acontext later

The goal is not a giant taxonomy.
The goal is one boring, durable event contract that both live coordination and memory projection can trust.

## 2. Core thesis

For City as a Service, coordination should be treated as a first-class product artifact.
Not every chat line matters.
But every meaningful operational turn should be representable as a compact event with:
- stable naming
- minimal required fields
- review-safe meaning
- clear projection value

That gives the stack a clean split:
- **Execution Market DB:** lifecycle truth
- **IRC/session streams:** live collaboration and intervention
- **coordination events:** stable operational signal
- **Acontext/local projector artifacts:** reusable office memory and observability

## 3. Design principles

### 3.1 Events should describe operational facts, not transcript fragments
Good:
- `city_redirect_observed`
- `city_review_completed`
- `city_dispatch_context_reused`

Bad:
- `operator_said_maybe_try_window_b`
- `worker_seemed_confused`

The first class is durable.
The second class belongs in transcripts or notes, not in the reusable seam.

### 3.2 Events should be compact enough for PR review
A reviewer should be able to inspect event output in git without replaying an entire live session.
That means:
- stable keys
- short rationale fields
- compact arrays
- no transcript dumps inside the core event body

### 3.3 Events should prefer review-safe truth
Before review, coordination events may reflect provisional field reality.
After review, some of those observations become memory-safe.
The contract must keep that distinction visible.

### 3.4 Events should be sink-agnostic
The same event payload should work for:
- line-delimited local JSON
- replay bundle summaries
- Acontext writes later
- aggregate analytics jobs

## 4. Event families

The first city-ops event contract only needs four families.

### 4.1 Dispatch family
Events about task setup and memory reuse before field execution.

Examples:
- `city_task_created`
- `city_dispatch_brief_composed`
- `city_dispatch_context_reused`
- `city_worker_assigned`

### 4.2 Field-execution family
Events about what the worker encountered.

Examples:
- `city_redirect_observed`
- `city_submission_received`
- `city_rejection_observed`
- `city_follow_on_task_recommended`

### 4.3 Review family
Events about converting messy field output into trusted product artifacts.

Examples:
- `city_review_started`
- `city_review_completed`
- `city_review_escalated`

### 4.4 Projection family
Events about turning reviewed truth into reusable memory.

Examples:
- `city_reviewed_episode_written`
- `city_office_playbook_delta_written`
- `city_dispatch_brief_improved`
- `city_manifest_written`

## 5. Canonical event names for the first implementation slice

The first slice should standardize exactly this set:
- `city_task_created`
- `city_dispatch_brief_composed`
- `city_dispatch_context_reused`
- `city_worker_assigned`
- `city_submission_received`
- `city_redirect_observed`
- `city_rejection_observed`
- `city_review_started`
- `city_review_completed`
- `city_review_escalated`
- `city_reviewed_episode_written`
- `city_office_playbook_delta_written`
- `city_dispatch_brief_improved`
- `city_manifest_written`

This is intentionally narrow.
If an event is not needed for replay proof, memory projection, or first observability, it can wait.

## 6. Required shared fields

Every city coordination event should carry these fields:

```json
{
  "event_name": "city_review_completed",
  "event_time": "2026-04-28T07:00:00Z",
  "task_id": "task_123",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "event_source": "review_loop",
  "correlation_id": "bundle_fixture_001"
}
```

### Required fields
- `event_name`
- `event_time`
- `task_id`
- `workflow_template`
- `jurisdiction_name`
- `event_source`
- `correlation_id`

### Strongly recommended fields
- `office_name`
- `review_status`
- `outcome_status`
- `redirect_target`
- `rejection_reasons[]`
- `memory_write_recommended`
- `source_type`
- `confidence`

## 7. Event-source values

The first pass should constrain `event_source` to a short allowlist:
- `dispatch_loop`
- `worker_submission`
- `review_loop`
- `projector`
- `replay_harness`
- `operator_override`

This keeps provenance inspectable.
A reviewer should know whether a claim came from live worker evidence, human review, or deterministic replay.

## 8. Correlation rules

The first daylight seam needs replayability more than global event complexity.
So the correlation rule should stay simple.

### 8.1 `correlation_id`
Use one correlation id across the replay bundle chain.
Examples:
- fixture id
- reviewed episode id
- deterministic replay run id

### 8.2 `task_id`
Always keep the concrete EM task id when available.
If replaying from a fixture, keep the original task id and let `correlation_id` identify the replay bundle.

### 8.3 Optional lineage fields
If needed later, add:
- `reviewed_episode_id`
- `office_playbook_id`
- `dispatch_brief_id`

But do not block the first seam on richer lineage modeling.

## 9. Memory-safety status

Not every event should automatically qualify for memory projection.
The contract should therefore support a small status seam.

Recommended field:
- `memory_projection_status`

Recommended first values:
- `not_applicable`
- `provisional`
- `review_safe`
- `projected`

### Example
- a worker reports a redirect → `provisional`
- operator confirms the redirect pattern during review → `review_safe`
- projector writes the office playbook delta → `projected`

This keeps the bridge honest.
The system can observe early field signals without prematurely hardening them into municipal memory.

## 10. Minimal event payload examples

### 10.1 Redirect observed

```json
{
  "event_name": "city_redirect_observed",
  "event_time": "2026-04-28T07:11:00Z",
  "task_id": "task_123",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "Permit Intake",
  "redirect_target": "Window B",
  "event_source": "worker_submission",
  "correlation_id": "fixture_redirect_001",
  "memory_projection_status": "provisional"
}
```

### 10.2 Review completed

```json
{
  "event_name": "city_review_completed",
  "event_time": "2026-04-28T07:18:00Z",
  "task_id": "task_123",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "Permit Intake",
  "outcome_status": "redirected",
  "review_status": "approved_with_learning",
  "memory_write_recommended": true,
  "event_source": "review_loop",
  "correlation_id": "fixture_redirect_001",
  "memory_projection_status": "review_safe"
}
```

### 10.3 Playbook delta written

```json
{
  "event_name": "city_office_playbook_delta_written",
  "event_time": "2026-04-28T07:19:00Z",
  "task_id": "task_123",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "Permit Intake",
  "event_source": "projector",
  "correlation_id": "fixture_redirect_001",
  "memory_projection_status": "projected"
}
```

## 11. Expected ordering for the first replay proof

The first replay proof should not require every possible event.
But when the full chain is present, the expected order should look like this:
1. `city_dispatch_brief_composed`
2. `city_dispatch_context_reused` (if prior memory existed)
3. `city_submission_received`
4. `city_redirect_observed` or `city_rejection_observed` when applicable
5. `city_review_started`
6. `city_review_completed`
7. `city_reviewed_episode_written`
8. `city_office_playbook_delta_written`
9. `city_dispatch_brief_improved`
10. `city_manifest_written`

The manifest acceptance contract should validate that the observed order is sensible for the replayed fixture.

## 12. Relationship to replay bundles

The replay bundle should not store raw event firehoses.
It should store a compact event summary derived from this contract.
That summary should be enough to answer:
- which meaningful coordination moments occurred
- whether they happened in the expected order
- whether memory-safety state advanced correctly
- whether the replay proof reached the improved-brief stage

## 13. Relationship to IRC session management

IRC remains valuable because city work is messy and interruptions are real.
But the first seam should stop treating IRC logs as the product artifact.

Instead:
- IRC/session flows remain the live collaboration surface
- operators and agents can still talk freely
- meaningful coordination turns emit canonical events
- those events become the bridge into replay, memory, and observability

That gives session management a clearer future.
The system can later summarize a live IRC thread by referencing stable event names instead of scraping conversational ambiguity.

## 14. Recommended first daytime build order

1. add a small event model/allowlist for the canonical city event names
2. emit events from replay-harness code paths first
3. validate required fields and ordering locally
4. write compact event summaries into replay bundles
5. only after that, wire the same contract into live review/projector flows

This keeps the first proof deterministic and reviewable before live coordination complexity is introduced.

## 15. Sharp recommendation

Do not begin by instrumenting everything.
Begin by making one replayed city learning loop legible through a tiny stable event contract.

If one rejection fixture and one redirect fixture can produce:
- validated artifacts
- a compact ordered event summary
- a manifest judgment
- a learning-strength classification

then the coordination seam is real.
After that, IRC summaries, Acontext sinks, and dashboards have something solid to build on.
