# City-as-a-Service — Acontext ORAS OCI-Layout Cache Bridge

> Date: 2026-05-30 00:15 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: internal/admin observation; alternate trusted registry client installed; first required Acontext UI image loaded and tagged locally; remaining images, Compose, API/dashboard, and live parity still blocked

## Why this exists

`DREAM-PRIORITIES.md` remains the governing dream priority file: Execution Market AAS / City-as-a-Service only. The stale cron payload mentioned AutoJob, Frontier Academy, and KK v2; those lanes are explicitly stopped and were not worked on.

The previous Acontext slice installed `crane` and attempted a digest-pinned export/load path, but both `crane digest` and `crane pull` timed out without creating a tarball or local image. The next safe move was **not** to repeat blind Docker pulls or the same crane path. This slice tried a different trusted acquisition path: `oras copy --to-oci-layout`.

## Runtime observation

### Trusted tool installed

```text
oras 1.3.2+Homebrew
/opt/homebrew/bin/oras
installed via Homebrew formula oras
```

### Pinned image provenance preserved

- Image: `ghcr.io/memodb-io/acontext-ui:latest`
- Platform: `linux/arm64`
- OCI index digest: `sha256:b303d1f1894bbe356e4f70483c06a7bfe9c38bcf46a5fff5de2d8826e87ef436`
- linux/arm64 manifest digest: `sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7`
- Config digest: `sha256:5a1be63a0fd630cef6fbffea574c6979b0c53920f0ab0f5af0b96c473754a9bc`

### Bounded attempt result

`oras manifest fetch --platform linux/arm64 --format json ghcr.io/memodb-io/acontext-ui:latest` completed and resolved the expected manifest digest.

A direct `oras pull` completed but skipped image layers because they do not include `org.opencontainers.image.title`; ORAS explicitly recommended `oras copy --to-oci-layout`.

That alternate path worked:

```text
oras copy --platform linux/arm64 --no-tty --to-oci-layout \
  ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7 \
  /tmp/acontext-ui-oras-oci-layout-ef6bdb2b:acontext-ui-linux-arm64

# Result:
# 14 OCI-layout files
# 75,494,698 bytes
# Digest: sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7
```

The local OCI layout was tarred and loaded into Docker:

```text
docker load -i /tmp/acontext-ui-oras-oci-layout-ef6bdb2b.tar
# Loaded image: acontext-ui-linux-arm64:latest
```

Then the loaded image ID was tagged to the required Compose name:

```text
docker tag sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7 \
  ghcr.io/memodb-io/acontext-ui:latest
```

Post-attempt inventory:

```text
ghcr.io/memodb-io/acontext-ui:latest -> present, arm64/linux, sha256:ef6b...
pgvector/pgvector:pg16 -> present
remaining required images -> absent
```

## Landed files

```text
mcp_server/city_ops/acontext_oras_oci_layout_cache_bridge.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_oras_oci_layout_cache_bridge.json
mcp_server/tests/city_ops/test_acontext_oras_oci_layout_cache_bridge.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_oras_oci_layout_cache_bridge_landed
```

Meaning: a different trusted registry acquisition path successfully materialized the first required Acontext UI image into Docker and tagged it with the required Compose image name.

## Still blocked

Do **not** claim any of the following:

- all required Acontext images present
- Acontext Compose started
- local Acontext API healthy
- local Acontext dashboard healthy
- readiness gate rebuilt with empty blockers
- one live Acontext parity attempt authorized
- live Acontext write/retrieval performed
- live Acontext runtime parity
- IRC runtime session manager changes
- cross-project autorouting
- customer copy/delivery/publication readiness
- public catalog/route/pricing readiness
- operator queue launch/autonomous dispatch readiness
- ERC-8004 reputation or Worker Skill DNA readiness
- payment or production reverification
- exact GPS/raw metadata release
- worker-copyable AAS or municipal doctrine

## Next safe step

Use the now-proven ORAS OCI-layout method only for the **remaining missing images**, then rerun local image inventory.

Stop before Compose/API/dashboard/live-parity checks while any required image remains missing.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_acontext_oras_oci_layout_cache_bridge.py
# 10 passed
```
