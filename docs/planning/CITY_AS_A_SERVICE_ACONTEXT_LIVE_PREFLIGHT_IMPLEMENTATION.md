# City as a Service — Acontext Live Preflight Implementation

> Created: 2026-05-07 01:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: live transport preflight landed; live Acontext sink still false

## 1. Why this slice exists

The midnight slice created a deterministic local Acontext transport parity fixture. It proved that a `city_ops.session_rebuild_report.v1` can be packaged into `city_ops.acontext_transport_packet.v1`, retrieved locally, and compared without changing identity, claim boundaries, promotion class, guidance tone, guidance placement, worker-copyability, or readiness.

The next requested proof is a live local Acontext write/retrieve run. This cron environment cannot run it yet: Docker is not connected, the Acontext Python package is not installed, and the default local API/dashboard endpoints are not reachable.

Rather than pretending the sink exists, this slice adds the guardrail immediately before the live run: a read-only preflight artifact that says whether the live transport test may be attempted, while explicitly refusing to write to Acontext or promote readiness.

## 2. New files

```text
mcp_server/city_ops/acontext_live_preflight.py
mcp_server/tests/city_ops/test_acontext_live_preflight.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_live_preflight_result.json
docs/planning/CITY_AS_A_SERVICE_ACONTEXT_LIVE_PREFLIGHT_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports `build_acontext_live_preflight_result`.

## 3. New schema

```text
city_ops.acontext_live_preflight.v1
```

The preflight reads the existing `city_ops.acontext_transport_packet.v1` and a read-only environment probe. It never creates an Acontext project, session, artifact, or sink write.

## 4. What the preflight checks

- Docker daemon availability
- Acontext Python SDK availability
- local Acontext API reachability at `http://localhost:8029/api/v1`
- local dashboard reachability at `http://localhost:3000`
- that no live Acontext write or retrieval has been performed during preflight
- that blocked claims remain outside `safe_to_claim[]`

A ready preflight means only:

```text
ready_to_attempt_live_transport=true
```

It still keeps these false:

```text
acontext_sink_ready=false
session_rebuild_ready=false
runtime_parity_proven=false
live_acontext_write_performed=false
live_acontext_retrieval_performed=false
```

## 5. Current environment result

The real 1am probe returned blocked:

```text
docker_available=false
acontext_python_sdk_available=false
local_acontext_api_reachable=false
local_acontext_dashboard_reachable=false
```

Blockers:

```text
docker_daemon_unavailable
acontext_python_sdk_missing
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
```

So the live Acontext sink test was not attempted.

## 6. Honest claim label

This slice adds only:

```text
acontext_live_preflight_landed
```

The current CaaS label is now:

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted + session_rebuild_consumer_landed + session_rebuild_report_fixture_landed + acontext_transport_parity_test_landed + acontext_live_preflight_landed
```

Do **not** claim:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
runtime_parity_proven
acontext_live_transport_parity_landed
worker-copyable municipal doctrine
```

## 7. Test gate

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

The new focused gate passed:

```text
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops/test_acontext_transport.py mcp_server/tests/city_ops/test_acontext_live_preflight.py -q
# 9 passed, 1 warning
```

## 8. Next smallest proof

When Docker and the Acontext SDK/server are available:

1. rerun `build_acontext_live_preflight_result()` and require `ready_to_attempt_live_transport=true`
2. write the existing `city_ops.acontext_transport_packet.v1.stored_payload` into local Acontext under `execution_market.city_as_a_service`
3. retrieve by `proof_anchor_id`, `packet_id`, and namespace
4. feed the retrieved payload through `assert_acontext_transport_parity(packet, retrieval)`
5. only then add a separate live transport parity label

Until that passes, keep `acontext_sink_ready=false`.
