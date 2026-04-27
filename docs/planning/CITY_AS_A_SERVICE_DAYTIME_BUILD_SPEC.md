# City as a Service — Daytime Build Spec

> Last updated: 2026-04-27
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_IMPLEMENTATION_SLICE_V1.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `CITY_AS_A_SERVICE_LOCAL_PROJECTOR_BOOTSTRAP.md`
> - `CITY_AS_A_SERVICE_REVIEW_AND_ROUTING_UI_BLUEPRINT.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The City-as-a-Service planning set is now rich enough that the main risk is not lack of ideas.
The risk is daytime building the wrong first slice, building it in the wrong order, or tying it too early to infrastructure that is still blocked.

This doc turns the current planning stack into a narrow build handoff.
It answers:
- what to implement first
- which files, objects, and surfaces should exist
- what can stay fake/local
- what acceptance gates prove the loop is real

The target is simple:

> make the second city task smarter than the first one using reviewed municipal memory.

## 2. Non-negotiable product principle

The first real build is **not** a broad city workflow platform.
It is a learning loop.

That loop is:
1. worker completes a city task
2. operator reviews it into a normalized result
3. system emits replayable memory artifacts
4. next dispatch retrieves a compact brief
5. operator or agent changes instructions because of that brief

If that loop is missing, more templates, more UI, and more infra will only scale confusion.

## 3. What to build in the first implementation window

### In scope
- `counter_question` reviewed-result flow
- `packet_submission` reviewed-result flow
- local file-based artifact sink
- deterministic projector that writes reviewed episodes and office playbooks
- pre-dispatch briefing composer
- thin operator surfaces or admin/debug views that prove the loop works
- instrumentation for review completion and memory reuse

### Explicitly out of scope
- live Acontext dependency
- embeddings or semantic retrieval
- multi-city generalization
- large workflow orchestration engine
- worker marketplace redesign
- automatic learning directly from raw worker uploads
- generalized city dashboard for executives

## 4. Recommended code seams

Daytime should avoid burying the first slice in giant abstractions.
Use a thin seam with four responsibilities.

### 4.1 Result normalizer
Input:
- task envelope
- worker submission
- operator review form values

Output:
- `reviewed_result`
- `review_artifact`

### 4.2 Projector
Input:
- task envelope
- `reviewed_result`
- `review_artifact`

Output:
- `reviewed_episode`
- optional `office_playbook_delta`
- merged office playbook artifact
- optional jurisdiction brief artifact later

### 4.3 Brief composer
Input:
- office playbook artifact
- recent reviewed episodes
- task template + office/jurisdiction context

Output:
- `dispatch_brief`

### 4.4 Observability emitter
Input:
- lifecycle events from the review/projector/brief loop

Output:
- stable product events
- counters for review quality, routing quality, and memory reuse

## 5. Suggested first file layout

This can live behind feature flags at first.
It does not need to be public UI-ready.

```text
mcp_server/city_ops/
  contracts.py
  review_normalizer.py
  projector.py
  brief_composer.py
  observability.py
  fixtures/
    city_ops_review_cases/

docs/planning/examples/city_ops_memory/
  reviewed_results/
  reviewed_episodes/
  office_playbooks/
  jurisdiction_briefs/
  dispatch_briefs/
```

If Python placement is awkward, equivalent TypeScript placement is acceptable.
The important thing is preserving the seam, not the exact language.

## 6. Concrete artifact rules

### 6.1 Always write these after reviewed closure
- one `reviewed_result`
- one `review_artifact`
- one `reviewed_episode`

### 6.2 Write these conditionally
- `office_playbook_delta` only when the reviewed episode contains meaningful learning
- jurisdiction brief update only when multiple episodes support it

### 6.3 Always recompute these when office context exists
- office playbook merge result
- dispatch brief for office + workflow template

### 6.4 Never do this in v1
- write memory directly from raw upload
- infer stable office doctrine from one ambiguous hearsay-only event
- let live infrastructure block local replayability

## 7. Minimal operator surfaces

The first slice only needs enough surface area to support reviewed truth and retrieval.

### 7.1 Review Console v0
Must support:
- evidence rail
- normalized outcome form
- review decision form
- follow-on recommendation selection
- memory write preview

### 7.2 Dispatch Brief Panel v0
Must support:
- show summary, top risks, rejection reasons, redirect targets, evidence guidance, fallback instruction
- copy recommended fallback into task instructions
- inspect source episodes

### 7.3 Office Memory Debug View v0
Must support:
- current office playbook
- recent reviewed episodes
- recent generated brief
- provenance from episode to playbook to brief

This can be admin-only or even JSON-first initially.
The requirement is inspectability, not polish.

## 8. The first deterministic projector behavior

The projector should stay boring.
No model inference needed for the first loop.

### Example projector logic
1. save `reviewed_result`
2. map it into `reviewed_episode`
3. inspect for known learning signals:
   - redirect observed
   - rejection reason repeated
   - evidence restriction discovered
   - office scope corrected
   - queue pattern observed
4. emit `office_playbook_delta` when one of those signals appears
5. merge compact playbook fields
6. regenerate `dispatch_brief`

### Important constraint
The projector should be rerunnable on fixtures without changing semantics.
Deterministic replay matters more than cleverness.

## 9. Recommended fixture pack

Before any live rollout, build a fixture pack of 8-12 reviewed cases.

Minimum scenario coverage:
1. clean `counter_question` with stable answer
2. `packet_submission` rejected for outdated form version
3. repeated same rejection reason at same office
4. redirect from intake desk to specific window
5. office disallows counter photos
6. office closed unexpectedly during business hours
7. accepted packet with stamped receipt
8. inconclusive case with low-confidence hearsay
9. queue delay worth operational note
10. rerun after memory exists, showing changed dispatch brief

The fixture pack is the fastest way to prove whether the contracts are too vague.

## 10. Acceptance gates

The first slice is only real if all of these pass.

### Gate A — reviewed closure completeness
Given a reviewed city task,
the system can produce valid:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`

### Gate B — replayable projector
Given the same reviewed fixtures twice,
the emitted playbook and brief artifacts are deterministic.

### Gate C — useful memory delta
Given repeated rejection or redirect fixtures,
the office playbook changes in a visible and defensible way.

### Gate D — dispatch improvement visibility
Given a later task at the same office/template,
the generated brief clearly warns about the learned routing/evidence failure mode.

### Gate E — provenance traceability
An operator can trace a brief claim back to the reviewed episode(s) that caused it.

### Gate F — event instrumentation
The loop emits at least these events:
- `city_review_completed`
- `city_reviewed_episode_written`
- `city_office_playbook_delta_written`
- `city_dispatch_brief_composed`
- `city_dispatch_context_reused`

## 11. Recommended implementation order

### Phase 1 — contracts and fixtures
- lock JSON/object shapes
- create fixture pack
- write schema validation

### Phase 2 — review normalizer
- turn reviewed UI/admin input into `reviewed_result` + `review_artifact`
- validate required/conditional fields

### Phase 3 — local projector
- emit reviewed episodes
- merge office playbooks
- emit dispatch briefs

### Phase 4 — debug surfaces
- make artifacts inspectable by operator/admin
- add memory preview before confirm

### Phase 5 — observability
- emit loop events
- create first review/memory effectiveness dashboard or logs

### Phase 6 — only then consider Acontext sink swap
- keep contracts identical
- swap transport, not product meaning

## 12. Daytime engineering questions worth answering early

These are the only high-value open questions for the first slice:
- where should reviewed artifacts live in the product codebase?
- is the first review surface server-rendered/admin-only or dashboard-native?
- what is the smallest schema validation layer that can guard bad writes?
- how should office keys be derived so memory collisions stay low?
- what exact operator action counts as `city_dispatch_context_reused`?

Everything else should wait until the local loop proves value.

## 13. Sharp recommendation

If daytime wants one clean next move, it should build this exact product loop:

**reviewed result -> reviewed episode -> office playbook -> dispatch brief**

with fixtures first, local files second, observability third, and live memory infrastructure last.

That is the smallest build that can prove City as a Service is becoming compounding municipal intelligence instead of just a new task category.
