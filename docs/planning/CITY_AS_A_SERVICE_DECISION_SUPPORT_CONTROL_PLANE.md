# City as a Service — Decision Support Control Plane

> Last updated: 2026-04-29
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_COORDINATION_EVENT_CONTRACT.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `../acontext-integration-plan.md`
> - `../mcp_server/swarm/COORDINATION_CONTROL_PLANE.md`
> Status: build-planning draft

## 1. Why this doc exists

The planning stack already covers important pieces in isolation:
- City as a Service as the vertical wedge
- reviewed-result and memory contracts
- Acontext as the reusable memory layer
- observability metrics for learning quality
- event contracts for replay bundles
- swarm coordination control-plane ideas

What is still missing is the **system-level join** between them.
There is not yet one document that defines how:
- reviewed municipal work becomes durable decision support
- IRC/session coordination stays compact and restart-safe
- Acontext becomes retrieval and observability infrastructure instead of a vague future dependency
- cross-project lessons from municipal workflows become reusable operational leverage for Execution Market

This doc closes that gap.

The goal is simple:

> Every reviewed city task should improve the next dispatch through a durable, inspectable, memory-backed decision support loop.

## 2. Core thesis

City as a Service should not treat memory, IRC coordination, and observability as side systems.
They are part of the product.

The product advantage compounds when Execution Market can do all of the following at once:
- capture trusted municipal outcomes
- preserve why decisions were made
- retrieve the right prior context before the next run
- measure whether that prior context changed behavior and outcomes
- reuse the same coordination and memory seam across adjacent Execution Market AAS verticals

The control plane is the seam that connects:
- **EM DB** for execution truth
- **IRC/live session coordination** for active work
- **local projector artifacts** for deterministic replay and buildability
- **Acontext** for reusable context and cross-project observability

## 3. Product question this control plane must answer

For any repeated office/template workflow, the system should be able to answer:
- what happened last time?
- what did we learn?
- which artifact proves that learning?
- did the next dispatcher/operator actually reuse that learning?
- did reuse reduce redirects, repeated rejections, or uncertainty?

If the system cannot answer those questions quickly, the CaaS memory loop is still decorative.

## 4. System model

## 4.1 Source-of-truth split

### Execution Market DB
Canonical for:
- task lifecycle
- assignments
- submissions
- reviews
- payouts
- reputation effects

### IRC / live coordination sessions
Canonical only for:
- real-time status exchange
- operator interventions
- active routing discussion
- in-flight exceptions and escalations

### Local control-plane artifacts
Canonical for the first build of:
- deterministic event history
- replayable decision packets
- office-memory deltas
- dispatch-brief provenance

### Acontext
Canonical for reusable working intelligence such as:
- jurisdiction briefs
- office playbooks
- reviewed episode summaries
- retrieval-ready dispatch context
- cross-project metric and pattern views

## 4.2 Design principle

Acontext should be a **thinking layer**, not the ledger.
IRC should be a **bus**, not memory.
The local control plane should preserve enough structure that daytime implementation can ship before Docker or external infra is perfect.

## 5. The decision support loop

The control plane should standardize this loop:

1. `city_task_created`
2. worker executes and submits evidence
3. operator/system emits `reviewed_result` + `review_artifact`
4. control plane records `city_review_completed`
5. projector emits `reviewed_episode` + optional `office_playbook_delta`
6. control plane records promotion and merge events
7. brief composer builds future `dispatch_brief`
8. future dispatch retrieves relevant context
9. dispatcher changes instructions, routing, or risk handling
10. observability records whether reuse happened and whether outcome improved

This is the product loop.
Not just storage. Not just coordination. Not just analytics.

## 6. Control-plane objects

## 6.1 Required decision objects

The first slice should standardize these objects as the minimum viable decision support chain:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `office_playbook_delta`
- `office_playbook_after`
- `dispatch_brief`
- `review_packet`
- `event_summary`

## 6.2 Why `review_packet` matters

`review_packet` should become the compact bridge object between raw replay bundles and future retrieval.
It should summarize:
- the trusted outcome
- whether meaningful learning exists
- whether memory promotion is safe
- what future behavior should change
- which artifacts prove the claim

This makes it a strong candidate for future Acontext ingestion because it is:
- compact
- deterministic
- operator-safe
- provenance-aware

## 7. Coordination event model

## 7.1 Event principles

Control-plane events should be:
- compact
- lifecycle-oriented
- deterministic in order
- artifact-linked
- reusable across local replay, IRC summaries, and Acontext sinks

They should not be transcript dumps.

## 7.2 Recommended event layers

### Execution events
Examples:
- `city_task_created`
- `city_worker_assigned`
- `city_submission_received`
- `city_review_completed`

### Learning events
Examples:
- `city_reviewed_episode_written`
- `city_office_playbook_delta_written`
- `city_office_playbook_merged`
- `city_learning_strength_classified`

### Retrieval events
Examples:
- `city_dispatch_brief_composed`
- `city_dispatch_context_reused`
- `city_follow_on_task_created`

### Coordination events
Examples:
- `city_review_escalated`
- `city_redirect_observed`
- `city_operator_override`
- `city_session_summary_written`

## 7.3 Shared payload seam

A compact event payload should preserve the fields most useful across all sinks:

```json
{
  "event_name": "city_dispatch_context_reused",
  "task_id": "[task_id]",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "Permit Intake Window B",
  "coordination_session_id": "city_packet_submission_2026_04_29_001",
  "review_packet_id": "rp_2026_04_29_001",
  "source_episode_ids": ["ep_102", "ep_118"],
  "reuse_mode": "routing_changed",
  "event_time": "2026-04-29T07:00:00Z"
}
```

The important point is not perfection.
It is stable reuse.

## 8. IRC session management enhancement for CaaS

For the concrete local-server bring-up, session metadata, restart-safe rebuild order, and sink-swap acceptance gates, see `CITY_AS_A_SERVICE_ACONTEXT_LOCAL_SERVER_AND_SESSION_DISCIPLINE.md`.

## 8.1 Why IRC still matters

City tasks are messy in ways that APIs are not.
Offices redirect people, counters behave differently than expected, and operators sometimes need intervention in the middle of execution.
IRC remains valuable as the live coordination bus for those moments.

## 8.2 What should change

The CaaS layer should not rely on raw chat history for meaning.
Instead, each meaningful municipal run should have:
- a `coordination_session_id`
- compact event-shaped status lines
- optional JSON payload mode for machine ingestion
- restart-safe summary checkpoints written to local artifacts

## 8.3 Recommended transport discipline

Every important live update should be mirrorable into the control plane.
Examples:
- assignment issued
- worker reports redirect
- operator requests follow-up question
- review escalated because evidence is ambiguous
- brief changed after reviewed learning

Recommended machine-ingestible message shape:

```json
{
  "event_type": "city_redirect_observed",
  "grammar": "v1",
  "coordination_session_id": "city_packet_submission_2026_04_29_001",
  "task_id": "task_123",
  "workflow_template": "packet_submission",
  "office_name": "Permit Intake Window A",
  "redirect_target": "Window B",
  "timestamp": 1777446000.0
}
```

## 8.4 Restart-safe session rebuild

If IRC disconnects or a service restarts, the system should rebuild active context from:
1. latest local event ledger entries
2. latest `review_packet` or partial review state
3. latest coordination summary artifact
4. most recent dispatch brief used for the task

That gives the live bus a memory backbone instead of making it the memory itself.

## 9. Acontext role in the first real implementation

## 9.1 What Acontext should ingest first

Acontext should ingest distilled artifacts, not raw logs.
Best first candidates:
- `review_packet`
- `reviewed_episode`
- `office_playbook_after`
- jurisdiction brief snapshots
- compact metric rollups by office/template

## 9.2 What Acontext retrieval should return

Before dispatch, retrieval should return a compact brief that can shape decisions immediately:
- top redirect targets
- top rejection reasons
- known evidence restrictions
- worker familiarity notes
- confidence/risk warnings
- freshest source episodes and their dates

## 9.3 Why this matters

The Acontext bridge should improve operator and agent judgment, not just preserve history.
A good retrieval result changes instructions in under a minute.

## 10. Cross-project decision support

## 10.1 Why cross-project matters

The same product seam being designed for CaaS can become reusable infrastructure across Execution Market verticals.
The lesson is bigger than municipal workflows.

A shared decision-support control plane can later support:
- local verification services
- compliance errands
- inspection/report workflows
- real-world evidence collection categories outside city ops

## 10.2 Shared primitives worth standardizing now

The following primitives should be treated as cross-project assets:
- reviewed outcome contract
- memory promotion policy
- event summary contract
- dispatch brief provenance
- context reuse event semantics
- worker familiarity summary shape

If these primitives stabilize in CaaS first, later AAS verticals inherit a tested learning loop instead of starting from scratch.

## 10.3 Strategic payoff

This is how Execution Market stops being only a marketplace and becomes an operating system for real-world task learning.

## 11. Observability: what success should look like

The system is working when all of the following become measurable:
- reviewed tasks reliably produce memory-safe artifacts
- dispatch briefs exist for repeated office/template runs
- operators materially change instructions after retrieval
- repeated redirects decline after playbook updates
- repeated rejection-for-same-reason declines after learning is promoted
- familiarity-aware assignment outperforms proximity-only assignment
- intervention and escalation points become visible instead of anecdotal

## 11.1 Additional integration metrics

To connect CaaS observability with the control-plane seam, add these metrics to the existing stack:
- `coordination_session_rebuild_success_rate`
  - percent of interrupted sessions that recover using local decision artifacts
- `review_packet_ingestion_rate`
  - percent of eligible reviewed tasks that produce Acontext-ready packets
- `artifact_provenance_resolution_rate`
  - percent of dispatch warnings that can link back to a reviewed episode or review packet
- `context_reuse_to_outcome_lift`
  - outcome delta when dispatch reused prior memory vs when it did not
- `operator_override_explanation_rate`
  - percent of overrides carrying compact reason codes that can become future learning signals

## 12. Recommended build order

### Phase 1 — lock the compact decision seam
- finalize `review_packet` and `event_summary` behavior
- extend event payloads with `coordination_session_id` and provenance refs
- make `city_dispatch_context_reused` explicit in the contract

### Phase 2 — local control-plane ledger
- write append-only JSONL events for review, projector, retrieval, and override moments
- write per-office and per-workflow summaries from reviewed artifacts
- add restart-safe coordination summary files

### Phase 3 — retrieval and reuse discipline
- compose dispatch briefs from local artifacts first
- record whether operator behavior changed because of retrieval
- expose provenance inside the brief

### Phase 4 — IRC integration cleanup
- align live IRC status lines with stable event names
- support JSON payload mode for meaningful CaaS events
- generate compact session summaries for intervention and recovery

### Phase 5 — Acontext sink swap
- publish `review_packet`, `reviewed_episode`, and office playbook snapshots into Acontext
- preserve the same retrieval contract and observability semantics
- use the local-first/session-discipline checklist from `CITY_AS_A_SERVICE_ACONTEXT_LOCAL_SERVER_AND_SESSION_DISCIPLINE.md` as the acceptance gate, not mere successful transport writes

## 12.1 First shared implementation seam

To keep daytime implementation from scattering this logic across review, replay, IRC, and retrieval layers, the first build should treat one compact contract as the join point:

- **input:** reviewed replay bundle with `review_packet`, `event_summary`, and provenance refs
- **ledger write:** append one control-plane event row per meaningful decision moment
- **retrieval output:** one promotion-aware `dispatch_brief`
- **continuity output:** one `morning_pickup_brief.json`
- **observability output:** one scorecard row that can be grouped by office/template/session

That seam should be considered implementation-ready only if the same underlying promotion decision can flow without reinterpretation through:
- IRC/session rebuild
- local replay inspection
- Acontext retrieval
- operator brief rendering
- observability queries

If any surface has to guess the tone, placement, or trust class again, the seam is not locked.

## 12.2 Minimal append-only ledger shape

The first local control-plane ledger should stay boring and reusable.
Each JSONL row should be able to support replay, session rebuild, retrieval metrics, and Acontext export without transcript spelunking.

Suggested minimum shape:

```json
{
  "event_name": "city_dispatch_context_reused",
  "event_time": "2026-04-29T07:00:00Z",
  "coordination_session_id": "city_packet_submission_2026_04_29_001",
  "task_id": "task_123",
  "vertical": "city_as_a_service",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "Permit Intake Window B",
  "review_packet_id": "rp_2026_04_29_001",
  "promotion_class": "promote_cautiously",
  "guidance_tone": "verify_first",
  "guidance_placement": "secondary_caution",
  "reuse_mode": "routing_changed",
  "source_episode_ids": ["ep_102", "ep_118"],
  "operator_override_reason": null
}
```

This is intentionally close to the replay and retrieval seam.
The goal is to let later Acontext ingestion behave like a sink swap, not a semantic rewrite.

## 12.3 Session rebuild contract

Restart-safe IRC/session recovery should rebuild an active city workflow from a compact ordered set of artifacts, in this order:
1. latest ledger rows for the `coordination_session_id`
2. latest `dispatch_brief` actually used for the task
3. latest `review_packet` and `event_summary`
4. latest coordination summary artifact
5. linked `reviewed_episode` and `office_playbook_after` only when deeper inspection is needed

That order matters.
It keeps recovery fast and avoids forcing operators to reconstruct live context from raw transcripts or full replay bundles unless the compact decision seam is insufficient.

## 13. Concrete daytime handoff questions

The next build window should answer these in code, not in theory:
- where will the first append-only city control-plane ledger live?
- which service emits `city_dispatch_context_reused`?
- what exact operator actions count as reuse?
- what minimum artifact set is required to rebuild a live municipal session after interruption?
- how will `review_packet` be promoted into Acontext without leaking noisy or weak claims?

## 14. Sharpest insight

The moat is not just better evidence capture.
It is **decision support that compounds**.

A reviewed municipal task should not die as a closed ticket.
It should become:
- a reusable office lesson
- a future dispatch warning
- a routing improvement
- a measurable change in outcome quality

That is the control plane worth building.
