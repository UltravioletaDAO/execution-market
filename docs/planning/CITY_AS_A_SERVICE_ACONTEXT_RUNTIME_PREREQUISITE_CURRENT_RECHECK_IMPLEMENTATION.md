# City-as-a-Service — Acontext Runtime Prerequisite Current Recheck Implementation

> Date: 2026-06-04 00:05 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only.
> Status: internal/admin read-only prerequisite recheck; no operator answer, no approval, no runtime mutation, no customer/public exposure.

## Why this slice exists

`DREAM-PRIORITIES.md` keeps dream work limited to Execution Market AAS / City-as-a-Service and explicitly blocks AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2. The June 3 stack already concluded that no more no-answer product/runtime wrappers should be added without a real operator answer.

The one useful truth-producing move still available was a current, read-only Acontext runtime prerequisite recheck. It answers only whether the local runtime prerequisites can be freshly reverified now.

## Current read-only facts

Commands observed, without starting services or mutating runtime state:

```bash
docker context ls
docker info --format 'ServerVersion={{.ServerVersion}} OperatingSystem={{.OperatingSystem}} Architecture={{.Architecture}} Driver={{.Driver}}'
docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.CreatedSince}} {{.Size}}' | grep required Acontext images
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}' | grep Acontext services
curl --max-time 2 http://localhost:8029/api/v1/health
curl --max-time 2 http://localhost:8089/health
curl --max-time 2 http://localhost:3000
```

Observed result:

- Docker active context remains `desktop-linux`.
- Docker daemon is not reachable through the user Docker socket.
- Current required image inventory was not checkable.
- Current container inventory was not checkable.
- Local Acontext API/core/UI health endpoints refused connection.
- No Compose startup, Docker pull/cache, project creation, session creation, live write, live retrieval, runtime adapter registration, or IRC/session-manager mutation was performed.

## Implementation

New deterministic artifact builder:

- `mcp_server/city_ops/acontext_runtime_prerequisite_current_recheck.py`

New persisted fixture:

- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_runtime_prerequisite_current_recheck.json`

New tests:

- `mcp_server/tests/city_ops/test_acontext_runtime_prerequisite_current_recheck.py`

Safe claim:

```text
admin_acontext_runtime_prerequisite_current_recheck_landed
```

Meaning only: a current read-only prerequisite check confirmed that local Docker/Acontext runtime reverification is blocked by Docker daemon unreachability, while preserving the no-answer hold state.

## Still blocked

This slice does not authorize or claim:

```text
operator answer recording
operator approval recording
runtime-memory answer record authorization
Docker daemon repair
current image inventory verification
current container inventory verification
Compose startup
current Compose health
current Acontext API/core/UI health
Acontext project/session creation
live Acontext write
live Acontext retrieval
runtime parity
runtime adapter registration or enablement
IRC/session-manager mutation
cross-project autorouting
customer/public/worker surface
catalog/pricing/operator queue/dispatch
ERC-8004 reputation
Worker Skill DNA
payment or production readiness
exact GPS/raw metadata release
private-context release
domain/legal/emergency/repair/insurance/SLA authority
worker-copyable doctrine
stopped-project integration
```

## Verification

Focused gate:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_acontext_runtime_prerequisite_current_recheck.py
# 12 passed
```

## Next safe move

If no real operator answer exists: keep both lanes held or pause proof layering.

If runtime-memory work is explicitly selected later: first restore Docker daemon reachability, then rerun read-only image/container inventory. Only after a separate approval should Compose startup or live write/retrieve parity be attempted.
