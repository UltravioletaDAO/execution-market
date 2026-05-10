# City as a Service — Internal/Admin Route Mount Manifest Implementation

> Status: 2026-05-10 03:00 dream implementation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice adds the app-level smoke proof for the internal/admin decision-support routes without widening the surface area. The previous route preflights proved individual route contracts. This manifest proves the router can be included in a FastAPI app and still expose exactly the expected internal/admin GET routes with the shared admin-auth dependency and pass-through artifact semantics.

## Files changed

- `mcp_server/city_ops/decision_support_matrix_admin_route.py`
  - added `build_internal_admin_decision_support_matrix_route_mount_manifest()`
  - added `write_internal_admin_decision_support_matrix_route_mount_manifest()`
  - added route-table validation for both mounted internal/admin decision-support routes
- `mcp_server/city_ops/__init__.py`
  - exported the new manifest builder/writer
- `mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py`
  - added app-level include-router smoke coverage
  - added fail-closed coverage when the router is not included
  - added persisted-manifest coverage
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_matrix_route_mount_manifest.json`
  - persisted conservative proof artifact

## New safe claim

- `internal_admin_decision_support_matrix_route_mount_smoke_landed`

## What the manifest proves

The persisted manifest verifies:

- exactly two expected routes mount after `app.include_router(router)`:
  - `GET /internal/admin/city-ops/decision-support-matrix`
  - `GET /internal/admin/city-ops/decision-support-matrix/operator-display-adapter`
- both routes require `verify_internal_admin_key`
- both routes are GET-only
- both routes remain under `/internal/admin/`
- both routes return persisted proof artifacts as pass-through payloads
- safe claims and blocked claims stay adjacent in the resulting manifest

## Guardrails preserved

The manifest keeps these false:

- public/network route readiness
- customer-visible catalog readiness
- customer copy readiness
- polished operator console readiness
- broad operator UI readiness
- worker-visible readiness
- dispatch routing or automation readiness
- live Acontext readiness / Acontext sink readiness
- runtime parity
- ERC-8004 reputation readiness
- worker Skill DNA readiness
- legal/regulator readiness
- GPS/metadata exposure allowance
- worker-copyable municipal doctrine readiness

## Verification

```bash
python3 -m py_compile \
  mcp_server/city_ops/decision_support_matrix_admin_route.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_decision_support_matrix_admin_route.py -q
# 25 passed, 2 warnings
```

## Next smallest safe step

Run the full city-ops test gate, then stop route expansion unless there is a clear need for one more internal/admin proof artifact. The next product-significant step remains live Acontext write/retrieve parity only after local prerequisites are real. Until then, do not broaden into customer/public/dispatch/reputation/GPS/worker-doctrine surfaces.
