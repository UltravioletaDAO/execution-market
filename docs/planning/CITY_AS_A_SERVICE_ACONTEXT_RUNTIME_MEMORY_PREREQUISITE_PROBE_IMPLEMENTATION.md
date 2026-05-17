# City-as-a-Service — Acontext runtime-memory prerequisite probe

Date: 2026-05-16 22:01 EDT

Status: internal/admin prerequisite evidence only.

## What landed

- `mcp_server/city_ops/acontext_runtime_memory_prerequisite_probe.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_runtime_memory_prerequisite_probe.json`
- `mcp_server/tests/city_ops/test_acontext_runtime_memory_prerequisite_probe.py`

Safe claim added:

```text
admin_acontext_runtime_memory_prerequisite_probe_landed
```

## What was checked

Local-only Acontext readiness was rechecked without publishing externally:

- Docker daemon and Docker Compose are available.
- Compose manifest and env file are present in `~/clawd/infra/acontext`.
- The dedicated `~/clawd/.venv-acontext` SDK venv imports `acontext==0.1.13`.
- The default active runner still cannot import `acontext`.
- `acontext` CLI is not on PATH, and `python -m acontext` is not a CLI entrypoint.
- `docker compose pull` was given a longer window but did not complete; only `pgvector/pgvector:pg16` was observed locally afterward.
- A separate `docker pull redis:7.4` timed out silently after 180 seconds.
- Compose services did not start.
- `http://localhost:8029/api/v1` and `http://localhost:3000` remain unreachable.

## What this does **not** claim

This is not a live runtime-memory proof. It does not authorize or claim:

- live Acontext write/retrieve parity;
- Acontext sink readiness;
- runtime parity;
- customer/public packaging, delivery, routes, queue launch, or dispatch;
- ERC-8004 reputation;
- payment or production infrastructure reverification;
- exact GPS/raw metadata exposure;
- worker-copyable municipal doctrine.

## Remaining blockers

```text
acontext_cli_not_on_path
default_active_runner_acontext_import_missing
compose_image_pull_not_completed
acontext_compose_services_not_started
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
readiness_gate_not_rebuilt_empty
```

## Next safe action

Resolve the Docker pull hang or pre-pull all compose images, start local Acontext services, verify localhost API/dashboard, then rerun the read-only preflight and rebuild the blocker/gate chain. Attempt exactly one live write/retrieve parity pass only if the rebuilt gate has empty blockers and explicitly authorizes it.
