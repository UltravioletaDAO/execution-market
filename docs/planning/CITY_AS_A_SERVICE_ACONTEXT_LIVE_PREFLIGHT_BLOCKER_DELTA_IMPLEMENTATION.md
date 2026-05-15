# City as a Service — Acontext Live Preflight Blocker Delta Implementation

> Created: 2026-05-15 07:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin blocker delta landed; no live Acontext write, no retrieval, no runtime parity claim

## 1. Why this slice exists

The 6 AM handoff named the runtime-memory path clearly: run exactly one live Acontext write/retrieve parity pass **only after prerequisites are real**.

At 7 AM the read-only probe showed partial progress but not readiness:

- Docker daemon: available.
- Acontext Python SDK: missing.
- Local Acontext API at `http://localhost:8029/api/v1`: unreachable.
- Local Acontext dashboard at `http://localhost:3000`: unreachable.

So this slice records the smallest honest progress: Docker is no longer the blocker, but live transport is still blocked before any sink write.

## 2. New files

```text
mcp_server/city_ops/acontext_live_preflight_blocker_delta.py
mcp_server/tests/city_ops/test_acontext_live_preflight_blocker_delta.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_live_preflight_blocker_delta.json
docs/planning/CITY_AS_A_SERVICE_ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports:

```python
build_acontext_live_preflight_blocker_delta
load_acontext_live_preflight_blocker_delta
write_acontext_live_preflight_blocker_delta
```

## 3. Schema and safe claim

```text
city_ops.acontext_live_preflight_blocker_delta.v1
```

Safe claim added:

```text
acontext_live_preflight_blocker_delta_landed
```

This means only that a persisted internal/admin delta exists over a blocked Acontext preflight.

## 4. Source contract

The delta consumes a `city_ops.acontext_live_preflight.v1` source and refuses any source that:

- is already ready to attempt live transport;
- marks `acontext_sink_ready=true`;
- marks `runtime_parity_proven=true`;
- records a live Acontext write;
- records a live Acontext retrieval;
- puts blocked live/customer/dispatch/reputation claims in `safe_to_claim[]`.

## 5. Current blocker delta

Baseline blockers from the earlier handoff:

```text
docker_daemon_unavailable
acontext_python_sdk_missing
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
```

7 AM current blockers:

```text
acontext_python_sdk_missing
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
```

Cleared blocker:

```text
docker_daemon_unavailable
```

Verdict:

```text
live_transport_still_blocked_with_partial_prerequisite_progress
```

## 6. Readiness posture

The delta keeps all of these false:

```text
ready_to_attempt_live_transport=false
acontext_sink_ready=false
session_rebuild_ready=false
runtime_parity_proven=false
live_acontext_write_performed=false
live_acontext_retrieval_performed=false
customer_visible_aas_packaging_ready=false
public_route_ready=false
autonomous_dispatch_ready=false
operator_queue_launch_ready=false
erc8004_reputation_ready=false
payment_coverage_reverified_by_this_delta=false
production_infrastructure_reverified_by_this_delta=false
gps_or_metadata_exposure_allowed=false
worker_copyable_doctrine_ready=false
```

It also does not create customer copy, register routes, dispatch workers, attach reputation receipts, probe payment processors, reverify production infrastructure, or expose GPS/raw metadata.

## 7. Next safe step

Do not attempt live Acontext parity yet. Clear the remaining prerequisites first:

1. install or expose the Acontext Python SDK/CLI;
2. start the local Acontext API at `http://localhost:8029/api/v1`;
3. start the local Acontext dashboard at `http://localhost:3000`;
4. rerun the read-only preflight;
5. attempt exactly one live write/retrieve parity pass only if blockers are empty.

## 8. Test coverage

Targeted coverage verifies:

- fixture equality;
- Docker-cleared / SDK-API-dashboard-blocked delta semantics;
- live runtime/customer/dispatch/reputation readiness stays false;
- blocked claims stay in `do_not_claim_yet[]` and out of `safe_to_claim[]`;
- temp write/load roundtrip;
- ready-to-attempt preflights cannot be misrepresented as blocker deltas;
- live-write drift fails closed;
- forbidden safe claims fail closed;
- loader rejects readiness promotion and live-write authorization drift.

Focused verification during implementation:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_live_preflight_blocker_delta.py
# 9 passed
```
