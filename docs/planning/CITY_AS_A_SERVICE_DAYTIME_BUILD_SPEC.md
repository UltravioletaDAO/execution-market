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
- replay-bundle judgment outputs, including `review_packet`
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

### 4.4 Replay judgment composer
Input:
- `bundle_manifest`
- `event_summary`
- `brief_improvement_scorecard`
- `improved_dispatch_brief`
- `office_playbook_delta`
- `reviewed_episode`

Output:
- `review_packet`
- one explicit promotion stance that later brief composition can respect without rereading the full bundle

### 4.5 Observability emitter
Input:
- lifecycle events from the review/projector/brief loop

Output:
- stable product events
- counters for review quality, routing quality, and memory reuse

### 4.6 Replay bundle writer
Input:
- baseline task context
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- optional `office_playbook_delta`
- merged office playbook artifact
- `improved_dispatch_brief`
- `brief_improvement_scorecard`
- `event_summary`
- `bundle_manifest`
- `review_packet`

Output:
- one deterministic replay bundle in a stable folder layout
- explicit artifact presence states for conditionally omitted outputs
- a PR-reviewable proof object that can be inspected without UI dependencies

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

If Python placement is awkward, equivalent TypeScript placement is acceptable.
The important thing is preserving the seam, not the exact language.

## 6. Concrete artifact rules

### 6.1 Always write these after reviewed closure
- one `reviewed_result`
- one `review_artifact`
- one `reviewed_episode`
- one `bundle_manifest` once replay acceptance checks can be evaluated
- one `event_summary` once the replay lifecycle can be summarized deterministically
- one `review_packet` once the replay bundle judgment is available

### 6.2 Write these conditionally
- `office_playbook_delta` only when the reviewed episode contains meaningful learning
- jurisdiction brief update only when multiple episodes support it
- placeholder artifact state objects when a conditional replay output is intentionally not emitted

### 6.3 Always recompute these when office context exists
- office playbook merge result
- dispatch brief for office + workflow template
- replay-bundle scorecard and packet outputs whenever a before/after brief comparison exists
- dispatch-visible guidance classification based on the packet promotion stance
- one explicit guidance-tone classification for the improved brief so operator language differs intentionally across confident, cautious, held, and blocked learning

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

The projector and replay judgment seam should stay boring.
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

### Gate G — compact judgment object
Given a replay bundle,
the system can emit a valid `review_packet` that:
- matches the manifest judgment
- states learning strength honestly
- makes memory promotion explicit
- points back to the canonical artifacts
- is strong enough to drive retrieval behavior without re-deriving meaning from the full bundle
- is strong enough to determine operator-facing guidance tone without forcing brief composers to improvise confidence language
- yields one explicit brief guidance classification that can be verified against the surfaced section placement and wording style of the improved dispatch brief

### Gate H — standard replay bundle
Given a replay fixture,
the system can emit one deterministic replay bundle that:
- includes the canonical artifact set in a stable layout
- records placeholder presence states for skipped or not-applicable outputs
- keeps `event_summary`, `bundle_manifest`, and `review_packet` mutually aligned
- can be reviewed in git without reconstructing meaning from raw logs

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

### Phase 4 — replay judgment layer
- emit `bundle_manifest` from the canonical replay artifacts
- emit `event_summary` from the canonical replay lifecycle
- emit `review_packet` from the canonical replay artifacts
- keep packet rationale short and behavior-focused
- enforce alignment between manifest judgment and memory-promotion stance
- emit or derive one stable promotion-policy interpretation that later retrieval can consume directly
- derive one explicit guidance-tone contract for brief composition, for example `directive`, `cautious`, `inspect_only`, or `suppressed`

### Phase 5 — replay bundle writer
- write the canonical replay bundle in a stable folder layout
- include placeholder objects or explicit presence-state handling for conditionally omitted artifacts
- make the bundle PR-reviewable without relying on dashboard polish

### Phase 6 — debug surfaces
- make artifacts inspectable by operator/admin
- add memory preview before confirm

### Phase 7 — observability
- emit loop events
- create first review/memory effectiveness dashboard or logs

### Phase 8 — only then consider Acontext sink swap
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

## 14. Review-friendly replay reading order

The first deterministic replay bundle should be easy to inspect in a fixed order:
1. `bundle_manifest`
2. `event_summary`
3. `review_packet`
4. `brief_improvement_scorecard`
5. `improved_dispatch_brief`
6. `office_playbook_delta`
7. `reviewed_episode`
8. `reviewed_result`
9. `baseline_dispatch_brief`

This order keeps the proof centered on operational improvement first, then the compact reviewed judgment object, then the supporting evidence chain.

## 15. Sharpest next daylight proof target

The narrowest strong daytime win is now:
- one reviewed rejection fixture bundle
- one reviewed redirect fixture bundle
- deterministic `event_summary`
- deterministic `bundle_manifest`
- explicit `review_packet`
- one conservative learning-strength call per bundle
- one explicit promotion-policy outcome that changes how the improved brief surfaces learned guidance

If that bundle pair is legible, behavior-changing, and promotion-safe, broader Review Console and Acontext integration work can expand from a real proof seam instead of optimism.

## 16. Morning briefing artifact and daytime pickup contract

The first daylight implementation pass should not rely on scattered notes across planning docs.
It should produce and review one tiny execution-facing briefing artifact per replay bundle or fixture batch.

Recommended output:
- `morning_pickup_brief.json` beside the replay bundle or fixture batch summary

Minimum fields:
- `build_target`
- `fixtures_completed`
- `fixtures_blocked`
- `acceptance_gates_passed`
- `acceptance_gates_failed`
- `promotion_policy_observations`
- `guidance_tone_observations`
- `next_smallest_proof`
- `do_not_claim_yet`

This artifact is not another archive object.
It is a daylight coordination object that answers:
- what proof was actually completed
- what remains blocked or unproven
- what the next smallest honest build move is
- what claims the team must explicitly avoid making yet

### 16.1 Why this matters

The city-ops planning seam is now rich enough that daytime risk is no longer lack of direction.
The risk is overclaiming from partial bundles or reopening broad architectural discussion when one smaller proof still decides the product truth.

A compact pickup brief keeps the loop honest:
- replay bundle = audit archive
- manifest/event/packet = proof contract
- morning pickup brief = coordination handoff for the next engineering block

### 16.2 Minimum honesty rules for the pickup brief

The pickup brief should explicitly state:
- which acceptance gates truly passed
- which bundle outputs are still placeholder or partial
- whether dispatch guidance changed behaviorally or only cosmetically
- whether promotion stance is safe to surface in operator-facing tone yet
- whether tone changed correctly across promoted, cautious, held, or blocked guidance instead of flattening everything into the same warning style

If those answers are fuzzy, the brief should say so directly.
That is better than optimistic compression.

## 13. Sharp recommendation

If daytime wants one clean next move, it should build this exact product loop:

**reviewed result -> reviewed episode -> office playbook -> dispatch brief**

with fixtures first, local files second, observability third, and live memory infrastructure last.

That is the smallest build that can prove City as a Service is becoming compounding municipal intelligence instead of just a new task category.
