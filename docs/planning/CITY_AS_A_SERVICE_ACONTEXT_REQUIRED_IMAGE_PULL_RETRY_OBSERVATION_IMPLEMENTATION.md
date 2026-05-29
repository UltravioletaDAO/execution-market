# City as a Service — Acontext Required Image Pull Retry Observation

> Date: 2026-05-28 22:11 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin runtime-prerequisite pull retry; not Compose startup; not live parity; not customer/public

## Why this exists

The Docker daemon recovery observation proved the first runtime prerequisite: Docker/Buildx are available locally. The next safe truth-producing step was not another admin route layer; it was a bounded pull/cache check for the first required Acontext image.

This slice attempted exactly one required image pull:

```text
docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest
```

The retry timed out after ~180 seconds, emitted no useful tail output, and the image was still not present afterward. The only required image currently observed locally remains `pgvector/pgvector:pg16`.

## Landed files

```text
mcp_server/city_ops/acontext_required_image_pull_retry_observation.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_required_image_pull_retry_observation.json
mcp_server/tests/city_ops/test_acontext_required_image_pull_retry_observation.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_required_image_pull_retry_observation_landed
```

Meaning: Docker stayed available and one bounded pull retry was attempted, but the first required Acontext image is still missing and the runtime gate remains blocked.

## Still blocked

- first required Acontext image cached locally
- all required Acontext images present
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

Resolve the GHCR/layer pull stall for `ghcr.io/memodb-io/acontext-ui:latest` or provide a trusted preloaded image cache. Only after the first image is present locally should the required-image inventory advance toward all-image presence, local Compose startup, API/dashboard health, read-only preflight rebuild, and finally one bounded live parity attempt if explicitly authorized by the rebuilt gate.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_required_image_pull_retry_observation.py \
  mcp_server/tests/city_ops/test_acontext_docker_daemon_recovery_observation.py
# 18 passed
```
