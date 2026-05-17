# City-as-a-Service — AAS runtime-memory blocker decision board

Date: 2026-05-17 03:00 EDT

Status: internal/admin decision-support artifact only.

## What landed

- `mcp_server/city_ops/aas_runtime_memory_blocker_decision_board.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_runtime_memory_blocker_decision_board.json`
- `mcp_server/tests/city_ops/test_aas_runtime_memory_blocker_decision_board.py`

Safe claim added:

```text
admin_aas_runtime_memory_blocker_decision_board_landed
```

## Why this exists

The prior Acontext diagnostics narrowed the live-runtime blocker to the Docker Desktop/containerd/network/layer-fetch path: Docker context and Buildx are available, GHCR manifests advertise `linux/arm64`, but an explicit-platform pull for the first Acontext image still timed out without output and did not place the image locally.

This board turns that into a daytime pickup ticket that connects four system-integration lanes:

1. memory system ↔ Acontext integration planning;
2. IRC/session handoff discipline;
3. cross-project decision support;
4. agent observability and success metrics.

It does not retry Docker, start compose, write or retrieve from Acontext, alter session-manager runtime behavior, expose a route, generate customer copy, enable dispatch, emit reputation, or reverify payments/production.

## Resolution decision tree

The board ranks the next safe paths:

1. repair Docker Desktop/containerd/network layer-fetch before compose;
2. use a trusted pre-populated image cache or mirror;
3. defer live runtime and continue fixture-backed handoffs;
4. replace the Acontext runtime only after a separate architecture decision.

All options explicitly keep `authorizes_live_runtime=false` until image inventory, compose health, API/dashboard health, an empty rebuilt readiness gate, and one live write/retrieve parity pass all succeed.

## Session-management enhancement

The artifact defines a compact IRC/session pickup pattern without raw transcript replay:

- preserve `proof_anchor_id`, `coordination_session_id`, `compact_decision_id`, and `review_packet_id`;
- emit one compact `city_acontext_runtime_blocker_confirmed` state event in future coordination logs;
- require future agents to carry `safe_to_claim[]` and `do_not_claim_yet[]` together.

## Agent success metrics

The board makes future agent success measurable without pretending the live dashboard exists:

- claim-boundary integrity;
- four-ID handoff completeness;
- Docker image inventory gate;
- live runtime parity gate;
- coordination metrics board continuity.

Current truth remains blocked on the Docker/image path:

```text
missing_required_image_count = 8
acontext_sink_ready = false
runtime_parity_proven = false
agent_observability_live_dashboard_ready = false
```

## What this does **not** claim

This does not authorize or claim:

- Docker pull blocker resolved;
- trusted image cache selected;
- all Acontext images present;
- compose services started;
- API/dashboard health;
- live Acontext write/retrieve parity;
- memory system ↔ Acontext runtime readiness;
- IRC runtime session-manager enhancement;
- public/customer dashboards or AAS packaging;
- operator queue launch or autonomous dispatch;
- ERC-8004 reputation readiness;
- payment or production reverification;
- GPS/raw metadata exposure;
- worker-copyable municipal doctrine.

## Next safe action

Fix or bypass the Docker layer-fetch path first. Only then:

1. verify all required Acontext images are present from trusted provenance;
2. start compose;
3. healthcheck API and dashboard;
4. rerun read-only preflight and rebuild the readiness gate empty;
5. attempt exactly one live write/retrieve parity pass using reviewed fixture context only.
