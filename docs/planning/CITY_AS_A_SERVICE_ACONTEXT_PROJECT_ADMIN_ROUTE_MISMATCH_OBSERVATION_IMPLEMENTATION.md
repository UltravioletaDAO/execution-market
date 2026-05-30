# City as a Service — Acontext Project Admin Route Mismatch Observation

**Date:** 2026-05-30 04:00 America/New_York
**Scope:** Execution Market AAS / City-as-a-Service internal-admin runtime prerequisite proof
**Safe claim:** `admin_acontext_project_admin_route_mismatch_observation_landed`

## What landed

The Acontext runtime gate advanced one truth-producing rung after the 03:00 SDK/API contract-discovery smoke:

- `mcp_server/city_ops/acontext_project_admin_route_mismatch_observation.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_project_admin_route_mismatch_observation.json`
- `mcp_server/tests/city_ops/test_acontext_project_admin_route_mismatch_observation.py`
- export helpers in `mcp_server/city_ops/__init__.py`

The prior smoke proved the running local Acontext API and Swagger contract are reachable and that session/message routes require a project Bearer secret. This slice attempted the next controlled gate: create exactly one local project through the documented admin route, keep the returned secret in memory only, then use it for one sanitized write/retrieve parity test.

## Runtime truth observed

The gate did **not** reach live write/retrieve parity. It found a narrower blocker:

- Swagger is reachable at `http://127.0.0.1:8029/swagger/doc.json`.
- Swagger still advertises `POST /admin/v1/project`.
- The running local API returns `404 page not found` for both:
  - `POST /admin/v1/project`
  - `POST /api/v1/admin/v1/project`
- The local Postgres schema contains `projects`, `sessions`, and `messages`, but no secret values, project IDs, session IDs, message IDs, or raw logs were persisted.
- The root token was available to the local probe, but its value was never printed, logged, committed, or included in the fixture.

## What this does **not** claim

This is intentionally a mismatch observation, not a parity proof. It does not claim:

- Acontext project creation
- project Bearer secret acquisition or recording
- live session creation
- live message write
- live message retrieval
- runtime parity
- IRC runtime/session-manager mutation
- cross-project autorouting
- customer/public/catalog delivery
- pricing, queue launch, dispatch, reputation, Worker Skill DNA, or payment readiness
- GPS/raw metadata/private-context release
- authority claims or worker-copyable doctrine

## Why it matters

The active blocker moved from a broad “need project Bearer secret” to a precise route/registration mismatch: the Swagger contract advertises the admin project creation route, but the running API does not serve it at either plausible path. That is the next concrete fix before any safe Acontext write/retrieve parity attempt.

## Next safe step

Resolve why the local API advertises `/admin/v1/project` while returning 404, or identify the supported non-admin project-secret creation path. Only after that should a separate artifact run one sanitized create-session → store-message → retrieve-message parity smoke with cleanup/quarantine.
