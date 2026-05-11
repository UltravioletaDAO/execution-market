# City as a Service — Phase 1 Controlled Pilot Readiness Board Implementation

> Status: 2026-05-11 00:00 updated after remaining package records  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice adds the missing internal stoplight between reviewed Phase 1 proof coverage and any future controlled concierge pilot language.

The board deliberately answers one question:

> Which Phase 1 City Counter Ops offers have enough internal proof packaging to plan the next gate, without accidentally authorizing customer copy, public catalog exposure, live transport claims, dispatch, reputation, GPS/raw metadata exposure, or worker-copyable doctrine?

Current answer:

- all three Phase 1 offers have reviewed fixture coverage
- all three Phase 1 offers now have internal package records
- no offer is customer/pilot/public ready
- the next safe build is a separate internal customer-output schema review gate, not pilot/customer exposure

## Files changed

- `mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py`
  - builds, writes, loads, and validates the controlled-pilot readiness board
  - consumes only the reviewed fixture registry and all three Phase 1 internal package records
  - fails closed on pilot exposure, customer copy, live Acontext, runtime, dispatch, reputation, worker doctrine, or GPS/raw metadata readiness promotion
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_controlled_pilot_readiness_board.json`
  - persisted deterministic board artifact
- `mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py`
  - covers artifact parity, per-offer readiness rows, false readiness flags, valid temp writes, and fail-closed drift cases
- `mcp_server/city_ops/__init__.py`
  - exports the builder/loader/writer

## New safe claim

- `phase1_controlled_pilot_readiness_board_landed`

## Board posture

The board preserves this global readiness posture:

```json
{
  "all_phase1_offers_have_reviewed_fixture": true,
  "all_phase1_offers_have_internal_package_record": true,
  "customer_copy_ready": false,
  "customer_visible_catalog_ready": false,
  "public_service_catalog_ready": false,
  "customer_pilot_exposure_allowed": false,
  "front_door_sku_ready": false,
  "live_acontext_ready": false,
  "runtime_parity_proven": false,
  "autonomous_dispatch_ready": false,
  "reputation_ready": false,
  "worker_copyable_doctrine_ready": false,
  "exact_gps_or_raw_metadata_exposure_allowed": false
}
```

## Per-offer status

| Offer | Reviewed fixture | Internal package record | Board status | Next smallest step |
|---|---:|---:|---|---|
| Counter Reality Check | yes | yes | `internal_package_recorded_not_customer_ready` | customer-output schema review as a separate internal gate |
| Packet Submission Attempt | yes | yes | `internal_package_recorded_not_customer_ready` | customer-output schema review as a separate internal gate |
| Posting Compliance Check | yes | yes | `internal_package_recorded_not_customer_ready` | customer-output schema + GPS/raw metadata privacy review as separate internal gates |

## Guardrails preserved

The board explicitly blocks:

- customer copy readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- filing success or broad office reuse claims
- city influence, approval guarantees, legal sufficiency, or regulator acceptance
- live Acontext readiness or sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004/reputation readiness
- worker Skill DNA / worker-copyable municipal doctrine
- exact GPS or raw metadata exposure

## Verification

Focused gate passed:

```bash
python3 -m py_compile \
  mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py -q
# 10 passed, 2 warnings
```

Full city-ops gate also passed:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 278 passed, 2 warnings
```

## Next smallest safe step

Do not add more route wrappers or public copy by default.

Next product-safe implementation step:

1. Add a separate customer-output schema review gate that consumes the three internal package records.
2. Keep the gate internal/admin-only.
3. Fail closed on dropped blocked claims, readiness promotion, GPS/raw metadata exposure, worker-copyability strengthening, or customer/pilot/public exposure language.
4. Keep live Acontext, runtime parity, dispatch, reputation, privacy, and worker-doctrine gates separate.

Even after that schema review, do not claim pilot/customer/public readiness until a distinct pilot-exposure authorization gate exists.
