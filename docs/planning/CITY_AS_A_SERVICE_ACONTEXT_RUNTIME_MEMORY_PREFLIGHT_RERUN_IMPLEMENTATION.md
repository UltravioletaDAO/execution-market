# City as a Service — Acontext Runtime-Memory Preflight Rerun Implementation

> Status: 2026-05-16 7 AM internal/admin blocker-progress slice
> Scope: Execution Market AAS / City-as-a-Service only
> Product posture: no customer/public launch claim, no live Acontext parity claim

## What changed

This slice converted the next runtime-memory step into a tested internal artifact:

```text
acontext_runtime_memory_preflight_rerun.json
```

It records three facts without overclaiming:

1. Docker is available.
2. The active City Ops runner can expose the dedicated Acontext SDK venv for read-only preflight import.
3. Local Acontext API/dashboard reachability still blocks any live write/retrieve parity attempt.

## Runtime observation

A local compose startup was attempted from `~/clawd/infra/acontext` with the checked-in Acontext compose manifest and env file. The multi-image pull/startup did not settle inside the 7 AM work window and was stopped. No Acontext containers were observed running afterward, and the expected local endpoints remained unreachable:

- `http://localhost:8029/api/v1`
- `http://localhost:3000`

## Runner bridge

The default active Python runner still does not have `acontext` installed globally. The preflight runner now supports an explicit venv SDK bridge:

```text
~/clawd/.venv-acontext/lib/python3.14/site-packages
```

That bridge is for read-only preflight work only. It does not authorize live Acontext writes, live retrievals, sink readiness, or runtime parity claims.

## Safe claim

```text
admin_acontext_runtime_memory_preflight_rerun_landed
```

Meaning: the runtime-memory preflight was rerun with the explicit SDK bridge available, and the remaining blockers are now narrower.

## Still blocked

The rebuilt preflight still has blockers:

```text
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
```

Therefore these remain blocked:

- live Acontext write/retrieve parity
- Acontext sink readiness
- runtime parity
- customer-visible packaging
- public route readiness
- operator queue launch
- autonomous city dispatch
- ERC-8004 reputation receipts
- payment or production-infrastructure reverification
- exact GPS/raw metadata exposure
- worker-copyable municipal doctrine

## Files

- `mcp_server/city_ops/acontext_live_preflight.py`
- `mcp_server/city_ops/acontext_runtime_memory_preflight_rerun.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_runtime_memory_preflight_rerun.json`
- `mcp_server/tests/city_ops/test_acontext_live_preflight.py`
- `mcp_server/tests/city_ops/test_acontext_runtime_memory_preflight_rerun.py`

## Verification

Focused tests:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_live_preflight.py \
  mcp_server/tests/city_ops/test_acontext_runtime_memory_preflight_rerun.py
# 14 passed
```

## Next smallest proof

Complete local Acontext startup and verify both endpoints. Then rerun the read-only preflight, rebuild blocker delta/read surface/gate, and attempt exactly one live write/retrieve parity pass only if the rebuilt gate has empty blockers.
