# City as a Service — AAS Claim Quarantine Internal/Admin Route

> Date: 2026-05-22 00:30 America/New_York  
> Status: internal/admin route mount smoke landed; not public; not customer-facing; not dispatch; not runtime parity  
> Safe claim: `internal_admin_aas_claim_quarantine_route_mount_smoke_landed` only

## What landed

The May 21 handoff named the next safest product fork: mount or preflight the existing `aas_claim_quarantine_read_surface.json` without turning it into a customer/public surface.

This slice adds exactly that:

- `mcp_server/city_ops/aas_claim_quarantine_admin_route.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_claim_quarantine_route_mount_manifest.json`
- `mcp_server/tests/city_ops/test_aas_claim_quarantine_admin_route.py`
- exports through `mcp_server/city_ops/__init__.py`
- FastAPI app mount in `mcp_server/main.py`

The route is:

```text
GET /internal/admin/city-ops/aas-claim-quarantine
```

It requires the existing internal admin key boundary and returns the persisted `aas_claim_quarantine_read_surface.json` payload as-is after fail-closed guards.

## Why this matters

The claim quarantine surface is useful only if it can be inspected consistently by operators without copy/paste drift. This route makes the quarantine board addressable as an internal/admin read endpoint while preserving the central safety rule:

> mounted internal route ≠ public route ≠ customer delivery ≠ launch readiness.

## Guardrails preserved

The route and mount manifest explicitly keep these false/blocked:

- public or catalog route readiness
- customer copy, delivery, and publication
- public pricing or customer quote readiness
- controlled pilot or operator queue launch
- dispatch routing / dispatch automation
- ERC-8004 reputation receipts
- worker Skill DNA claims
- live Acontext / runtime parity
- payment or production reverification
- exact GPS/raw metadata release
- domain/legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability authority
- worker-copyable AAS doctrine

## Manifest contract

`aas_claim_quarantine_route_mount_manifest.json` proves only:

- the route exists in a FastAPI app after `include_router(router)`;
- it is `GET` only;
- it is under `/internal/admin/`;
- it depends on `verify_internal_admin_key`;
- it reads only `aas_claim_quarantine_read_surface.json`;
- response semantics remain pass-through.

It does **not** prove or claim any broader product readiness.

## Verification

Focused route tests:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_claim_quarantine_admin_route.py
12 passed
```

Related route/read-surface regression:

```text
.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_claim_quarantine_read_surface.py \
  mcp_server/tests/city_ops/test_aas_claim_quarantine_admin_route.py \
  mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py
47 passed
```

Full city-ops suite:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
1070 passed
```

## Next smallest safe fork

Two safe forks remain:

1. **Operator-learning fork:** build a prevented-claim/regret panel over the quarantined launch claims.
2. **Route-hardening fork:** add a compact handoff packet for this route mount manifest so the next agent can continue without reopening raw context.

Do not use this route as a customer catalog, launch flag, dispatch signal, reputation trigger, runtime-memory claim, or worker instruction surface.
