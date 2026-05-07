# City as a Service — Proof Observability Metrics Implementation

> Created: 2026-05-07 03:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: deterministic metrics fixture landed; no live-readiness claim

## 1. Why this seam exists

The 02:00 seam made the proof block inspectable through a thin operator/debug surface. The next risk was that the surface could still become a prose-only artifact: useful to read, but hard for a coordinator, IRC handoff, or morning brief to compare over time.

This seam adds a metrics snapshot over the surface without broadening into dashboard work or live Acontext writes.

## 2. What landed

New implementation:

- `mcp_server/city_ops/proof_observability.py`
- `mcp_server/tests/city_ops/test_proof_observability.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/proof_observability_snapshot.json`

Updated:

- `mcp_server/city_ops/__init__.py`
- `docs/planning/CITY_AS_A_SERVICE_MORNING_BRIEF_2026_05_07.md`
- `docs/planning/CITY_AS_A_SERVICE_IMPLEMENTATION_BACKLOG_AND_DECISIONS.md`
- `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
- `docs/planning/CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`

New schema:

```text
city_ops.proof_observability_snapshot.v1
```

## 3. Data flow

```text
operator_debug_surface.json
-> proof_observability_snapshot.json
```

The snapshot is derived from the operator/debug surface only. It does not read raw transcripts, unreviewed memory, worker freeform chat, private operator context, or live Acontext state.

## 4. What the snapshot measures

The first metrics are deliberately boring and inspectable:

- `safe_claim_count`
- `blocked_claim_count`
- `debug_card_count`
- `acontext_blocker_count`
- `critical_readiness_false_count`
- `all_critical_readiness_flags_false`
- `local_transport_parity_fixture_passed`
- `ready_to_attempt_live_transport`
- `worker_copyable_surface_enabled`
- `copyable_worker_instruction_allowed`
- `live_acontext_write_performed`
- `live_acontext_retrieval_performed`

The first signals are:

- `claim_boundary_visibility`
- `operator_guidance_boundary`
- `local_transport_parity_fixture`
- `live_acontext_prerequisites`
- `readiness_honesty`

## 5. Claim boundary

Earned at most:

```text
proof_observability_metrics_landed
```

Still false / blocked:

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

## 6. Guardrails

Tests fail if the snapshot:

- accepts `acontext_sink_ready` or another blocked claim as safe
- hides inherited `do_not_claim_yet` boundaries
- accepts worker-copyable guidance
- accepts promoted `session_rebuild_ready`, `acontext_sink_ready`, or `runtime_parity_proven`
- reads from a surface that performed live sink writes or semantic reinterpretation

## 7. Current fixture verdict

The fixture verdict is:

```text
proof_observability_metrics_landed_live_transport_blocked
```

The current decision-support recommendation is to clear local Acontext prerequisites before live sink work:

```text
docker_daemon_unavailable
acontext_python_sdk_missing
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
```

## 8. Verification

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 73 passed, 1 warning

python3 -m py_compile \
  mcp_server/city_ops/proof_observability.py \
  mcp_server/tests/city_ops/test_proof_observability.py
# passed
```

## 9. Next smallest proof

Do not broaden into templates, polished dashboard work, or worker-copyable doctrine.

The next useful proof remains live local Acontext transport parity:

1. start Docker and local Acontext without changing CaaS semantics
2. install or expose the Acontext Python SDK/CLI in this environment
3. verify `http://localhost:8029/api/v1` and `http://localhost:3000` are reachable
4. rerun preflight until `ready_to_attempt_live_transport=true`
5. run one live local write/retrieve using the existing transport packet
6. reuse `assert_acontext_transport_parity(...)`
7. keep `acontext_sink_ready=false` until the live path passes without semantic strengthening
