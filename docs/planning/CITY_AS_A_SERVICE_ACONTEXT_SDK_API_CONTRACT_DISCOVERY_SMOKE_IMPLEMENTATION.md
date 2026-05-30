# City-as-a-Service — Acontext SDK/API Contract-Discovery Smoke

**Date:** 2026-05-30 03:00 America/New_York  
**Scope:** Execution Market AAS / City-as-a-Service, internal/admin only  
**Safe claim:** `admin_acontext_sdk_api_contract_discovery_smoke_landed`

## What landed

The Acontext runtime prerequisite ladder advanced one safe rung after the remaining-images ORAS + Compose health observation.

New implementation files:

- `mcp_server/city_ops/acontext_sdk_api_contract_discovery_smoke.py`
- `mcp_server/tests/city_ops/test_acontext_sdk_api_contract_discovery_smoke.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_sdk_api_contract_discovery_smoke.json`

The artifact records a bounded, read-only API/SDK contract-discovery smoke against the now-running local Acontext stack.

## Observed facts

Local stack recheck:

- `http://127.0.0.1:8029/health` returned `200` with OK shape.
- `http://127.0.0.1:8029/swagger/index.html` returned `200`.
- `http://127.0.0.1:8029/swagger/doc.json` returned `200`.
- Swagger reports `basePath=/api/v1` and `52` paths.

Contract surface discovered:

- `/session` exposes read/create shape.
- `/session/{session_id}/messages` exposes read/write shape.
- `/session/{session_id}/events`, `/flush`, and `/token_counts` are visible.
- `/disk` and `/disk/{disk_id}/artifact` surfaces are visible.
- `/agent_skills` and `/learning_spaces` surfaces are visible.

SDK/auth state:

- Python package import for `acontext` in the execution-market venv still fails with `ModuleNotFoundError`.
- Project endpoints require Bearer auth.
- No-auth probes returned `401 Unauthorized`.
- A root API bearer token probe also returned `401 Unauthorized` for project endpoints.
- No token or secret value is recorded in the artifact.

## Explicit stop line

This artifact does **not**:

- create an Acontext project,
- obtain or persist a project secret,
- create an Acontext session,
- write a live Acontext message,
- retrieve a live Acontext message,
- prove runtime parity,
- change IRC runtime session management,
- enable cross-project autorouting,
- publish customer copy,
- create public/catalog/pricing readiness,
- launch queues or dispatch,
- attach ERC-8004 reputation,
- prove Worker Skill DNA,
- reverify payment/production,
- expose exact GPS/raw metadata/private context,
- grant authority claims,
- or create worker-copyable doctrine.

## Next safe step

The next artifact should be a separate controlled write/retrieve parity gate:

1. obtain or create exactly one local Acontext project Bearer secret without recording the value,
2. create one sanitized test session,
3. store one sanitized message/payload,
4. retrieve it,
5. prove identity/claim/readiness boundaries survive unchanged,
6. clean up or quarantine the test object if the API supports it.

Only after both the live write and live retrieval succeed should any artifact claim Acontext runtime parity.

## Verification

Focused test gate:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_acontext_sdk_api_contract_discovery_smoke.py
```

Result:

```text
6 passed
```
