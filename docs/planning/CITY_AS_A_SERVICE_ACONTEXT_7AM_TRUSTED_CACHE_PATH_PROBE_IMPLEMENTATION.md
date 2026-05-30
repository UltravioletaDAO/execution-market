# City-as-a-Service — Acontext 7 AM Trusted Cache-Path Probe

> Date: 2026-05-29 07:04 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: internal/admin observation; no install; no blind pull; no export/load; no Compose; no API/dashboard/live parity claim

## Why this exists

The 6 AM final wrap selected Fork A: try exactly one changed, trusted registry-client/export-load cache path for the pinned `ghcr.io/memodb-io/acontext-ui` `linux/arm64` image, then rerun local image inventory.

This probe first checked whether an installed trusted export/load-capable client was available. It found no `crane`, `oras`, `skopeo`, or `regctl`. Docker Buildx/imagetools is installed, but this was treated as metadata-only for this purpose: it does not provide a bounded local export/load cache path for the pinned image without changing into another pull/build path, and the prior bounded imagetools metadata path had already timed out.

Because no export/load-capable trusted registry client was present, this slice stopped and recorded one bounded observation artifact. It did **not** repeat `docker pull ghcr.io/memodb-io/acontext-ui:latest`, did **not** repeat the digest-pinned Docker pull, and did **not** start Compose.

## Pinned image provenance preserved

- Image: `ghcr.io/memodb-io/acontext-ui:latest`
- Platform: `linux/arm64`
- OCI index digest: `sha256:b303d1f1894bbe356e4f70483c06a7bfe9c38bcf46a5fff5de2d8826e87ef436`
- linux/arm64 manifest digest: `sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7`
- Config digest: `sha256:5a1be63a0fd630cef6fbffea574c6979b0c53920f0ab0f5af0b96c473754a9bc`

## Commands run for the bounded probe

```bash
command -v crane oras skopeo regctl nerdctl docker
docker buildx version
docker context show
docker image inspect ghcr.io/memodb-io/acontext-ui:latest --format '{{.Id}} {{.Architecture}} {{.Os}}'
docker image inspect ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7 --format '{{.Id}} {{.Architecture}} {{.Os}}'
docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.CreatedSince}} {{.Size}}' | grep -E 'acontext|pgvector|seaweed|redis|rabbitmq|aws-cli|jaeger' || true
```

## Observation result

- Export/load-capable trusted registry clients present: none (`crane`, `oras`, `skopeo`, `regctl` absent).
- Docker Buildx/imagetools present: yes (`github.com/docker/buildx v0.30.1-desktop.1`), but not used as a local export/load cache path.
- Docker context: `desktop-linux`.
- First Acontext UI image by tag: absent.
- First Acontext UI image by pinned digest: absent.
- Required image inventory after probe: only `pgvector/pgvector:pg16` present.

## Landed files

```text
mcp_server/city_ops/acontext_7am_trusted_cache_path_probe.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_7am_trusted_cache_path_probe.json
mcp_server/tests/city_ops/test_acontext_7am_trusted_cache_path_probe.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_7am_trusted_cache_path_probe_landed
```

Meaning: an internal/admin bounded probe checked installed trusted export/load cache tooling and local image inventory, then stopped because no export/load-capable trusted client was present and the first required Acontext UI image remained absent.

## Still blocked

Preserve the blocked claims from the 6 AM final wrap. In particular, do not claim:

- first required Acontext image cached locally
- all required Acontext images present
- Acontext Compose started
- local Acontext API healthy
- local Acontext dashboard healthy
- live Acontext runtime parity
- Acontext sink/retrieval readiness
- customer copy/delivery/publication readiness
- public catalog/route/pricing readiness
- operator queue launch/autonomous dispatch readiness
- ERC-8004 reputation or Worker Skill DNA readiness
- payment or production reverification
- exact GPS/raw metadata release
- raw transcript, legal, regulator, emergency, repair, insurance, SLA, official report, or fault-liability authority
- worker-copyable AAS or municipal doctrine

## Next safe step

Install/use a real trusted export/load-capable registry client or provide a trusted preloaded image tar with matching digest provenance, then rerun local image inventory. Stop again unless `ghcr.io/memodb-io/acontext-ui:latest` (or the exact pinned digest) is actually present locally.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_acontext_7am_trusted_cache_path_probe.py
# 8 passed
```
