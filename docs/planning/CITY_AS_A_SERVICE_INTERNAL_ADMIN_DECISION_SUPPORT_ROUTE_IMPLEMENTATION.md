# City as a Service — Internal/Admin Decision-Support Route Implementation

> Status: 23:00 dream kickoff implementation note
> Scope: Execution Market AAS / City-as-a-Service only
> Related source: `CITY_AS_A_SERVICE_MORNING_BRIEF_2026_05_09.md`

## What landed

The fail-closed preflight said the next safe step was a real authenticated internal/admin route only if an admin auth boundary was clear. The existing `/api/v1/admin` boundary was already implemented as `verify_admin_key`; this slice extracts that dependency into a shared module and uses it for the CaaS internal/admin route.

Code changes:

- `mcp_server/admin_auth.py`
  - shared `verify_admin_key()` dependency extracted from `mcp_server/api/admin.py`
  - preserves accepted auth sources for legacy admin APIs: `Authorization: Bearer`, `X-Admin-Key`, and legacy `admin_key` query param
  - adds `verify_internal_admin_key()` for internal/admin routes, rejecting query-param secrets
  - preserves constant-time comparison and `EM_ADMIN_KEY` fail-closed behavior
- `mcp_server/api/admin.py`
  - imports the shared admin auth dependency instead of defining a separate copy
- `mcp_server/city_ops/decision_support_matrix_admin_route.py`
  - registers `GET /internal/admin/city-ops/decision-support-matrix`
  - authenticates with the shared internal admin key boundary
  - rejects `admin_key` query-param auth for this internal route
  - returns the persisted `decision_support_matrix_card.json` payload as-is
  - validates the card remains read-only, internal/admin-only, pass-through-only, and conservative before returning it
  - refuses promoted readiness, public/customer/worker/dispatch/live-sink/reputation/GPS/worker-doctrine drift
  - builds a route-level mount-ready preflight proof from the actual router/dependency metadata
- `mcp_server/main.py`
  - mounts the internal/admin CaaS router
- `mcp_server/city_ops/__init__.py`
  - exports `load_internal_admin_decision_support_matrix_card()`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_matrix_admin_route_preflight.json`
  - persisted route-level preflight proof for the actual mounted internal/admin route
- `mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py`
  - proves auth is required
  - proves unconfigured admin auth fails closed
  - proves `X-Admin-Key` and bearer auth both work
  - proves wrong keys, invalid bearer format, and query-param auth are rejected
  - proves route response equals the persisted card payload exactly
  - proves safe/blocked claim cards remain adjacent
  - proves promoted readiness and access drift are rejected

## Safe to claim

- `internal_admin_decision_support_matrix_route_landed`
- the route-level preflight proof is mount-ready for internal/admin only
- the decision-support matrix card now has an authenticated internal/admin GET route
- the route response is pass-through: persisted card payload in, identical JSON response out
- the route uses the same admin key material as the existing admin API while refusing query-param auth on the internal/admin path
- the route keeps public/customer/worker/dispatch/live-sink/reputation/GPS/worker-doctrine flags false

## Still blocked / not safe to claim

- public route readiness
- customer-visible catalog readiness
- customer copy readiness
- polished operator console readiness
- dispatch routing or dispatch automation readiness
- live Acontext readiness / Acontext sink readiness
- runtime parity
- ERC-8004 reputation readiness
- worker Skill DNA readiness
- legal sufficiency or regulator acceptance
- exact GPS/metadata exposure
- worker-copyable municipal doctrine

## Verification

Passed:

```bash
python3 -m py_compile mcp_server/admin_auth.py mcp_server/api/admin.py mcp_server/city_ops/decision_support_matrix_admin_route.py mcp_server/city_ops/decision_support_matrix_route_preflight.py mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py mcp_server/tests/city_ops/test_decision_support_matrix_route_preflight.py mcp_server/tests/test_admin_auth.py
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py mcp_server/tests/city_ops/test_decision_support_matrix_route_preflight.py mcp_server/tests/test_admin_auth.py -q
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Results:

- focused route/preflight/shared-auth gate: `26 passed, 2 warnings`
- full city-ops gate: `205 passed, 2 warnings`

The legacy admin auth focused tests were updated to import the shared `mcp_server.admin_auth` dependency directly, avoiding unrelated API package side effects while still proving bearer, `X-Admin-Key`, legacy query fallback for `/api/v1/admin`, fail-closed config, and actor capture behavior.

## Next smallest safe step

Wire a thin operator/admin consumer to this internal route only if it keeps the persisted card payload as the sole source and preserves the same blocked claims.

Do not add customer copy, public catalog, dispatch routing, live Acontext writes, ERC-8004 reputation updates, worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or worker-copyable doctrine in the next slice.
