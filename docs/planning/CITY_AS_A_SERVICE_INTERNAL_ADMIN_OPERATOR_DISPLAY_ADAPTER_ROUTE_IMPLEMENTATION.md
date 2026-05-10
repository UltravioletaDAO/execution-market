# City as a Service — Internal/Admin Operator Display Adapter Route Implementation

> Status: 02:00 dream implementation note  
> Scope: Execution Market AAS / City-as-a-Service only  
> Related source: `CITY_AS_A_SERVICE_INTERNAL_ADMIN_OPERATOR_DISPLAY_ADAPTER_IMPLEMENTATION.md`

## What landed

The previous slice created `decision_support_matrix_operator_display_adapter.json`: a deterministic, data-only internal/admin display adapter over the operator consumer artifact.

This slice wires that adapter to a real authenticated internal/admin route while preserving the same proof boundaries. The route is intentionally small: it authenticates, loads the persisted adapter artifact, validates that it is still conservative, and returns the payload as-is.

Code changes:

- `mcp_server/city_ops/decision_support_matrix_admin_route.py`
  - adds `GET /internal/admin/city-ops/decision-support-matrix/operator-display-adapter`
  - reuses the existing internal admin auth boundary (`verify_internal_admin_key`)
  - returns `decision_support_matrix_operator_display_adapter.json` as-is after route-contract validation
  - adds a route-level preflight writer for the mounted adapter route
  - keeps public/customer/worker/dispatch/live-Acontext/memory/reputation/GPS/worker-doctrine access flags false
  - keeps network/public/customer/polished-console/operator-UI/worker-visible/dispatch/live-Acontext/runtime/reputation/Skill-DNA/legal/GPS/worker-doctrine readiness false
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_matrix_operator_display_adapter_admin_route_preflight.json`
  - persisted route proof showing admin auth, internal path match, adapter payload parity, pass-through-only response semantics, and no external side effects
- `mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py`
  - proves the adapter route requires admin auth
  - proves bearer and `X-Admin-Key` auth work
  - proves the response equals the persisted adapter artifact exactly
  - proves safe/blocked cards remain adjacent
  - proves promoted readiness and access-policy drift fail closed
- `mcp_server/city_ops/__init__.py`
  - exports the adapter-route loader/preflight/writer helpers

## Safe to claim

- `internal_admin_decision_support_matrix_operator_display_adapter_route_landed`
- the persisted display adapter is available behind an authenticated internal/admin route
- route response parity is proven in-process against the persisted adapter payload
- route preflight proves admin auth, path match, pass-through-only semantics, and no external side effects

## Still blocked / not safe to claim

- public route readiness
- network route readiness outside the internal/admin proof boundary
- customer-visible catalog readiness
- customer copy readiness
- polished operator console readiness
- broad operator UI readiness
- worker-visible readiness
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
python3 -m py_compile \
  mcp_server/city_ops/decision_support_matrix_admin_route.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py

PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py -q
```

Results:

- focused internal/admin route gate: `22 passed, 2 warnings`

## Next smallest safe step

Keep the adapter route internal/admin-only and use it as a proof-preserving operator pickup surface. The next build should either:

1. add a tiny route-level smoke test in the app-level router include path, or
2. stop here and move back down the proof ladder toward live Acontext write/retrieve parity only when local prerequisites are clear.

Do not add customer copy, public catalog, dispatch routing, live Acontext writes, ERC-8004 reputation updates, worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or worker-copyable doctrine in the next slice.
