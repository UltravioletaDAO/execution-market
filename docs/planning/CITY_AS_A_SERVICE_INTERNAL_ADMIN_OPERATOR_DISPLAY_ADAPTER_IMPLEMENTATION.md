# City as a Service — Internal/Admin Operator Display Adapter Implementation

> Status: 01:00 dream implementation note
> Scope: Execution Market AAS / City-as-a-Service only
> Related source: `CITY_AS_A_SERVICE_INTERNAL_ADMIN_OPERATOR_CONSUMER_IMPLEMENTATION.md`

## What landed

The previous slice created `decision_support_matrix_operator_consumer.json`: a deterministic, internal/admin-only consumer over the authenticated decision-support matrix route payload.

This slice adds the smallest safe display layer over that consumer artifact. It is **not** a UI, **not** a network route, **not** a polished console, **not** customer copy, and **not** dispatch automation. It is a data-only adapter that packages the existing consumer sections into deterministic display cards while preserving every safe/blocked claim boundary.

Code changes:

- `mcp_server/city_ops/decision_support_matrix_operator_display_adapter.py`
  - consumes only `decision_support_matrix_operator_consumer.json`
  - records a stable digest of the source consumer artifact so stale display artifacts fail closed
  - produces internal/admin display cards for source route, axis cards, safe claims, blocked claims, success metrics, readiness, and next action
  - passes through consumer sections without semantic reinterpretation
  - adds only one safe claim: `decision_support_matrix_operator_display_adapter_landed`
  - keeps network/public/customer/worker/dispatch/live-Acontext/memory/reputation/GPS/worker-doctrine access flags false
  - keeps operator UI, polished console, public route, customer catalog/copy, dispatch, live Acontext, runtime parity, ERC-8004 reputation, worker Skill DNA, legal/regulator, GPS/metadata, and worker-copyable doctrine readiness false
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_matrix_operator_display_adapter.json`
  - persisted deterministic display adapter artifact for the current proof block
- `mcp_server/tests/city_ops/test_decision_support_matrix_operator_display_adapter.py`
  - proves the adapter consumes only the persisted consumer artifact
  - proves safe and blocked claim cards remain adjacent and unsoftened
  - proves display cards pass through the source consumer sections
  - proves all external readiness/access flags remain false
  - proves persisted artifacts load and fail on stale source digest, card drift, or readiness promotion
  - proves consumer access drift is rejected before an adapter can be built
- `mcp_server/city_ops/__init__.py`
  - exports the builder, loader, and writer for the display adapter artifact

## Safe to claim

- `decision_support_matrix_operator_display_adapter_landed`
- a data-only internal/admin display adapter exists over the operator consumer artifact
- source consumer digest drift is detected on load
- display card drift is detected on load
- safe and blocked claims remain adjacent

## Still blocked / not safe to claim

- network route readiness
- public route readiness
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
  mcp_server/city_ops/decision_support_matrix_operator_display_adapter.py \
  mcp_server/tests/city_ops/test_decision_support_matrix_operator_display_adapter.py

PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_decision_support_matrix_operator_display_adapter.py -q
```

Results:

- focused operator-display-adapter gate: `10 passed, 2 warnings`
- full city-ops gate: `224 passed, 2 warnings`

## Next smallest safe step

If continuing, the next safe step is either:

1. keep this adapter as a local reviewed artifact and add only documentation/handoff, or
2. wire it to an authenticated internal/admin route that returns the persisted adapter payload as-is and proves response parity.

Do not add customer copy, public catalog, dispatch routing, live Acontext writes, ERC-8004 reputation updates, worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or worker-copyable doctrine in the next slice.
