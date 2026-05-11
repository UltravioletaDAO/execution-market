# City as a Service — Phase 1 Operator-Reviewed Sample Outputs Implementation

> Status: 2026-05-11 02:00 dream implementation
> Scope: Execution Market AAS / City-as-a-Service only
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice takes the next safe step after the Phase 1 customer-output schema review gate: one operator-reviewed internal sample output per Phase 1 City Counter Ops offer.

The samples are deliberately **not customer copy**. They are internal/admin wording-shape examples that prove the allowed schema fields can be populated while preserving privacy, legal-advice exclusion, non-guarantee language, and blocked-claim adjacency.

## Files changed

- `mcp_server/city_ops/phase1_operator_reviewed_sample_outputs.py`
  - builds/loads/writes `phase1_operator_reviewed_sample_outputs.json`
  - consumes only `phase1_customer_output_schema_review_gate.json`
  - creates one internal sample for each Phase 1 offer:
    - Counter Reality Check
    - Packet Submission Attempt
    - Posting Compliance Check
  - requires privacy-boundary review, legal-advice exclusion review, and non-guarantee language review
  - keeps operator publish approval and customer delivery approval false
  - fails closed on readiness promotion, forbidden safe claims, missing blocked claims, forbidden fields, sample publication drift, and review-gate removal
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_operator_reviewed_sample_outputs.json`
- `mcp_server/tests/city_ops/test_phase1_operator_reviewed_sample_outputs.py`
- `mcp_server/city_ops/__init__.py`
  - exports the build/load/write helpers

## New safe claim

- `phase1_operator_reviewed_sample_outputs_landed`

This claim means only: internal/admin sample outputs exist and passed conservative validation.

## What the sample packet proves

- all three Phase 1 offers can populate the allowed schema fields
- the samples include separate review flags for:
  - privacy boundary
  - legal-advice exclusion
  - non-guarantee language
- publish/customer delivery approvals remain false
- safe claims and blocked claims remain adjacent
- forbidden fields remain absent from sample payloads

## Still false / blocked

- customer copy readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- sample publication readiness
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
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_phase1_operator_reviewed_sample_outputs.py -q
# 11 passed, 2 warnings
```

Expanded city-ops gate:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 300 passed, 2 warnings
```

## Next smallest safe step

If Saúl wants to move toward customer-facing Phase 1 copy, add a tiny publication-approval checklist over these samples only.

Do **not** publish samples, expose a public route/catalog, dispatch from samples, claim pilot readiness, claim live Acontext/runtime parity, attach ERC-8004 reputation receipts, expose exact GPS/raw metadata, or create worker-copyable municipal doctrine by default.
