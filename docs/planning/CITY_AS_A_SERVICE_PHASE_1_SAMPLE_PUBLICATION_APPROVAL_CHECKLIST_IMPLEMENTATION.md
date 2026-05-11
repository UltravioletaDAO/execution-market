# City as a Service — Phase 1 Sample Publication Approval Checklist Implementation

> Status: 2026-05-11 03:00 dream implementation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice takes the next safe step after the operator-reviewed internal samples: a tiny publication-approval checklist over those samples.

The checklist is deliberately **not approval**. It does not create customer copy, does not publish samples, does not expose a route/catalog, and does not strengthen any live Acontext, dispatch, reputation, GPS/raw metadata, legal/regulator, or worker-doctrine claim.

## Files changed

- `mcp_server/city_ops/phase1_sample_publication_approval_checklist.py`
  - builds/loads/writes `phase1_sample_publication_approval_checklist.json`
  - consumes only `phase1_operator_reviewed_sample_outputs.json`
  - verifies source samples are internal/admin only and not publishable
  - adds publication checklist gates while keeping actual approvals false
  - fails closed on readiness promotion, forbidden safe claims, missing blocked claims, source publishability drift, approval flips, and offer-review publication drift
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_sample_publication_approval_checklist.json`
- `mcp_server/tests/city_ops/test_phase1_sample_publication_approval_checklist.py`
- `mcp_server/city_ops/__init__.py`
  - exports build/load/write helpers

## New safe claim

- `phase1_sample_publication_approval_checklist_landed`

This claim means only: an internal/admin checklist exists for evaluating whether the Phase 1 samples could later move toward customer-facing copy.

## What the checklist proves

- source sample packet validates before checklist creation
- safe and blocked claims still travel together
- structural privacy/legal/non-guarantee boundaries are preserved
- required approval gates are named explicitly
- operator publish approval remains false
- customer delivery approval remains false
- evidence redaction review remains required before exposure

## Still false / blocked

- publication approval readiness
- sample output publication readiness
- customer copy creation/readiness
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
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_sample_publication_approval_checklist.py
# 12 passed
```

Full city-ops gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 312 passed
```

## Next smallest safe step

If Saúl wants customer-facing Phase 1 copy, create one draft packet that consumes this checklist and still keeps `publication_approved=false` until explicit operator review is recorded.

Do **not** publish samples, expose a customer/public route, dispatch from samples, attach reputation receipts, expose exact GPS/raw metadata, or claim pilot/customer/catalog readiness by default.
