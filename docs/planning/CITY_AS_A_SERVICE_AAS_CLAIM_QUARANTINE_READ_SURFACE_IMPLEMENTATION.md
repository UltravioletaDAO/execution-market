# City-as-a-Service — AAS Claim Quarantine Read Surface Implementation

Date: 2026-05-21  
Scope: Execution Market AAS / City-as-a-Service internal/admin proof slice only

## Priority guardrail

`~/clawd/DREAM-PRIORITIES.md` explicitly superseded the stale cron payload. AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 were not touched. This work stayed inside Execution Market AAS / City-as-a-Service.

## What landed

Added an internal/admin **AAS claim quarantine read surface** over the claim quarantine board.

Files:

- `mcp_server/city_ops/aas_claim_quarantine_read_surface.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_claim_quarantine_read_surface.json`
- `mcp_server/tests/city_ops/test_aas_claim_quarantine_read_surface.py`
- `mcp_server/city_ops/__init__.py` exports for the claim quarantine board and read surface

## Safe claim

```text
admin_aas_claim_quarantine_read_surface_landed
```

Conservative meaning: a deterministic internal/admin read payload exists for a future operator surface. It does **not** create approval, customer copy, delivery, publication, public/catalog routes, public pricing, pilots, operator queue launch, dispatch, ERC-8004 reputation, worker Skill DNA, live Acontext/runtime parity, payment/production reverification, exact GPS/raw metadata release, domain/legal authority, or worker-copyable doctrine.

## Source artifact

Consumes only:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_claim_quarantine_board.json
```

The source board remains held:

- family count: `3`
- families with human approval record: `1`
- families with delivery authorization: `0`
- families publishable: `0`
- families with public/catalog routes: `0`
- families ready for dispatch: `0`
- families with reputation attachment ready: `0`
- families with live Acontext/runtime parity: `0`
- families allowed to release exact GPS/raw metadata: `0`

## Surface contract

The read surface is intentionally pass-through and sticky:

- `source_summary` — board id, source posture, zero launch counts, and honest safe claim scope.
- `quarantine_bucket_cards` — one card per blocked launch-claim bucket, each with a `QUARANTINED — NOT SAFE TO CLAIM` badge.
- `family_hold_cards` — the underlying three-family hold state copied from the board.
- `next_smallest_proof_queue` — the exact next proof queue from the board, without reinterpretation.
- `claim_boundary_footer` — sticky safe/blocked claim footer for future admin UI rendering.
- `readiness` — all customer, publication, route, pricing, pilot, queue, dispatch, reputation, runtime, payment, GPS/raw metadata, domain-authority, and worker-doctrine flags remain `false`.

## Fail-closed checks

The implementation fails closed if:

- the source board schema, id, scope, or status drifts;
- any quarantined bucket becomes publishable or launchable;
- source matrix zero counts are promoted;
- any source or surface blocked claim appears in `safe_to_claim`;
- the surface registers a public/network route;
- any readiness/access/authority flag flips true;
- the persisted fixture drifts from the source board.

## Verification

Focused claim-board + read-surface tests:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_claim_quarantine_board.py \
  mcp_server/tests/city_ops/test_aas_claim_quarantine_read_surface.py
# 20 passed
```

Full city-ops suite:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1048 passed
```

## Next smallest safe work

1. Add an internal/admin route preflight or mount manifest for this read surface, still with `network_route_registered=false` until a real route exists.
2. Build an operator regret/prevented-claim panel that records which quarantined claims were prevented during a review pass.
3. If customer exposure is desired, choose exactly one bucket and produce the named proof artifact rather than promoting broad AAS readiness.
