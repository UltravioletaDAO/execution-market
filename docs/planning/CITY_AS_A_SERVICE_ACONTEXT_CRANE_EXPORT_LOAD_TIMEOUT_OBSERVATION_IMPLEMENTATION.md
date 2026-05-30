# City-as-a-Service — Acontext Crane Export/Load Timeout Observation

> Date: 2026-05-29 23:14 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin observation; trusted registry client installed; bounded digest-pinned pull attempted; no image tar, no Docker load, no Compose, no API/dashboard/live parity claim

## Why this exists

`DREAM-PRIORITIES.md` remains the governing dream priority file: Execution Market AAS / City-as-a-Service only. The stale cron payload still mentioned AutoJob, Frontier Academy, and KK v2; those lanes are explicitly stopped and were not worked on.

The previous Acontext fork selected one meaningful unblocker: use a trusted export/load-capable registry client instead of repeating blind Docker pulls. The 7 AM probe found no such tool installed. This slice installed `crane` and tried the changed cache path once, with bounded timeouts.

## Runtime observation

### Trusted tool installed

```text
crane 0.21.6
/opt/homebrew/bin/crane
installed via Homebrew formula crane
```

### Pinned image provenance preserved

- Image: `ghcr.io/memodb-io/acontext-ui:latest`
- Platform: `linux/arm64`
- OCI index digest: `sha256:b303d1f1894bbe356e4f70483c06a7bfe9c38bcf46a5fff5de2d8826e87ef436`
- linux/arm64 manifest digest: `sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7`
- Config digest: `sha256:5a1be63a0fd630cef6fbffea574c6979b0c53920f0ab0f5af0b96c473754a9bc`

### Bounded attempt result

Two subprocess-timeout wrappers were used so the run would not hang indefinitely:

```text
crane digest --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest
# timed out after 90s, no stdout/stderr

crane pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui@sha256:ef6bdb2b91eefe22673a57e9fe6a936312c0ba91d58ed86332e9dd93b678c6a7 /tmp/acontext-ui-linux-arm64-ef6bdb2b.tar
# timed out after 180s, no stdout/stderr, tar not created
```

Post-attempt inventory:

```text
ghcr.io/memodb-io/acontext-ui:latest -> absent
ghcr.io/memodb-io/acontext-ui@sha256:ef6b...c6a7 -> absent
```

## Landed files

```text
mcp_server/city_ops/acontext_crane_export_load_timeout_observation.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_crane_export_load_timeout_observation.json
mcp_server/tests/city_ops/test_acontext_crane_export_load_timeout_observation.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_crane_export_load_timeout_observation_landed
```

Meaning: a trusted registry client is now installed, and a bounded digest-pinned crane export/load attempt was made, but it timed out without creating a tarball or caching/loading the first required Acontext image.

## Still blocked

Do **not** claim any of the following:

- first required Acontext image cached locally
- all required Acontext images present
- image tar / OCI layout created
- Docker image load completed
- Acontext Compose started
- local Acontext API healthy
- local Acontext dashboard healthy
- live Acontext runtime parity
- Acontext sink/retrieval readiness
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

Do not repeat blind Docker pulls or the same crane path. The next meaningful fork is a **different acquisition path**:

1. verified preloaded image tar / OCI layout with matching digest provenance;
2. alternate trusted mirror/cache already known to contain the pinned artifact; or
3. network/registry fix, then one bounded crane rerun and local inventory check.

Stop again unless the exact first required image is present locally by tag or pinned digest.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_acontext_crane_export_load_timeout_observation.py
# 8 passed
```
