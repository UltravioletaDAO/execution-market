# City-as-a-Service — Acontext individual image-pull timeout probe

Date: 2026-05-17 00:02 EDT

Status: internal/admin prerequisite evidence only.

## What landed

- `mcp_server/city_ops/acontext_individual_image_pull_timeout_probe.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_individual_image_pull_timeout_probe.json`
- `mcp_server/tests/city_ops/test_acontext_individual_image_pull_timeout_probe.py`

Safe claim added:

```text
admin_acontext_individual_image_pull_timeout_probe_landed
```

## What was checked

The prior compose-level pull attempt left the Acontext image inventory incomplete. The next safe action was to test image pulls individually with bounded timeouts instead of starting services.

From `~/clawd/infra/acontext`, the first required image was attempted directly:

```text
docker pull ghcr.io/memodb-io/acontext-ui:latest
```

Result: no Docker progress lines were emitted before the 180-second timeout. The second image pull was started, then stopped deliberately after the first timeout to avoid turning the cron window into an unbounded image-pull loop.

Registry endpoint checks were also recorded:

- `https://ghcr.io/v2/` responded over HTTP.
- `https://registry-1.docker.io/v2/` responded over HTTP.

Those checks prove only registry endpoint reachability. They do **not** prove image availability, Docker daemon pull success, completed image inventory, service startup, or runtime parity.

The local required-image inventory still shows only:

```text
pgvector/pgvector:pg16
```

## What this does **not** claim

This does not improve runtime readiness. It does not authorize or claim:

- first required image pulled;
- all required images attempted individually;
- all required Acontext images present;
- Docker registry reachability as image-pull success;
- compose services started;
- localhost API/dashboard reachability;
- empty rebuilt readiness gate;
- live Acontext write/retrieve parity;
- customer/public AAS packaging, route readiness, queue launch, or dispatch;
- ERC-8004 reputation;
- payment or production infrastructure reverification;
- exact GPS/raw metadata exposure;
- worker-copyable doctrine.

## Remaining blockers

```text
first_individual_image_pull_timed_out_without_progress
all_required_images_not_attempted_individually
required_acontext_images_missing
acontext_compose_services_not_started
local_acontext_api_not_rechecked_reachable
local_acontext_dashboard_not_rechecked_reachable
readiness_gate_not_rebuilt_empty
```

## Next safe action

Diagnose why `docker pull ghcr.io/memodb-io/acontext-ui:latest` stalls without progress even though the GHCR registry endpoint responds. Capture only non-secret daemon/network/error detail. After the stall is explained, retry remaining image pulls with shorter bounded timeouts or a cache/mirror strategy.

Only after all nine images are present locally should compose services be started and health checked. A live write/retrieve parity attempt remains blocked until a read-only preflight and readiness gate rebuild return empty blockers.
