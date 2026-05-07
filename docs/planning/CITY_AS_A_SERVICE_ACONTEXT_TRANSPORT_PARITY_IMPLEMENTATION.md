# City as a Service — Acontext Transport Parity Implementation

> Created: 2026-05-07 00:18 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: local parity fixture landed; live Acontext sink still false

## 1. Why this slice exists

The read-only session rebuild report proved that a compact proof block can become an inspectable debug artifact without reopening raw transcripts, unreviewed memory, freeform worker chat, private operator context, or a live sink.

The next risk was transport drift: if the same compact truth later moves through Acontext, the transport layer must not reinterpret the municipal learning, soften blocked claims, make cautious guidance worker-copyable, or flip readiness.

This slice adds the first deterministic local Acontext transport parity fixture. It models the exact write/retrieve contract that a future live Acontext adapter must preserve.

## 2. New files

```text
mcp_server/city_ops/acontext_transport.py
mcp_server/tests/city_ops/test_acontext_transport.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_transport_parity_result.json
docs/planning/CITY_AS_A_SERVICE_ACONTEXT_TRANSPORT_PARITY_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports `build_acontext_transport_parity_result`.

## 3. New schemas

```text
city_ops.acontext_transport_packet.v1
city_ops.acontext_transport_retrieval.v1
city_ops.acontext_transport_parity_result.v1
```

The packet is derived from `city_ops.session_rebuild_report.v1` only.
The retrieval fixture returns the same stored payload without semantic reinterpretation.
The parity result records which boundaries survived.

## 4. What is preserved

The transport fixture checks:

- identity:
  - `proof_anchor_id`
  - `coordination_session_id`
  - `compact_decision_id`
  - `review_packet_id`
- claim boundaries:
  - inherited safe claims
  - `do_not_claim_yet[]`
  - blocked readiness/closure claims
- promotion boundaries:
  - `promotion_class`
  - `guidance_tone`
  - `guidance_placement`
  - `behavior_change_class`
  - `summary_judgment`
  - `source_episode_ids`
- worker-copyability boundary:
  - `copyable_worker_instruction.allowed=false`
- readiness:
  - `session_rebuild_ready=false`
  - `acontext_sink_ready=false`
  - `report_promotes_readiness=false`
  - `consumer_promotes_readiness=false`

## 5. Honest claim label

This slice adds only:

```text
acontext_transport_parity_test_landed
```

The full current CaaS label is now:

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted + session_rebuild_consumer_landed + session_rebuild_report_fixture_landed + acontext_transport_parity_test_landed
```

Do **not** claim:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
worker-copyable municipal doctrine
runtime_parity_proven
```

## 6. Test gate

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 56 passed, 1 warning
```

New tests fail if:

- the transport packet marks a live Acontext write as performed
- retrieval changes identity, claims, promotion boundaries, or readiness
- `acontext_sink_ready` or other blocked claims appear in `safe_to_claim[]`
- worker-copyable guidance becomes allowed
- session rebuild readiness is promoted during retrieval

## 7. Product meaning

This is still a local fixture, not a live Acontext integration.

The useful product movement is narrower and more important: Acontext is now framed as a transport swap over an already-reviewed compact proof unit. The future live sink has a concrete parity contract to satisfy instead of a vague “store some memory” instruction.

That keeps the CaaS loop honest:

```text
reviewed municipal reality
-> compact decision/report
-> transport packet
-> retrieval parity check
-> later live Acontext adapter with the same contract
```

## 8. Next smallest proof

The next CaaS block should not broaden into templates, dashboards, or generalized memory.

Run this same packet through a live local Acontext server once Docker is available, then prove the retrieved payload preserves the same identity, claim, promotion, copyability, and readiness boundaries.

Until that live write/retrieve path passes, keep:

```text
acontext_sink_ready=false
session_rebuild_ready=false
worker-copyable municipal doctrine=false
```
