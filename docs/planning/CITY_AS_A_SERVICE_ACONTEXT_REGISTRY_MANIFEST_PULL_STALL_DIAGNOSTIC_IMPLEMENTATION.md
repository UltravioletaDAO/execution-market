# City-as-a-Service — Acontext registry-manifest / pull-stall diagnostic

Date: 2026-05-17 01:02 EDT

Status: internal/admin prerequisite evidence only.

## What landed

- `mcp_server/city_ops/acontext_registry_manifest_pull_stall_diagnostic.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_registry_manifest_pull_stall_diagnostic.json`
- `mcp_server/tests/city_ops/test_acontext_registry_manifest_pull_stall_diagnostic.py`

Safe claim added:

```text
admin_acontext_registry_manifest_pull_stall_diagnostic_landed
```

## What was checked

The previous per-image probe showed `docker pull ghcr.io/memodb-io/acontext-ui:latest` timing out without progress. This diagnostic narrowed the blocker without promoting readiness:

- Docker Desktop / engine was reachable locally (`desktop-linux`, server arch `arm64`).
- GHCR and Docker Hub registry base endpoints responded.
- GHCR anonymous bearer-token manifest fetches succeeded for:
  - `ghcr.io/memodb-io/acontext-ui:latest`
  - `ghcr.io/memodb-io/acontext-api:latest`
  - `ghcr.io/memodb-io/acontext-core:latest`
- All three GHCR Acontext image indexes advertised `linux/arm64`.
- A bounded `docker --debug pull ghcr.io/memodb-io/acontext-ui:latest` still timed out after 45 seconds with no stdout/stderr progress.

Interpretation: the blocker is no longer “GHCR manifest missing” or “no arm64 image advertised.” It is still somewhere in the local Docker Desktop/containerd/layer-fetch path, network/proxy path, or pull execution path.

## What this does **not** claim

This does not authorize or claim:

- Docker pull success;
- first required image present;
- all required images attempted or present;
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

Inspect Docker Desktop/containerd pull-path diagnostics without capturing secrets. If the daemon path is understood, retry only the first GHCR UI image with a short bounded timeout and explicit `--platform linux/arm64` or a trusted cache/mirror strategy.

Only after all nine required images are present locally should compose services be started and health checked. A live write/retrieve parity attempt remains blocked until read-only preflight and readiness gate rebuild return empty blockers.
