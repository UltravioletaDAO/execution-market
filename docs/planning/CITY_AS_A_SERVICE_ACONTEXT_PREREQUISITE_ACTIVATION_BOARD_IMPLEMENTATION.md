# City as a Service — Acontext Prerequisite Activation Board Implementation

> Date: 2026-05-16 00:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin proof only
> Status: landed as fail-closed local artifact + tests
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`

## Why this exists

The latest Acontext parity-attempt gate correctly blocks a live write/retrieve run until the SDK, API, and dashboard prerequisites are real. Tonight's setup probe found useful progress, but also a runner mismatch:

- Docker is available.
- The Acontext CLI exists locally.
- A local Docker Compose manifest exists under `~/clawd/infra/acontext`.
- A dedicated Acontext SDK virtualenv exists.
- The Python runtime used by the city-ops test/preflight path still cannot import `acontext`.
- The local Acontext API and dashboard are not reachable yet.
- A direct SDK install attempt into the active Homebrew Python failed because of a local `pyexpat` linkage issue.
- A Docker Compose startup attempt was made but did not complete within the dream window, so no API/dashboard readiness was claimed.

This slice captures that setup state without pretending it authorizes live runtime parity.

## Landed artifacts

- `mcp_server/city_ops/acontext_prerequisite_activation_board.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_prerequisite_activation_board.json`
- `mcp_server/tests/city_ops/test_acontext_prerequisite_activation_board.py`

Safe claim added:

```text
admin_acontext_prerequisite_activation_board_landed
```

## Current verdict

```text
activation_started_not_live_ready
```

## What the board is allowed to say

The board can say only that setup work has started and that some local assets are present:

1. Docker is available.
2. Acontext CLI is installed.
3. Acontext Compose manifest exists.
4. A dedicated SDK virtualenv exists.
5. The active runner still lacks SDK import readiness.
6. API/dashboard reachability is still blocked.

## Explicitly still blocked

The board does **not** authorize or prove:

- Acontext prerequisites fully cleared;
- read-only preflight rerun completed;
- live Acontext parity attempt authorized;
- live Acontext write or retrieval;
- Acontext sink readiness;
- runtime parity;
- live memory transport swap readiness;
- customer-visible AAS packaging;
- public/catalog routes;
- operator queue launch;
- autonomous city dispatch;
- ERC-8004 reputation;
- payment or production infrastructure health;
- exact GPS/raw metadata exposure;
- worker-copyable municipal doctrine.

## Next smallest proof

1. Finish local Acontext service startup until both read-only health probes respond.
2. Wire the active city-ops preflight/test runner to a Python runtime that can import `acontext`.
3. Rerun the read-only preflight.
4. Rebuild the blocker delta, read surface, gate, and activation board from the new preflight result.
5. Only if the rebuilt gate explicitly authorizes it, perform exactly one live write/retrieve parity attempt.

## Validation

Focused gate:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_prerequisite_activation_board.py \
  mcp_server/tests/city_ops/test_acontext_live_parity_attempt_readiness_gate.py
# 15 passed
```

Full city-ops suite:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 781 passed
```

Compile check:

```bash
/opt/homebrew/bin/python3.14 -m py_compile \
  mcp_server/city_ops/acontext_prerequisite_activation_board.py \
  mcp_server/tests/city_ops/test_acontext_prerequisite_activation_board.py
```
