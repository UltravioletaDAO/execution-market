# City as a Service — Phase 1 Customer Output Schema Review Gate Implementation

> Status: 2026-05-11 01:00 dream implementation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice adds the separate internal/admin customer-output schema review gate that the 00:00 package-record work identified as the next smallest safe step.

The gate consumes the three Phase 1 City Counter Ops internal package records:

- Counter Reality Check
- Packet Submission Attempt
- Posting Compliance Check

It defines a conservative future customer-output schema boundary, but it does **not** create customer copy, publish a catalog, authorize a controlled pilot, create a front-door SKU, dispatch work, prove live Acontext/runtime parity, promote ERC-8004 reputation, expose exact GPS/raw metadata, or create worker-copyable municipal doctrine.

## Files changed

- `mcp_server/city_ops/phase1_customer_output_schema_review_gate.py`
  - builds/loads/writes `phase1_customer_output_schema_review_gate.json`
  - consumes only the three internal package records
  - requires operator-review source records, preserved forbidden claims, false readiness flags, and source package safe claims
  - defines shared allowed customer-output fields and shared forbidden fields
  - fails closed on readiness promotion, customer copy creation, forbidden safe claims, missing blocked claims, offer drift, field drift, or field overlap
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_customer_output_schema_review_gate.json`
- `mcp_server/tests/city_ops/test_phase1_customer_output_schema_review_gate.py`
- `mcp_server/city_ops/__init__.py`
  - exports the build/load/write helpers

## New safe claim

- `phase1_customer_output_schema_review_gate_landed`

This claim means only: the internal schema review gate exists and passed tests.

## What the gate allows later

The gate allows a future operator-reviewed customer output to contain only fields like:

- task/local case reference
- offer type
- plain-language status
- reviewed evidence summary
- what was checked
- what was not checked
- limitations and non-guarantees
- recommended next action
- operator review notice

## What remains forbidden

The gate explicitly blocks fields and claims for:

- exact GPS coordinates
- raw metadata blobs
- raw transcript authority
- private operator context
- private city-contact details
- guaranteed approval language
- legal advice / legal sufficiency
- regulator acceptance
- filing success
- worker-copyable municipal doctrine
- dispatch instructions / assignments
- ERC-8004 reputation receipts

## Still false / blocked

- customer copy readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA / worker-copyable municipal doctrine
- legal/regulator acceptance
- filing success, broad office reuse, city relationship, or approval guarantees
- exact GPS/raw metadata exposure

## Verification

Focused gate:

```bash
python3 -m py_compile \
  mcp_server/city_ops/phase1_customer_output_schema_review_gate.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_phase1_customer_output_schema_review_gate.py
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_phase1_customer_output_schema_review_gate.py -q
# 11 passed, 2 warnings
```

Expanded city-ops gate:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 289 passed, 2 warnings
```

## Next smallest safe step

Draft one operator-reviewed sample output per Phase 1 offer against this schema, with separate privacy/legal/non-guarantee review.

Do **not** publish the samples, route them publicly, dispatch from them, or claim pilot/customer/catalog readiness. Live Acontext, runtime parity, dispatch, reputation, GPS/raw metadata privacy, pilot exposure, and worker-doctrine gates remain separate.
