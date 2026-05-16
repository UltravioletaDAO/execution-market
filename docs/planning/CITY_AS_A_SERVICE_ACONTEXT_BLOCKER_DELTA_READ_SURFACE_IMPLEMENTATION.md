# City as a Service — Acontext Blocker Delta Read Surface Implementation

> Created: 2026-05-16 22:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin read surface landed; no live Acontext write, no retrieval, no runtime parity claim

## 1. Why this slice exists

The latest Acontext path had a useful blocker delta: Docker is available, but the Acontext Python SDK, local API, and local dashboard still block a live write/retrieve parity attempt.

This slice makes that delta operator-readable without turning it into authority. It is a pass-through internal/admin surface for prerequisite cards, blocker summary, next actions, and sticky claim boundaries.

## 2. New files

```text
mcp_server/city_ops/acontext_live_preflight_blocker_delta_read_surface.py
mcp_server/tests/city_ops/test_acontext_live_preflight_blocker_delta_read_surface.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_live_preflight_blocker_delta_read_surface.json
docs/planning/CITY_AS_A_SERVICE_ACONTEXT_BLOCKER_DELTA_READ_SURFACE_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports:

```python
build_acontext_live_preflight_blocker_delta_read_surface
load_acontext_live_preflight_blocker_delta_read_surface
write_acontext_live_preflight_blocker_delta_read_surface
```

## 3. Schema and safe claim

```text
city_ops.acontext_live_preflight_blocker_delta_read_surface.v1
```

Safe claim added:

```text
admin_acontext_blocker_delta_surface_landed
```

Meaning: an internal/admin surface can display the blocked Acontext prerequisite state. It does not clear prerequisites and does not authorize any live sink write.

## 4. Source contract

The surface consumes only:

```text
acontext_live_preflight_blocker_delta.json
```

It refuses source deltas that:

- are ready to attempt live transport;
- mark Acontext sink readiness or runtime parity true;
- record a live Acontext write or retrieval;
- have no current blockers;
- mark public/customer/dispatch/reputation/runtime claims safe.

## 5. Rendered operator sections

The surface renders:

- four-ID session header;
- blocker delta summary;
- prerequisite status cards;
- operator next-action cards;
- sticky claim-boundary footer;
- conservative readiness flags.

Docker is shown as cleared but explicitly not authority for a live write. SDK/API/dashboard remain blocking.

## 6. Readiness posture

The surface keeps all of these false:

```text
surface_promotes_live_readiness=false
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
payment_coverage_reverified_by_this_surface=false
production_infrastructure_reverified_by_this_surface=false
gps_or_metadata_exposure_allowed=false
worker_copyable_doctrine_ready=false
```

It also registers no route, writes no customer copy, enables no dispatch automation, emits no reputation receipt, reverifies no payment/production infrastructure, and exposes no GPS/raw metadata.

## 7. Next safe step

Clear the remaining prerequisites, then rerun read-only preflight:

1. install or expose Acontext Python SDK/CLI;
2. start local Acontext API at `http://localhost:8029/api/v1`;
3. start local dashboard at `http://localhost:3000`;
4. rerun preflight;
5. attempt exactly one live write/retrieve parity pass only if blockers are empty.

## 8. Verification

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_live_preflight_blocker_delta.py \
  mcp_server/tests/city_ops/test_acontext_live_preflight_blocker_delta_read_surface.py
# 17 passed
```
