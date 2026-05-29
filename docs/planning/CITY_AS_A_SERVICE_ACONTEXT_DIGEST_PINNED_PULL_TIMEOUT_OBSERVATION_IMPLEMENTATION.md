# City-as-a-Service — Acontext Digest-Pinned Pull Timeout Observation

## Summary

Implemented `mcp_server/city_ops/acontext_digest_pinned_pull_timeout_observation.py` as the next truth-producing AAS runtime prerequisite artifact after the May 29 cache-path resolution plan.

The runtime proof did two bounded things:

1. Used the anonymous GHCR registry API to lock the first required Acontext image to exact OCI digests.
2. Attempted one digest-pinned Docker pull for the linux/arm64 manifest.

Result: the registry manifest path is healthy and provenance is now exact, but Docker Desktop still did not cache the image within the bounded pull window.

## Evidence captured

- Source plan: `acontext_cache_path_resolution_plan.json`
- First required image: `ghcr.io/memodb-io/acontext-ui:latest`
- OCI index digest: `sha256:b303d1f1894bbe356e4f70483c06a7bfe9c38bcf46a5fff5de2d8826e87ef436`
- linux/arm64 manifest digest: `sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7`
- Config digest: `sha256:5a1be63a0fd630cef6fbffea574c6979b0c53920f0ab0f5af0b96c473754a9bc`
- Layers: `10`
- Layer byte budget: `75,482,880`
- Digest-pinned pull window: `240s`
- Pull result: timed out
- Image inspect after attempt: not present

Persisted fixture:

```text
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_digest_pinned_pull_timeout_observation.json
```

## Safe claim

```text
admin_acontext_digest_pinned_pull_timeout_observation_landed
```

## What this proves

- GHCR anonymous registry metadata is reachable for the first required Acontext image.
- The exact linux/arm64 manifest digest and layer budget are known.
- The next cache path can use digest-pinned provenance instead of tag-based guessing.
- Docker Desktop still fails to cache the first required image through a bounded digest-pinned pull.

## What this does not prove

This artifact does **not** prove or authorize:

- first required image cached locally
- all required images cached locally
- Compose startup
- Acontext API/dashboard health
- read-only preflight gate rebuilt empty
- live Acontext write/retrieve parity
- IRC runtime session-manager mutation
- cross-project autorouting
- customer copy/delivery/publication
- public/catalog/pricing route
- queue launch or dispatch
- ERC-8004 reputation or Worker Skill DNA
- payment/production reverification
- exact GPS/raw metadata release
- domain/emergency authority
- worker-copyable doctrine

## Next safe move

Do not repeat blind tag pulls. Use the locked digests as provenance for exactly one changed cache path:

1. trusted registry-client copy/load,
2. trusted preloaded image tar with matching digest,
3. registry mirror, or
4. Docker Desktop cache/network maintenance.

After that, rerun image inventory and stop unless `ghcr.io/memodb-io/acontext-ui` is actually present locally by digest or tag.

## Verification

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_acontext_digest_pinned_pull_timeout_observation.py
8 passed
```
