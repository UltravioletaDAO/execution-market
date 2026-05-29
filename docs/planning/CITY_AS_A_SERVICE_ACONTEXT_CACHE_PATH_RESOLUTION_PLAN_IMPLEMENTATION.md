# City as a Service — Acontext Cache-Path Resolution Plan

> Date: 2026-05-29 01:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin cache-path resolution plan; not registry tooling install; not cache execution; not Compose startup; not live parity; not customer/public

## Why this exists

The 00:05 image-cache path probe showed that repeating blind Docker pulls is no longer useful evidence:

- Docker remained available on the local `desktop-linux` context.
- The first required Acontext image, `ghcr.io/memodb-io/acontext-ui:latest`, remained absent.
- The only observed required image present locally remained `pgvector/pgvector:pg16`.
- Alternate registry/cache tools were not locally available: `oras`, `crane`, `skopeo`, `regctl`, and `nerdctl`.
- `docker buildx imagetools inspect ghcr.io/memodb-io/acontext-ui:latest` timed out in a bounded 60-second window without metadata output.
- Local Acontext API/dashboard checks stayed unreachable.

This slice converts that evidence into one selected next changed cache path without performing the change. The selected next path is:

```text
trusted_registry_client_export_load_path
```

Meaning: the next execution slice should use exactly one trusted registry client or equivalent trusted cache source to attempt a bounded inspect/export/load path, then stop and rerun image inventory. It should not start Compose unless all required images are present locally.

## Landed files

```text
mcp_server/city_ops/acontext_cache_path_resolution_plan.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_cache_path_resolution_plan.json
mcp_server/tests/city_ops/test_acontext_cache_path_resolution_plan.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_cache_path_resolution_plan_landed
```

Meaning: an internal/admin plan selected the least destructive changed cache path after the image-cache probe. It did not install tooling, use tooling, load images, start services, rebuild readiness, or authorize live Acontext parity.

## Ranked cache paths

1. **Trusted registry client export/load path** — recommended next changed path, not executed here. Candidate clients: `crane`, `oras`, `skopeo`, or `regctl`.
2. **Trusted preloaded image tar** — acceptable only with explicit provenance and digest verification.
3. **Verified remote builder/cache export** — acceptable only if an existing trusted builder/cache exists.
4. **Registry mirror configuration** — defer because it changes registry routing.
5. **Docker Desktop network/cache reset** — last resort operator maintenance because it can disrupt unrelated local containers.

## Still blocked

- registry tooling installed or used
- trusted preloaded image tar obtained
- registry mirror configured
- Docker Desktop cache/network maintenance performed
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

Execute exactly one bounded changed cache path in a separate artifact:

```text
trusted_registry_client_export_load_path
```

The execution artifact must record:

1. the exact tool or trusted cache source used;
2. how it was obtained;
3. the required image list and `linux/arm64` platform target;
4. the output location if an image tar/cache artifact is produced;
5. local image inventory after the attempt;
6. explicit stop if `ghcr.io/memodb-io/acontext-ui:latest` is still absent.

Only after the first required image is present should the ladder advance to all-image inventory, then local Compose startup, then API/dashboard health, then read-only preflight rebuild, and finally exactly one bounded live write/retrieve parity attempt if the rebuilt gate authorizes it.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_cache_path_resolution_plan.py \
  mcp_server/tests/city_ops/test_acontext_image_cache_path_probe.py
# 19 passed

PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1488 passed
```
