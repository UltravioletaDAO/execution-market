# City-as-a-Service — AAS Property Ops Blocked-Claim Quarantine Vocabulary

> Date: 2026-06-07 00:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only  
> Safe claim: `internal_admin_aas_property_ops_blocked_claim_quarantine_vocabulary_landed`  
> Status: deterministic Property Ops quarantine vocabulary; not an operator answer, approval, answer receipt, customer/public/worker copy, property access authorization, appraisal/code/legal/insurance/remediation authority, catalog/pricing/route, queue/dispatch, reputation, payment, runtime/Acontext/IRC mutation, GPS/raw-metadata/private-context/PII release, worker doctrine, or stopped-project integration.

## Why this exists

`DREAM-PRIORITIES.md` is still the active dream override: only Execution Market AAS / City-as-a-Service is in scope, and AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 stay stopped.

The latest source-backed AAS concept roadmap had already landed safer ranks 2-7. The next unhandled low-authority row is rank 8: Property Ops. This lane is useful, but risky: property language can accidentally turn into claims about access, inspection, appraisals, code compliance, legal sufficiency, insurance readiness, safety, repairs, remediation, or private location data. This slice keeps Property Ops as blocked-claim vocabulary only.

## What landed

- `mcp_server/city_ops/aas_property_ops_blocked_claim_quarantine_vocabulary.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_property_ops_blocked_claim_quarantine_vocabulary.json`
- `mcp_server/tests/city_ops/test_aas_property_ops_blocked_claim_quarantine_vocabulary.py`

The artifact consumes `aas_concept_gap_implementation_roadmap.json` by digest and validates the rank-8 Property Ops source row:

```text
blocked_claim_quarantine_vocabulary_only
```

## Safe internal vocabulary

The vocabulary allows only internal/admin placeholders and boundary language:

- property identifier placeholder without private location or parties
- visible condition placeholder without access or entry authorization
- apparent occupancy or use signal without tenancy or legal claim
- visible maintenance signal without repair or remediation commitment
- apparent access or obstruction signal without right-of-entry claim
- photo/screenshot/text reference placeholder after redaction review
- code, compliance, appraisal, insurance, and legal claims quarantined
- unresolved Property Ops unknowns

## What remains blocked

The artifact explicitly records no:

- operator answer, operator approval, or answer receipt
- customer/public/worker copy
- property access, site entry, recipient/customer-use authorization, or worker visit
- inspection, appraisal, code review, legal review, insurance review, safety certification, or compliance certification
- repair, remediation, maintenance, warranty, habitability, value, or outcome commitment
- catalog, pricing, quote, route, queue, dispatch, or worker instruction
- ERC-8004 reputation or Worker Skill DNA
- payment/production reverification
- live Acontext/IRC/session-manager mutation
- exact GPS, raw metadata, private context, PII, address, or doxxable location release
- worker-copyable doctrine
- AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2 integration/expansion

## Next required gate

```text
separate_explicit_operator_answer_receipt_then_property_ops_customer_or_dispatch_gate
```

Until that exists, the recommended posture is:

```text
blocked_claim_quarantine_only
```

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_property_ops_blocked_claim_quarantine_vocabulary.py
```

Result:

```text
11 passed
```

No deploy is required: this is internal/admin planning code, persisted fixture, and documentation only. No backend/frontend/public/runtime/customer/worker/payment/reputation surface changed.
