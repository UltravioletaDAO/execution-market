# City as a Service — Internal/Admin Operator Consumer Implementation

> Status: 00:00 dream implementation note
> Scope: Execution Market AAS / City-as-a-Service only
> Related source: `CITY_AS_A_SERVICE_INTERNAL_ADMIN_DECISION_SUPPORT_ROUTE_IMPLEMENTATION.md`

## What landed

The previous route slice made `GET /internal/admin/city-ops/decision-support-matrix` authenticated and pass-through: the route returns the persisted `decision_support_matrix_card.json` payload as-is after internal/admin auth and conservative guards.

This slice adds the next safe consumer layer without turning it into a public UI or polished console.

Code changes:

- `mcp_server/city_ops/decision_support_matrix_operator_consumer.py`
  - builds a deterministic thin operator/admin consumer artifact from the internal/admin route payload contract
  - consumes only `GET /internal/admin/city-ops/decision-support-matrix`
  - records a stable digest of the source route payload so stale consumer artifacts fail closed
  - passes through `axis_cards`, `claim_cards`, `success_metrics`, `readiness`, `recommended_next_action`, `next_smallest_proof`, and verdict fields without semantic reinterpretation
  - adds only one safe claim: `decision_support_matrix_operator_consumer_landed`
  - keeps public/customer/worker/dispatch/live-Acontext/memory/reputation/GPS/worker-doctrine access flags false
  - keeps operator UI, polished console, public route, customer catalog/copy, dispatch, live Acontext, runtime parity, ERC-8004 reputation, worker Skill DNA, legal/regulator, GPS/metadata, and worker-copyable doctrine readiness false
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_matrix_operator_consumer.json`
  - persisted deterministic consumer artifact for the current proof block
- `mcp_server/tests/city_ops/test_decision_support_matrix_operator_consumer.py`
  - proves the consumer reads only the internal/admin route payload contract
  - proves pass-through sections match the source card exactly
  - proves safe and blocked claims stay adjacent and non-overlapping
  - proves external readiness/access flags remain false
  - proves an authenticated in-process route response can feed the consumer builder directly
  - proves persisted consumer artifacts load and fail on stale source digest or pass-through drift
  - proves promoted route payloads fail closed before a consumer is built
- `mcp_server/city_ops/__init__.py`
  - exports the builder, loader, and writer for the operator consumer artifact

## Safe to claim

- `decision_support_matrix_operator_consumer_landed`
- an internal/admin-only consumer artifact now exists over the authenticated matrix route payload
- the consumer preserves the route card as the sole source of truth
- source payload digest drift is detected on load
- pass-through section drift is detected on load
- safe and blocked claims remain adjacent

## Still blocked / not safe to claim

- public route readiness
- customer-visible catalog readiness
- customer copy readiness
- polished operator console readiness
- broad operator UI readiness
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
  mcp_server/city_ops/decision_support_matrix_operator_consumer.py \
  mcp_server/tests/city_ops/test_decision_support_matrix_operator_consumer.py

PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_decision_support_matrix_operator_consumer.py -q

PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Results:

- focused operator-consumer gate: `9 passed, 2 warnings`
- full city-ops gate: `214 passed, 2 warnings`

## Next smallest safe step

Continue with a narrow internal/admin display adapter that consumes only `decision_support_matrix_operator_consumer.json` and refuses to register any public/customer/dispatch surface.

Do not add customer copy, public catalog, dispatch routing, live Acontext writes, ERC-8004 reputation updates, worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or worker-copyable doctrine in the next slice.
