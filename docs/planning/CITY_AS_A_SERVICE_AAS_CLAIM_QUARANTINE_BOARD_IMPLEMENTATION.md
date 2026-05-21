# City-as-a-Service — AAS Claim Quarantine Board Implementation

Date: 2026-05-21
Scope: Execution Market AAS / City-as-a-Service internal/admin proof slice only

## Priority guardrail

`~/clawd/DREAM-PRIORITIES.md` explicitly superseded the stale cron payload. AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 were not touched. This work stayed inside Execution Market AAS / City-as-a-Service.

## What landed

Added an internal/admin **AAS claim quarantine board** that consumes the existing cross-family approval-state matrix and turns every tempting launch/customer/runtime claim into an explicit held claim with a named smallest-proof requirement.

Files:

- `mcp_server/city_ops/aas_claim_quarantine_board.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_claim_quarantine_board.json`
- `mcp_server/tests/city_ops/test_aas_claim_quarantine_board.py`

## Safe claim

```text
admin_aas_claim_quarantine_board_landed
```

Conservative meaning: an internal/admin board exists for tracking claims that must remain quarantined. It does **not** authorize customer copy, delivery, publication, public routes, pricing, pilots, queues, dispatch, ERC-8004 reputation, worker Skill DNA, live Acontext/runtime parity, payment/production health, exact GPS/raw metadata release, domain/legal authority, or worker-copyable doctrine.

## Source artifact

Consumes only:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_cross_family_approval_state_matrix.json
```

The source matrix remains held:

- family count: `3`
- families with human approval record: `1`
- families with delivery authorization: `0`
- families publishable: `0`
- families with public/catalog routes: `0`
- families ready for dispatch: `0`
- families with reputation attachment ready: `0`
- families with live Acontext/runtime parity: `0`
- families allowed to release exact GPS/raw metadata: `0`

## Quarantine buckets

The board groups blocked claims into five operator-readable buckets:

1. **Customer/public exposure**
   - customer copy, delivery, publication, publishability, public route, catalog, front-door SKU.
   - smallest proof: named delivery/publication decision with fresh redaction and domain-authority checks.

2. **Pricing/operator launch**
   - public price, quote, operator queue, controlled pilot, operator workflow launch.
   - smallest proof: operator-reviewed pricing/workflow approval after customer exposure boundaries are approved.

3. **Dispatch/reputation/worker Skill DNA**
   - dispatch, autonomous dispatch, ERC-8004 reputation, attachable receipts, worker Skill DNA, worker-copyable doctrine.
   - smallest proof: live-safe dispatch route plus explicit reputation receipt policy; worker doctrine needs repeatable reviewed cases.

4. **Runtime/payment/production readiness**
   - live Acontext, runtime parity, payment/production reverification.
   - smallest proof: fresh live runtime preflight, transport parity proof, and separate payment/production health verification.

5. **Location metadata/domain authority**
   - exact GPS/raw metadata release, domain/legal/regulator/emergency/safety/repair/insurance/SLA/official-report/fault-liability authority.
   - smallest proof: scoped authority review and redaction pass; never inferred from planning artifacts.

## Why this matters

Previous AAS slices made the hold state safer one family at a time. This board adds a cross-family launch-claim firewall: if future agents, operators, or UI surfaces are tempted to say “ready,” they now have a deterministic artifact saying exactly which proof is missing.

The product rule is now mechanically represented:

```text
approval-state matrix is not approval
approval record is not delivery authorization
delivery gate is not publication unless it names a path
package labels are not public pricing
coordination insight is not runtime parity
```

## Verification

Focused test:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_claim_quarantine_board.py
# 10 passed
```

Full city-ops suite:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1038 passed
```

## Next smallest safe work

1. Add a read surface over `aas_claim_quarantine_board.json` for a future internal admin page.
2. Wire the board into any AAS operator dashboard only as internal/admin read-only state.
3. If Saúl wants customer exposure, choose one bucket and produce the exact named proof artifact rather than promoting broad readiness.
