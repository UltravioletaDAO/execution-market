# City as a Service — Acontext Docker Daemon Recovery Observation Implementation

> Date: 2026-05-28 07:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin runtime-prerequisite observation; not live parity; not customer/public

## Why this exists

The May 28 next-truth selector said the next valuable work was not another internal route layer. It selected `runtime_truth_prerequisite_activation`: prove Docker/Acontext prerequisites, rerun the read-only live preflight, and only then consider one bounded write/retrieve parity attempt if the gate explicitly allows it.

This 7 AM slice performed the first truth-producing prerequisite check. Docker Desktop was started locally and the Docker daemon/Buildx recovered. The observation then stopped before Compose startup or live Acontext mutation because required Acontext images/services were still absent and the API/dashboard were unreachable.

## Landed files

```text
mcp_server/city_ops/acontext_docker_daemon_recovery_observation.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_docker_daemon_recovery_observation.json
mcp_server/tests/city_ops/test_acontext_docker_daemon_recovery_observation.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## What the observation records

Observed at the 7 AM run:

- Docker context: `desktop-linux`.
- Docker daemon recovered after local Docker Desktop startup.
- Docker client/server: 29.1.3, server `linux/arm64`.
- Buildx builders: `default` and `desktop-linux` running with BuildKit `v0.26.2`.
- Image inventory was checked, but no Acontext-related local images were present.
- No Acontext containers were running.
- Local Acontext API `localhost:8029` remained unreachable.
- Local dashboard `localhost:3000` remained unreachable.
- Compose services were not started by this artifact.
- No live Acontext write or retrieval was performed.

## Safe claim added

```text
admin_acontext_docker_daemon_recovery_observation_landed
```

Meaning: the first runtime prerequisite gate has a fresh observation showing Docker/Buildx are available, while all later Acontext/runtime gates remain blocked.

## Still blocked

The observation deliberately keeps these blocked:

- required Acontext image inventory/pull/cache completion
- Acontext Compose service startup
- local API/dashboard health
- rebuilt empty readiness gate
- live write/retrieve authorization
- live Acontext write
- live Acontext retrieval
- runtime parity
- IRC runtime session manager changes
- cross-project autorouting
- customer copy/delivery/publication
- public/catalog routes
- pricing/customer quote
- queue launch/dispatch
- ERC-8004 reputation or Worker Skill DNA
- payment/production reverification
- exact GPS/raw metadata exposure
- domain/emergency authority claims
- worker-copyable doctrine

## Next safe step

1. Complete a trusted Acontext image inventory/pull/cache path while Docker is running.
2. Only after required images are present, start local Acontext Compose services.
3. Verify local API and dashboard health.
4. Rerun the read-only live preflight and rebuild blocker delta/read surface/gate.
5. Attempt exactly one bounded live write/retrieve parity pass only if the rebuilt gate has no blockers and explicitly authorizes it.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_docker_daemon_recovery_observation.py
# 9 passed
```
