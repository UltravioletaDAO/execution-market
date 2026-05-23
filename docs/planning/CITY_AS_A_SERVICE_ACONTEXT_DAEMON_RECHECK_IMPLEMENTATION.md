# City-as-a-Service — Acontext Daemon Recheck Implementation

> Date: 2026-05-23 02:00 dream continuation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin prerequisite evidence; no live Acontext parity claim

## Why this slice exists

The prior Acontext lane proved a different blocker: Docker/buildx had been available, but the GHCR image pull path stalled before the Acontext compose set could be cached and started.

At the May 23 02:00 recheck, the local state had changed: `docker context show` still reported `desktop-linux`, but Docker API calls could not connect to `~/.docker/run/docker.sock`, Buildx showed error status, image/container inventory could not be checked, and the local Acontext API/dashboard were still unreachable.

This slice records that current blocker without pretending it closes the runtime-memory gap.

## Landed artifacts

```text
mcp_server/city_ops/acontext_runtime_memory_daemon_recheck.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_runtime_memory_daemon_recheck.json
mcp_server/tests/city_ops/test_acontext_runtime_memory_daemon_recheck.py
```

Exported through:

```text
mcp_server/city_ops/__init__.py
```

Safe latest claim:

```text
admin_acontext_runtime_memory_daemon_recheck_landed
```

## What the artifact records

The recheck consumes only:

```text
acontext_docker_pull_path_diagnostic.json
```

It records a sanitized current observation:

- Docker context: `desktop-linux`
- Docker daemon/socket: unavailable
- Buildx builder status: error
- Required image inventory: not checkable while daemon is unavailable
- Acontext containers: not checkable/running
- Local API: unreachable
- Local dashboard: unreachable
- Compose services: not started
- Live Acontext write/retrieve: not performed
- Readiness gate: not rebuilt empty

## Claim boundaries preserved

This is **not** any of the following:

- Docker repair
- completed image inventory
- completed GHCR pull/cache path
- Compose startup
- local Acontext API/dashboard health
- empty readiness gate
- authorized live write/retrieve parity attempt
- runtime parity proof
- customer/public route, catalog, or queue launch
- dispatch or autonomous dispatch
- ERC-8004 reputation receipt
- payment or production-infrastructure reverification
- exact GPS/raw metadata release
- legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability claim
- worker-copyable doctrine

## Why it matters

Without this artifact, future operators might keep chasing the old “pull path stalls” blocker even when the current first failure is earlier: Docker daemon access itself is down. The new recheck makes the prerequisite order explicit:

1. restore Docker Desktop / user socket;
2. recheck required image inventory;
3. complete image pull/cache through a trusted path;
4. start local Compose;
5. healthcheck API/dashboard;
6. rebuild the read-only preflight and attempt gate;
7. perform exactly one live write/retrieve parity pass only if the rebuilt gate allows it.

## Verification

Focused gate:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_runtime_memory_daemon_recheck.py
# 10 passed
```

Full city-ops gate should remain green before broader promotion.
