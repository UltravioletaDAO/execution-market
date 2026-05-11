# City as a Service — Phase 1 Remaining Internal Package Records Implementation

> Status: 2026-05-11 00:00 dream implementation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## Summary

This slice completes the internal package-record coverage gate for all three Phase 1 City Counter Ops offers without promoting customer copy, public catalog exposure, controlled-pilot exposure, live Acontext, runtime parity, dispatch, reputation, GPS/raw metadata exposure, legal/regulator claims, or worker-copyable municipal doctrine.

Before this slice, the controlled-pilot readiness board showed:

- all three Phase 1 offers had reviewed fixtures
- only `packet_submission_attempt` had an internal package record
- `counter_reality_check` and `posting_compliance_check` still needed conservative internal package records

After this slice:

- `counter_reality_check` has an internal package record
- `packet_submission_attempt` keeps its existing internal package record
- `posting_compliance_check` has an internal package record
- the readiness board now says all three internal package records exist
- customer/pilot/public readiness remains blocked

## Files changed

- `mcp_server/city_ops/phase1_remaining_offer_internal_package_records.py`
  - adds builders/loaders/writers for the Counter Reality Check and Posting Compliance Check internal package records
  - validates reviewed fixture source identity, operator-reviewed status, proof label, outcome/source/follow-on trigger, no raw transcript authority, no unreviewed memory, and no exact GPS/raw metadata exposure
  - keeps `safe_to_claim[]` adjacent to `do_not_claim_yet[]`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_counter_reality_check_internal_package_record.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_posting_compliance_internal_package_record.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_controlled_pilot_readiness_board.json`
  - now records all three internal package records as present
- `mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py`
  - consumes all three package records before reporting package coverage
  - still refuses customer/pilot/public readiness promotion
- `mcp_server/tests/city_ops/test_phase1_remaining_offer_internal_package_records.py`
- `mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py`
- `mcp_server/city_ops/__init__.py`
  - exports the new package-record helpers

## New safe claims

- `phase1_counter_reality_check_internal_package_record_landed`
- `phase1_posting_compliance_internal_package_record_landed`

Existing safe claim preserved:

- `phase1_controlled_pilot_readiness_board_landed`

## Board posture after this slice

The board may now safely claim internal package-record coverage only:

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
| Counter Reality Check | yes | yes | `internal_package_recorded_not_customer_ready` | customer-output schema review as a separate gate |
| Packet Submission Attempt | yes | yes | `internal_package_recorded_not_customer_ready` | customer-output schema review as a separate gate |
| Posting Compliance Check | yes | yes | `internal_package_recorded_not_customer_ready` | customer-output schema + GPS/raw metadata privacy review as separate gates |

## Guardrails preserved

The package records and board still block:

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

Focused gates passed:

```bash
python3 -m py_compile \
  mcp_server/city_ops/phase1_remaining_offer_internal_package_records.py \
  mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_phase1_remaining_offer_internal_package_records.py \
  mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_phase1_remaining_offer_internal_package_records.py \
  mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py -q
# 25 passed, 2 warnings
```

Full city-ops gate for this slice:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 278 passed, 2 warnings
```

## Next smallest safe step

Do **not** add more route wrappers or public copy by default.

Next product-safe implementation step:

1. Add a separate customer-output schema review gate that consumes the three internal package records.
2. Keep the gate internal/admin-only.
3. Make the gate fail closed unless all package records preserve blocked claims, operator-review requirements, and false readiness flags.
4. Keep live Acontext, runtime parity, dispatch, reputation, privacy, and worker-doctrine gates separate.

Even after customer-output schema review, do not claim pilot/customer/public readiness until a distinct pilot-exposure authorization gate exists.
