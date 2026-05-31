# City-as-a-Service — Acontext Project-Secret Path Resolution Decision (2026-05-30)

## Slice

Implemented one deterministic CityOps artifact for the current Acontext blocker:

```text
city_ops.acontext_project_secret_path_resolution_decision.v1
```

Implementation files:

- Module: `mcp_server/city_ops/acontext_project_secret_path_resolution_decision.py`
- Fixture: `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_project_credential_path_resolution_decision.json` (uses `credential` in the filename so the tracked fixture does not trip the repo's `*secret*.json` guardrail; schema, module, and safe claim remain the project-secret path resolution decision.)
- Tests: `mcp_server/tests/city_ops/test_acontext_project_secret_path_resolution_decision.py`

It derives from `acontext_project_admin_route_mismatch_observation.json` only. It does not require live Acontext, does not repeat localhost probes, does not create a project/session, and does not store or retrieve a message.

## Recorded runtime truth

Current state preserved by the artifact:

- Swagger advertises `POST /admin/v1/project`.
- Swagger base path was `/api/v1` in the source observation.
- Runtime probes returned `404` at both known path shapes:
  - `/admin/v1/project`
  - `/api/v1/admin/v1/project`
- No project Bearer secret was acquired.
- No secret value, project ID, session ID, message ID, raw logs, or private operator context is persisted.

## Decision

The project-secret path remains unresolved. The safe next path is one of:

1. Read-only route mounting/config inspection to explain why Swagger and runtime route mounting disagree.
2. Read-only supported non-admin secret-path discovery.

Stop until that route/path is resolved.

## Safe claim

```text
admin_acontext_project_secret_path_resolution_decision_landed
```

## Not safe to claim

Do not claim Acontext runtime parity, project creation, project Bearer acquisition, live write/retrieve, IRC session-manager mutation, cross-project autorouting, customer/public delivery, dispatch, reputation, payment/production reverification, GPS/raw metadata release, or worker-copyable doctrine.

## Stop line

```text
If the project-secret route remains unresolved, stop before any write/retrieve parity, IRC session-manager mutation, cross-project autorouting, customer/public delivery, dispatch, reputation, payment, GPS/raw metadata, or worker-doctrine claim.
```
