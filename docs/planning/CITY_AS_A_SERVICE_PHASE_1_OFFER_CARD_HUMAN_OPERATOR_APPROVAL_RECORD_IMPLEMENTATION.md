# City as a Service — Phase 1 Offer Card Human Operator Approval Record Implementation

> Status: 2026-05-11 07:00 dream implementation
> Scope: Execution Market AAS / City-as-a-Service only
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice adds a narrow human-operator approval record for exactly one Phase 1 offer card: `counter_reality_check`.

The artifact names the approved text fields/sections, records the redaction checks that passed, names the only authorized delivery path, and carries forward the still-blocked claims. It is a record boundary only: it does not publish, route publicly, dispatch work, attach reputation receipts, expose exact GPS/raw metadata, or make pilot/catalog/customer delivery claims.

## Files changed

- `mcp_server/city_ops/phase1_offer_card_human_operator_approval_record.py`
  - builds/loads/writes `phase1_offer_card_human_operator_approval_record.json`
  - consumes the customer-facing draft packet plus the prior operator hold decision
  - records `human_operator_approval_recorded=true` for exactly one offer card
  - keeps `operator_publish_approval=false`, `customer_delivery_approval=false`, `publication_approved=false`, and all customer/catalog/pilot/dispatch/reputation/GPS readiness flags false
  - fails closed on source readiness promotion, multiple-offer approval drift, delivery-path expansion, forbidden safe claims, missing blocked claims, and customer-delivery/publication flips
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_offer_card_human_operator_approval_record.json`
- `mcp_server/tests/city_ops/test_phase1_offer_card_human_operator_approval_record.py`
- `mcp_server/city_ops/__init__.py`
  - exports build/load/write helpers

## New safe claim

- `phase1_offer_card_human_operator_approval_record_landed`

This means only: an internal/admin human-operator approval record exists for one named offer-card text boundary.

## Approved record boundary

- approved offer: `counter_reality_check`
- approved text fields: `draft_title`, `customer_safe_positioning`, `draft_sections`, `must_keep_limitations`
- approved delivery path: `internal_admin_review_record_to_named_operator_queue_only`
- redactions passed: exact GPS removed, raw metadata removed, private source identifiers removed, legal advice language absent, guarantee/influence language absent, dispatch instruction language absent, reputation receipt language absent

## Still false / blocked

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
- exact GPS/raw metadata exposure
- legal/regulator acceptance, filing success, broad office reuse, city relationship, or approval guarantees

## Verification

Focused gate:

```bash
python3 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_offer_card_human_operator_approval_record.py
# 12 passed
```

Adjacent Phase 1 gate:

```bash
python3 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_draft_packet_operator_review_decision.py \
  mcp_server/tests/city_ops/test_phase1_customer_facing_draft_packet.py \
  mcp_server/tests/city_ops/test_phase1_sample_publication_approval_checklist.py \
  mcp_server/tests/city_ops/test_phase1_offer_card_human_operator_approval_record.py
# 48 passed
```

Full city-ops gate:

```bash
python3 -m pytest -q mcp_server/tests/city_ops
# 348 passed
```

## Daytime recommendation

Use this as the approval-record boundary only. A separate explicitly reviewed customer-delivery approval is still required before any customer exposure, public route, catalog entry, pilot claim, dispatch, or reputation attachment.
