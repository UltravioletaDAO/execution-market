# City as a Service — Acontext Required Image Extended Pull Timeout Observation

> Date: 2026-05-28 23:03 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin runtime-prerequisite extended pull timeout; not Compose startup; not live parity; not customer/public

## Why this exists

The May 28 22:11 required-image pull retry proved that Docker stayed available but the first required Acontext image was still missing after a bounded three-minute pull attempt. The next safe truth-producing step was one longer bounded retry plus a registry-manifest sanity check, not another route layer and not a Compose startup.

This slice verified that GHCR anonymous manifest fetches still succeed for the three Acontext-owned images and advertise `linux/arm64` manifests:

```text
ghcr.io/memodb-io/acontext-ui:latest
ghcr.io/memodb-io/acontext-api:latest
ghcr.io/memodb-io/acontext-core:latest
```

Then it attempted exactly one longer required-image pull:

```text
docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest
```

The pull remained silent and timed out after ~600 seconds. The image was still not present afterward. The only required image currently observed locally remains `pgvector/pgvector:pg16`. Local Acontext API/dashboard health checks remain unreachable.

## Landed files

```text
mcp_server/city_ops/acontext_required_image_extended_pull_timeout_observation.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_required_image_extended_pull_timeout_observation.json
mcp_server/tests/city_ops/test_acontext_required_image_extended_pull_timeout_observation.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_required_image_extended_pull_timeout_observation_landed
```

Meaning: Docker is available and GHCR manifests are reachable, but Docker Desktop still did not cache the first required Acontext image in a longer bounded pull window. This narrows the problem to the Docker pull/cache path; it does not close runtime readiness.

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

Do not keep repeating blind Docker pulls. The next useful move is to change the image-cache path: use a trusted preloaded image tar, registry mirror, Docker Desktop networking/cache reset, or a verified remote builder/cache that can export `ghcr.io/memodb-io/acontext-ui:latest` locally.

Only after the first image is present locally should the required-image inventory advance toward all-image presence, local Compose startup, API/dashboard health, read-only preflight rebuild, and finally one bounded live parity attempt if explicitly authorized by the rebuilt gate.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_required_image_extended_pull_timeout_observation.py \
  mcp_server/tests/city_ops/test_acontext_required_image_pull_retry_observation.py
# 18 passed

PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1469 passed
```
