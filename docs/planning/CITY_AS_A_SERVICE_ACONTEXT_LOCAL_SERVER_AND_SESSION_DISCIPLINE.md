# City as a Service — Acontext Local Server and Session Discipline

> Last updated: 2026-05-02
> Parent docs:
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_BUILD_SPEC.md`
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `../acontext-integration-plan.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The planning stack already says two important things clearly:
- do **not** block the first City-as-a-Service learning loop on live Acontext infrastructure
- Acontext is still the best candidate for the later reusable memory and observability layer

What is still too soft is the bridge between those statements.
There is not yet one implementation-oriented document that explains:
- how to stand up Acontext locally once Docker is available
- which City-as-a-Service artifacts should be written locally first versus mirrored into Acontext later
- how IRC/session coordination should stay compact and restart-safe instead of degenerating into transcript dependency
- what acceptance gates prove the Acontext swap is changing transport only, not semantics

This doc closes that gap.

The target is simple:

> keep the first City-as-a-Service decision seam local and deterministic, while making the future Acontext server/session swap boring, reversible, and semantically lossless.

## 2. Core principle

Acontext should enter the first real City-as-a-Service build as a **sink and retrieval surface for compact reviewed artifacts**, not as a prerequisite for meaning.

That means the semantic order stays:
1. reviewed municipal outcome
2. compact decision object
3. local append-only control-plane event
4. promotion-aware dispatch brief
5. optional Acontext ingestion and later retrieval

If any Acontext integration step forces daytime builders to re-derive trust class, tone, placement, or reuse semantics from raw logs, the integration is too early or too loose.

## 3. Local-first artifact policy

### 3.1 Must exist locally before any Acontext write

For every eligible reviewed City-as-a-Service run, local deterministic artifacts should exist first:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `review_packet`
- `event_summary`
- `dispatch_brief`
- append-only control-plane ledger row(s)

Conditionally local first:
- `office_playbook_delta`
- `office_playbook_after`
- `morning_pickup_brief.json`
- jurisdiction brief snapshots once multiple episodes justify them

### 3.2 What Acontext should ingest first

The first Acontext sink should ingest distilled artifacts only:
- `review_packet`
- `reviewed_episode`
- `office_playbook_after`
- `dispatch_brief`
- compact ledger summaries grouped by office/template/session
- morning continuity artifacts when they exist

It should **not** ingest first:
- raw chat transcripts as authoritative memory
- unreviewed worker uploads as durable guidance
- replay bundles that require rereading many files to recover the promotion decision
- IRC lines without stable event names and provenance refs

## 4. Local server setup discipline

Once Docker is available, the local Acontext bring-up should stay narrow.
The goal is not “Acontext everywhere.”
The goal is to prove City-as-a-Service can publish and retrieve compact decision support without semantic drift.

### 4.1 Minimal bring-up checklist

1. start Docker daemon
2. run local Acontext server bootstrap
3. verify API responds locally
4. verify dashboard responds locally
5. create one project/namespace for Execution Market City-as-a-Service
6. run one fixture-backed ingestion of compact reviewed artifacts
7. run one retrieval that reproduces the same dispatch guidance class as the local brief

### 4.2 Suggested local endpoints to verify

Use the defaults already assumed in broader Acontext planning unless they change explicitly:
- API: `http://localhost:8029/api/v1`
- dashboard: `http://localhost:3000`

The important check is not just “HTTP 200.”
The real check is whether the local server can store and return the compact decision seam without semantic flattening.

## 5. Session discipline for City-as-a-Service

### 5.1 What a session is for

Acontext sessions should represent **coordination windows and retrieval context**, not become the canonical memory source.

For City-as-a-Service, a session should help answer:
- what task/run is active right now?
- what compact reviewed truth is currently shaping it?
- what changed during this coordination window?
- how do we rebuild the active context after restart without spelunking raw chat?

### 5.2 Session keying recommendation

Use a deterministic coordination key per meaningful municipal run:

```text
city_<workflow_template>_<jurisdiction_slug>_<yyyymmdd>_<sequence>
```

Examples:
- `city_packet_submission_miami_dade_20260502_001`
- `city_counter_question_miami_beach_20260502_003`

That same `coordination_session_id` should appear in:
- local ledger rows
- replay artifacts where relevant
- morning pickup brief
- Acontext session metadata
- Acontext artifact metadata

### 5.3 Session metadata minimums

Every City-as-a-Service Acontext session should carry at least:
- `vertical=city_as_a_service`
- `workflow_template`
- `jurisdiction_name`
- `office_name` when known
- `coordination_session_id`
- `task_id`
- `review_packet_id` when review exists
- `dispatch_brief_id` or equivalent brief ref when one is active

This keeps retrieval, observability, and restart rebuild aligned around the same compact join key.

## 6. IRC and live coordination discipline

### 6.1 IRC remains the bus, not the memory

Live coordination still matters because city work is messy:
- redirects happen mid-run
- counters behave differently than expected
- evidence rules can shift live
- operators may need to intervene before closure

But IRC should not hold product meaning by itself.
Every meaningful live update should be mirrorable into a compact event or summary artifact.

### 6.2 Message discipline

Meaningful coordination updates should be expressible in event-shaped payloads, for example:
- `city_worker_assigned`
- `city_redirect_observed`
- `city_review_escalated`
- `city_dispatch_context_reused`
- `city_session_summary_written`

JSON payload mode is preferred whenever machine ingestion matters.
The wording can stay human-readable, but the semantics must be stable enough to mirror into:
- local JSONL ledger
- continuity summary file
- later Acontext session/artifact writes

### 6.3 Restart-safe rebuild order

If IRC drops or a service restarts, rebuild active context in this order:
1. latest ledger rows for the `coordination_session_id`
2. latest `dispatch_brief` actually used
3. latest `review_packet`
4. latest `event_summary`
5. latest continuity summary artifact
6. deeper artifacts only if compact artifacts are insufficient

This preserves speed and trust.
It also prevents the live layer from becoming a hidden source of semantic drift.

## 7. Promotion-aware retrieval contract

Acontext retrieval should return the same operational distinctions already defined locally.
At minimum it must preserve:
- `promote_with_confidence`
- `promote_cautiously`
- `hold_for_more_evidence`
- `do_not_promote`

And it must preserve the operator-facing consequences of those classes:
- guidance tone
- guidance placement
- copyability/directiveness
- readiness to influence routing or fallback behavior

If Acontext returns only a generic blob like “previous office notes,” it is not ready to shape live dispatch.

## 8. First acceptable sink-swap proof

The first successful local-to-Acontext proof should demonstrate one replay-backed case where:
- local reviewed artifacts exist
- local ledger rows exist
- local dispatch brief exists
- Acontext ingests the compact decision seam
- Acontext retrieval returns enough structure to compose the same effective guidance class
- the next dispatch changes for the same reason under both local-only and Acontext-assisted paths

The goal is not byte-for-byte identity.
The goal is **semantic identity at the decision seam**.

## 9. Acceptance gates

A City-as-a-Service Acontext integration should not be considered ready until all of these pass:

### 9.1 Local-first gate
- no reviewed artifact requires Acontext to exist before it can be produced
- deterministic replay remains runnable offline/local

### 9.2 Session rebuild gate
- an interrupted municipal coordination session can be rebuilt from compact artifacts without reading raw transcript history

### 9.3 Promotion preservation gate
- retrieval preserves promotion class, guidance tone, and placement without re-derivation from raw bundles

### 9.4 Reuse proof gate
- at least one reviewed office/template case shows the next dispatch changed because retrieved prior memory was reused

### 9.5 Observability gate
- the system can record that reuse happened, which artifact justified it, and what behavior changed

## 10. What to defer

Do not let early Acontext enthusiasm pull the build into these too soon:
- transcript-heavy memory ingestion
- embeddings-first retrieval
- cross-city breadth before one office/template seam works well
- broad dashboard polish before compact decision support is stable
- generalized swarm memory redesign unrelated to City-as-a-Service proof

## 11. Recommended daytime implementation sequence

### Step 1
Lock the local compact seam:
- `review_packet`
- `event_summary`
- promotion-aware `dispatch_brief`
- append-only ledger row shape

### Step 2
Add continuity discipline:
- `coordination_session_id`
- session summary artifact
- morning pickup artifact
- rebuild order tests

### Step 3
Stand up local Acontext server once Docker is available and ingest one replay-backed case.

### Step 4
Prove retrieval can preserve the same guidance class and next-dispatch behavior change.

### Step 5
Only then widen ingestion to more artifacts, more offices, or richer observability.

## 12. Concrete output of this plan

If daytime follows this discipline, the Acontext integration story becomes much cleaner:
- local replay remains the product truth seam
- IRC remains useful without becoming the memory layer
- Acontext becomes a clean retrieval/observability surface
- the future transport swap stays reversible
- City-as-a-Service gains a real path from reviewed municipal work to reusable agent intelligence
