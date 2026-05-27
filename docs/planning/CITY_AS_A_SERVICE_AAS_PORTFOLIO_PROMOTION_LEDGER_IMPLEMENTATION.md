# City-as-a-Service — AAS Portfolio Promotion Ledger Implementation

> Created: 2026-05-27 00:35 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin ledger landed; no customer exposure, no public route, no pricing, no queue/dispatch, no reputation, no live runtime parity

## Why this slice exists

The May 26 portfolio promotion map identified the safest no-human/no-runtime continuation: one deterministic ledger across the active AAS families. The goal is to make the next morning decision clear without accidentally converting internal proof artifacts into customer copy, catalog readiness, dispatch readiness, reputation events, or worker doctrine.

## New files

```text
mcp_server/city_ops/aas_portfolio_promotion_ledger.py
mcp_server/tests/city_ops/test_aas_portfolio_promotion_ledger.py
mcp_server/city_ops/fixtures/aas_package_ladder/aas_portfolio_promotion_ledger.json
docs/planning/CITY_AS_A_SERVICE_AAS_PORTFOLIO_PROMOTION_LEDGER_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports:

```python
build_aas_portfolio_promotion_ledger
load_aas_portfolio_promotion_ledger
write_aas_portfolio_promotion_ledger
```

## Source artifacts consumed

The ledger consumes exactly these current boundary artifacts:

```text
aas_single_boundary_human_operator_approval_record.json
document_handoff_sample_output_review_decision.json
incident_verification_sample_output_review_decision.json
retail_reality_pending_approval_status_card.json
local_data_collection_sample_output_review_decision.json
```

It records each source schema, ID, digest, and latest safe claim.

## Safe claim

```text
admin_aas_portfolio_promotion_ledger_landed
```

This means only that a read-only internal/admin promotion ledger exists. It does not approve any family for customer exposure.

## Ledger posture

The ledger tracks five families:

1. Compliance Desk — approved internal label only, no delivery path.
2. Document / Handoff Logistics — held, not approved, not publishable.
3. Incident Verification — held, not approved, not publishable.
4. Retail Reality — pending human review, not approved.
5. Local Data Collection — held, not approved, not publishable.

Summary counters intentionally remain zero for:

```text
customer delivery authorization
publication readiness
public/catalog routes
pricing or customer quote readiness
queue or dispatch readiness
reputation attachment
live Acontext/runtime parity
exact GPS/raw metadata release
worker-copyable doctrine
```

## Fail-closed checks

The builder and loader reject:

- forbidden safe claims such as `customer_delivery_approved`, `publication_approved`, `dispatch_ready`, `erc8004_reputation_ready`, `live_acontext_ready`, or `worker_copyable_doctrine_ready`;
- promoted source public/readiness flags;
- Retail Reality approval status drift from pending to approved;
- Local Data Collection runtime-readiness drift;
- summary counters above zero;
- source digest drift;
- safe/blocked claim overlap.

## Verification

Focused verification during implementation:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_portfolio_promotion_ledger.py
```

Result:

```text
12 passed
```

## Next safe step

Do not build customer copy, public routes, pricing, queue launch, dispatch, reputation, or worker doctrine from this ledger.

The next safe fork is exactly one of:

1. Retail Reality human-operator approval record for the already selected boundary, if Saúl wants customer exposure.
2. Compliance Desk delivery/publication gate only if an exact delivery path is separately authorized.
3. Isolated Acontext runtime repair lane, without inferring customer exposure.
4. Another internal/admin proof seam if no human/runtime decision exists.
