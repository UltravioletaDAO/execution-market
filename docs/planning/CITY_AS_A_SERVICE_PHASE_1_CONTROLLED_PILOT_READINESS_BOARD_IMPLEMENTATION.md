# City as a Service — Phase 1 Controlled Pilot Readiness Board Implementation

> Status: 2026-05-10 23:00 dream implementation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice adds the missing internal stoplight between reviewed Phase 1 proof coverage and any future controlled concierge pilot language.

The board deliberately answers one question:

> Which Phase 1 City Counter Ops offers have enough internal proof packaging to plan the next gate, without accidentally authorizing customer copy, public catalog exposure, live transport claims, dispatch, reputation, GPS/raw metadata exposure, or worker-copyable doctrine?

Current answer:

- all three Phase 1 offers have reviewed fixture coverage
- only **Packet Submission Attempt** has an internal package record
- no offer is customer/pilot/public ready
- the next safe build is internal package records for **Counter Reality Check** and **Posting Compliance Check**

## Files changed

- `mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py`
  - builds, writes, loads, and validates the controlled-pilot readiness board
  - consumes only the reviewed fixture registry and Packet Submission internal package record
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
  "all_phase1_offers_have_internal_package_record": false,
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
| Counter Reality Check | yes | no | `reviewed_fixture_exists_needs_internal_package_record` | create a conservative internal package record |
| Packet Submission Attempt | yes | yes | `internal_package_recorded_not_customer_ready` | keep internal; do not advance to customer copy until other package records and schema review exist |
| Posting Compliance Check | yes | no | `reviewed_fixture_exists_needs_internal_package_record` | create a conservative internal package record and preserve GPS/raw metadata blocks |

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
# 263 passed, 2 warnings
```

## Next smallest safe step

Do not add more route wrappers or public copy by default.

Next product-safe implementation step:

1. Create `counter_reality_check` internal package record from the reviewed fixture.
2. Create `posting_compliance_check` internal package record from the reviewed fixture.
3. Update the readiness board to show all three internal package records exist.
4. Only then add a separate customer-output schema review gate.

Even after those steps, keep live Acontext, runtime parity, dispatch, reputation, privacy, and worker-doctrine gates separate.
