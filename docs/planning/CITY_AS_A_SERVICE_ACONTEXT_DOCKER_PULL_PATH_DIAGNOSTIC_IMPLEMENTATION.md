# City-as-a-Service — Acontext Docker pull-path diagnostic

Date: 2026-05-17 02:05 EDT

Status: internal/admin prerequisite evidence only.

## What landed

- `mcp_server/city_ops/acontext_docker_pull_path_diagnostic.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_docker_pull_path_diagnostic.json`
- `mcp_server/tests/city_ops/test_acontext_docker_pull_path_diagnostic.py`

Safe claim added:

```text
admin_acontext_docker_pull_path_diagnostic_landed
```

## What was checked

The previous registry-manifest diagnostic showed that GHCR manifests are available and advertise `linux/arm64`, while Docker Desktop still timed out on the first Acontext image. This pass inspected the local Docker pull path without recording tokens, registry credentials, raw Docker logs, or private operator context.

Observed:

- Current Docker context is `desktop-linux`.
- Docker server is reachable locally: `29.1.3`, Linux, `aarch64`, `overlayfs`.
- Buildx/BuildKit is running and advertises `linux/arm64` support.
- A bounded explicit-platform retry was attempted:

```bash
docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest
# timed out after 60s with no stdout/stderr progress
```

Interpretation: Docker context availability, BuildKit health, and arm64 platform support are present but still do not translate into local layer-pull success for the first GHCR Acontext image. The blocker is now specifically in the Docker Desktop/containerd/network/layer-fetch path or requires a trusted image cache/mirror strategy.

## What this does **not** claim

This does not authorize or claim:

- first required image pulled;
- all required images present;
- compose service startup;
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
docker_pull_still_times_out_without_output
docker_layer_fetch_or_daemon_path_not_explained
required_acontext_images_missing
acontext_compose_services_not_started
local_acontext_api_not_rechecked_reachable
local_acontext_dashboard_not_rechecked_reachable
readiness_gate_not_rebuilt_empty
```

## Next safe action

Fix or bypass the Docker layer-pull path before any compose startup:

1. Resolve the Docker Desktop/network/containerd layer-fetch stall, or use a trusted pre-populated image cache/mirror.
2. Verify all nine required Acontext compose images are present locally.
3. Start compose only after image inventory is complete.
4. Healthcheck API and dashboard.
5. Rerun read-only preflight and rebuild the blocker/readiness gate.
6. Attempt exactly one live write/retrieve parity pass only if the rebuilt gate has empty blockers.

Until then, keep the Acontext runtime-memory lane blocked and internal/admin-only.
