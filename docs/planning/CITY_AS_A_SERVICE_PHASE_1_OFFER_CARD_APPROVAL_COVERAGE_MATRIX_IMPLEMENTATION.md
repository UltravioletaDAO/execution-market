# City as a Service — Phase 1 Offer Card Approval Coverage Matrix Implementation

> Status: 2026-05-11 23:00 dream implementation
> Scope: Execution Market AAS / City-as-a-Service only
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice adds an internal/admin approval coverage matrix over all three Phase 1 City Counter Ops offer cards.

It consumes the copy-shaped draft packet, the operator hold decision, and the existing single-offer human-operator approval record. It makes the current boundary explicit:

- `counter_reality_check` has a text-boundary approval record only.
- `packet_submission_attempt` and `posting_compliance_check` still lack separate human-operator text-boundary approval records.
- all three offers still lack operator publish approval, customer delivery approval, publication approval, catalog route authorization, controlled-pilot authorization, dispatch authorization, reputation attachment authorization, and exact GPS/raw metadata release authorization.

This is a coverage matrix only. It does not publish, route publicly, deliver customer copy, dispatch work, attach reputation receipts, expose exact GPS/raw metadata, prove live Acontext/runtime parity, or make customer/catalog/pilot readiness claims.

## Files changed

- `mcp_server/city_ops/phase1_offer_card_approval_coverage_matrix.py`
  - builds/loads/writes `phase1_offer_card_approval_coverage_matrix.json`
  - consumes:
    - `phase1_customer_facing_draft_packet.json`
    - `phase1_draft_packet_operator_review_decision.json`
    - `phase1_offer_card_human_operator_approval_record.json`
  - records one approved offer-card text boundary and two unapproved offer cards
  - keeps all customer/public/catalog/pilot/dispatch/reputation/GPS readiness flags false
  - fails closed on source readiness promotion, source mismatch, delivery-path expansion, claim overlap, missing blocked claims, row approval drift, or customer-delivery/publication flips
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_offer_card_approval_coverage_matrix.json`
- `mcp_server/tests/city_ops/test_phase1_offer_card_approval_coverage_matrix.py`
- `mcp_server/city_ops/__init__.py`
  - exports build/load/write helpers

## New safe claim

- `phase1_offer_card_approval_coverage_matrix_landed`

This means only: an internal/admin matrix exists that compares the three Phase 1 draft offer cards against the current approval-record boundary.

## Coverage result

| Offer | Text-boundary approval | Customer delivery | Publication | Catalog/public route | Dispatch/reputation/GPS |
|---|---:|---:|---:|---:|---:|
| Counter Reality Check | recorded for text boundary only | blocked | blocked | blocked | blocked |
| Packet Submission Attempt | missing | blocked | blocked | blocked | blocked |
| Posting Compliance Check | missing | blocked | blocked | blocked | blocked |

## Still false / blocked

- complete Phase 1 approval coverage
- operator publish approval
- customer delivery approval
- publication approval/readiness
- customer copy creation/readiness
- customer-visible catalog / public service catalog readiness
- controlled concierge pilot / customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness / runtime parity
- autonomous dispatch / dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA / worker-copyable municipal doctrine
- exact GPS/raw metadata exposure or release authorization
- legal/regulator acceptance, filing success, broad office reuse, city relationship, or approval guarantees

## Verification

Focused gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_offer_card_approval_coverage_matrix.py
# 12 passed
```

Adjacent Phase 1 gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_customer_facing_draft_packet.py \
  mcp_server/tests/city_ops/test_phase1_draft_packet_operator_review_decision.py \
  mcp_server/tests/city_ops/test_phase1_offer_card_human_operator_approval_record.py \
  mcp_server/tests/city_ops/test_phase1_offer_card_approval_coverage_matrix.py
# 48 passed
```

Full city-ops gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 360 passed
```

## Next smallest safe step

If the goal is still controlled customer exposure, add separate human-operator text-boundary approval records for `packet_submission_attempt` and `posting_compliance_check`, or add a held customer-delivery approval checklist over exactly the one already-approved text boundary. Do not flip publish/customer/catalog/pilot/dispatch/reputation/GPS readiness by default.
