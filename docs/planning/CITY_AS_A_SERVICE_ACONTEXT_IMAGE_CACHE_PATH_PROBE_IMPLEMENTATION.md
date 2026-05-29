# City as a Service — Acontext Image-Cache Path Probe

> Date: 2026-05-29 00:05 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: internal/admin runtime-prerequisite cache-path probe; not tooling install; not Compose startup; not live parity; not customer/public

## Why this exists

The May 28 extended required-image pull proved that Docker stayed available and GHCR manifests for the Acontext-owned images were reachable, but Docker Desktop still did not cache the first required image after a longer bounded pull. Repeating blind `docker pull` attempts is no longer useful evidence.

This slice changes the probe from “try the same pull again” to “inspect which cache/export paths are actually available locally” before any Compose or parity work.

Observed commands, sanitized:

```text
command -v oras crane skopeo regctl nerdctl
docker buildx imagetools inspect ghcr.io/memodb-io/acontext-ui:latest
docker image inspect ghcr.io/memodb-io/acontext-ui:latest
docker image inspect pgvector/pgvector:pg16
curl --max-time 2 http://localhost:8029/api/v1/health
curl --max-time 2 -I http://localhost:3000
```

Result:

- Docker daemon remained available on `desktop-linux`.
- The first required image `ghcr.io/memodb-io/acontext-ui:latest` remained absent.
- The only observed required image still present was `pgvector/pgvector:pg16`.
- Local alternate registry/cache tools were absent: `oras`, `crane`, `skopeo`, `regctl`, and `nerdctl`.
- `docker buildx imagetools inspect ghcr.io/memodb-io/acontext-ui:latest` timed out in a bounded 60-second window without metadata output.
- No registry tool was installed, no mirror was configured, no preloaded tar was obtained, no Docker Desktop cache/network reset was performed, and no remote builder/cache export was available.
- Local Acontext API/dashboard checks remained unreachable.

## Landed files

```text
mcp_server/city_ops/acontext_image_cache_path_probe.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_image_cache_path_probe.json
mcp_server/tests/city_ops/test_acontext_image_cache_path_probe.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_image_cache_path_probe_landed
```

Meaning: the next changed-path runtime prerequisite was probed, and it is still blocked because no local alternate cache/export tooling is available, Buildx metadata inspection timed out, and the first required Acontext image is still missing.

## Still blocked

- registry tooling installed/available
- registry mirror configured
- trusted preloaded image tar obtained
- Docker Desktop cache/network reset completed
- remote builder/cache export completed
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

Pick exactly one changed cache path before the next runtime probe:

1. Install/use one trusted registry client (`crane`, `oras`, `skopeo`, or `regctl`) and attempt a bounded image export/load path.
2. Obtain a trusted preloaded tar for `ghcr.io/memodb-io/acontext-ui:latest` and `docker load` it.
3. Configure a trusted registry mirror or verified remote builder/cache export.
4. Reset Docker Desktop networking/cache only as an explicit operator-approved maintenance step.

Only after `ghcr.io/memodb-io/acontext-ui:latest` is present locally should the ladder advance to all-image inventory, Compose startup, API/dashboard health, read-only preflight rebuild, and then exactly one bounded live parity attempt if the rebuilt gate authorizes it.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_image_cache_path_probe.py \
  mcp_server/tests/city_ops/test_acontext_required_image_extended_pull_timeout_observation.py
# 20 passed
```
