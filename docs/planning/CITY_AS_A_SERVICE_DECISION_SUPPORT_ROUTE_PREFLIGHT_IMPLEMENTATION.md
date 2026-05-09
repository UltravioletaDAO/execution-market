# City as a Service — Decision Support Route Preflight Implementation

> Status: 05:00 pre-dawn implementation note  
> Scope: Execution Market AAS / City-as-a-Service only  
> Related source: `CITY_AS_A_SERVICE_MORNING_BRIEF_2026_05_09.md`

## What landed

The 04:00 handoff said the next smallest safe step was either a real authenticated internal/admin route for the decision-support matrix card, or a route-readiness preflight that fails closed until admin auth, card parity, and no-interpretation response rules are proven.

The safer preflight now exists.

Code changes:

- `mcp_server/city_ops/decision_support_matrix_route_preflight.py`
  - adds `build_decision_support_matrix_route_preflight()`
  - adds `write_decision_support_matrix_route_preflight_fixture()`
  - adds `load_decision_support_matrix_route_preflight()`
  - consumes only `decision_support_matrix_card.json`
  - defaults to blocked / not mount-ready
  - requires an admin auth boundary, path match, card payload parity, pass-through-only response semantics, and no external side effects before a route can be marked mount-ready
  - rejects promoted card readiness, public/external route drift, customer visibility, dispatch enablement, live Acontext writes, municipal-memory writes, reputation receipts, GPS/metadata exposure, and worker doctrine publication
- `mcp_server/city_ops/__init__.py`
  - exports the route-preflight builder/writer/loader
- `mcp_server/tests/city_ops/test_decision_support_matrix_route_preflight.py`
  - verifies card-only consumption
  - verifies default fail-closed readiness
  - verifies persisted fixture parity
  - verifies an injected all-good internal/admin probe can become mount-ready without public/customer/dispatch/live-sink claims
  - verifies promoted card readiness is refused
  - verifies persisted external route drift is rejected
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_matrix_route_preflight.json`
  - persisted deterministic route-preflight payload

## Route gate

The preflight does **not** register a route. It defines the gate for a future route.

A route can only be considered mount-ready when all of these are true:

1. `route_handler_registered=true`
2. `admin_auth_boundary_present=true`
3. `internal_path_matches_contract=true`
4. `card_payload_parity_verified=true`
5. `response_no_interpretation_verified=true`
6. all external side-effect flags remain false:
   - no public route
   - no customer visibility
   - no worker visibility
   - no dispatch enablement
   - no live Acontext writes
   - no municipal-memory writes
   - no reputation receipts
   - no GPS/metadata exposure
   - no worker doctrine publication

Default fixture state remains blocked because no real route/auth proof exists yet.

Suggested future route, unchanged from the card contract:

```text
GET /internal/admin/city-ops/decision-support-matrix
```

## Safe to claim

- `decision_support_matrix_route_preflight_landed`
- the decision-support matrix card now has a fail-closed internal/admin route-readiness preflight
- future route work has an explicit gate: admin auth + card parity + pass-through semantics + no external side effects
- a mount-ready probe can be represented without promoting public/customer/dispatch/Acontext/reputation claims

## Still blocked / not safe to claim

- authenticated internal/admin route readiness
- route mount readiness
- route response verification
- admin auth boundary proven
- public route readiness
- customer-visible catalog readiness
- customer copy readiness
- polished operator console readiness
- operator UI readiness beyond generated internal/admin payload contracts
- dispatch routing or dispatch automation readiness
- live Acontext readiness / Acontext sink readiness
- runtime parity
- ERC-8004 reputation readiness
- worker Skill DNA readiness
- legal sufficiency or regulator acceptance
- exact GPS/metadata exposure
- worker-copyable municipal doctrine

## Why this matters for AAS strategy

This is the missing seam between artifact work and real application wiring. The product pattern is now:

```text
reviewed proof artifact
-> read-only intelligence matrix
-> internal/admin card
-> fail-closed route preflight
-> authenticated route later
```

That lets Execution Market AAS move toward operator tooling without accidentally turning internal proof artifacts into public claims. The preflight makes the next daytime route implementation small and reviewable: wire auth, return the persisted card payload as-is, prove parity, and stop.

## Verification

Passed:

```bash
python3 -m py_compile mcp_server/city_ops/decision_support_matrix_route_preflight.py mcp_server/tests/city_ops/test_decision_support_matrix_route_preflight.py
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops/test_decision_support_matrix_route_preflight.py -q
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Results: focused gate `6 passed, 1 existing pytest config warning`; full city-ops gate `192 passed, 1 existing pytest config warning`.

## Next smallest safe step

Implement the actual authenticated internal/admin route only if an admin auth boundary can be proven in code. The route should return `decision_support_matrix_card.json` as-is and then update the route-preflight probe with:

- route handler registered
- admin auth boundary present
- card payload parity verified
- pass-through-only response semantics verified

Do not add customer copy, public catalog, dispatch routing, live Acontext writes, ERC-8004 reputation updates, worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or worker-copyable doctrine in the route slice.
