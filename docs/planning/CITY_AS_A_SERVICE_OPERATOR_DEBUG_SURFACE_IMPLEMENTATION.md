# City as a Service — Thin Operator Debug Surface Implementation

> Created: 2026-05-07 02:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: landed as a deterministic fixture; no readiness promotion

## 1. Why this seam exists

The live Acontext transport run is still blocked by local prerequisites. The safe next CaaS move is therefore not broader templates, a polished dashboard, or worker-facing doctrine. It is a thin operator/debug surface over the proof artifacts that already exist.

This surface answers five operator questions without reinterpreting semantics:

1. What proof anchor am I looking at?
2. What is safe to claim?
3. What is still unsafe to claim?
4. Is the guidance operator-visible or worker-copyable?
5. Is Acontext live transport blocked or attemptable?

## 2. New implementation

Code:

- `mcp_server/city_ops/operator_debug_surface.py`
- `mcp_server/tests/city_ops/test_operator_debug_surface.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/operator_debug_surface.json`

Export:

- `build_operator_debug_surface` from `mcp_server/city_ops/__init__.py`

New schema:

```text
city_ops.operator_debug_surface.v1
```

New safe label:

```text
thin_operator_debug_surface_landed
```

## 3. Source contract

The surface is read-only and derives only from:

- `session_rebuild_report.json`
- `acontext_transport_parity_result.json`
- `acontext_live_preflight_result.json`

Forbidden sources remain:

- raw transcripts
- unreviewed memory
- freeform worker chat
- private operator context

The surface refuses identity drift across the three artifacts and refuses any source artifact that upgrades worker-copyable guidance.

## 4. Claim boundaries

Current honest label:

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted + session_rebuild_consumer_landed + session_rebuild_report_fixture_landed + acontext_transport_parity_test_landed + acontext_live_preflight_landed + thin_operator_debug_surface_landed
```

Still blocked / not safe to claim:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
runtime_parity_proven
acontext_live_write_completed
acontext_live_retrieval_completed
acontext_live_transport_parity_landed
worker-copyable municipal doctrine
polished_review_console_ready
office_memory_view_ready
broad_operator_workflow_ready
```

## 5. Operator/debug cards

The fixture emits cards for:

- `identity` — proof anchor, compact decision, coordination session, review packet
- `safe_to_claim` — visible without softening
- `do_not_claim_yet` — visible without softening
- `operator_guidance` — operator-visible, not worker-copyable
- `transport` — blocked before live sink write unless the preflight is attemptable

This is intentionally data, not UI polish. It is the minimal inspection surface a future debug panel can render without weakening the proof contract.

## 6. Tests

Gate run:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 66 passed, 1 warning
```

Coverage added:

- deterministic fixture generation
- inherited `do_not_claim_yet` preservation
- attemptable preflight display without readiness promotion
- identity drift refusal
- worker-copyable upgrade refusal
- blocked safe-claim refusal

## 7. Current environment reality

The 2am actual preflight still showed:

```text
docker_available=false
acontext_python_sdk_available=false
local_acontext_api_reachable=false
local_acontext_dashboard_reachable=false
```

So the surface verdict remains:

```text
thin_operator_debug_surface_landed_live_transport_blocked
```

## 8. Next smallest proof

Start Docker/local Acontext and expose the Acontext SDK, rerun preflight until `ready_to_attempt_live_transport=true`, then write/retrieve the same `city_ops.acontext_transport_packet.v1` through live local Acontext and feed the retrieval through `assert_acontext_transport_parity`.

Until that passes, keep `acontext_sink_ready=false`, `session_rebuild_ready=false`, `runtime_parity_proven=false`, and worker-copyable municipal doctrine blocked.
