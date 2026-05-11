# City as a Service — Phase 1 Customer-Facing Draft Packet Implementation

> Status: 2026-05-11 04:00 dream implementation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice follows the publication-approval checklist with one internal/admin draft packet shaped for future customer-facing review.

The packet is deliberately **not approved and not publishable**. It creates a copy-shaped review artifact so an operator can evaluate tone, limitations, and offer boundaries without accidentally creating customer-ready copy, a public catalog, a pilot launch, dispatch behavior, reputation behavior, live Acontext claims, or worker-copyable municipal doctrine.

## Files changed

- `mcp_server/city_ops/phase1_customer_facing_draft_packet.py`
  - builds/loads/writes `phase1_customer_facing_draft_packet.json`
  - consumes only `phase1_sample_publication_approval_checklist.json`
  - creates one internal draft card per Phase 1 offer
  - keeps the packet copy-shaped but internal/admin-only
  - fails closed on publication approval, source approval-gate promotion, offer publishability, forbidden safe claims, missing blocked claims, and card readiness drift
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_customer_facing_draft_packet.json`
- `mcp_server/tests/city_ops/test_phase1_customer_facing_draft_packet.py`
- `mcp_server/city_ops/__init__.py`
  - exports build/load/write helpers

## New safe claim

- `phase1_customer_facing_draft_packet_landed`

This means only: an internal/admin draft-review packet exists over the Phase 1 sample-publication checklist.

## What the draft packet proves

- the source publication checklist is still not approved
- approval gates for evidence redaction, operator publish approval, and customer delivery remain false
- one draft card exists per Phase 1 offer
- each draft card requires pre-send reviews before any exposure
- safe claims and blocked claims remain adjacent
- publication/customer/catalog/pilot/live/dispatch/reputation/privacy/worker-doctrine readiness remains false

## Still false / blocked

- draft packet publication readiness
- publication approval/readiness
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
  mcp_server/tests/city_ops/test_phase1_customer_facing_draft_packet.py
# 12 passed
```

Full city-ops gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 324 passed
```

## Next smallest safe step

Record an explicit operator review decision against this draft packet. Do not flip `publication_approved` without a separate approval artifact, and do not expose a public/customer route by default.
