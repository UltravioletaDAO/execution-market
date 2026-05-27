# City as a Service — Local Data Collection Sample Output Review Decision Implementation

**Date:** 2026-05-26 22:00 America/New_York
**Status:** Landed explicit hold decision only
**Safe claim:** `local_data_collection_sample_output_review_decision_landed`

## What landed

`mcp_server/city_ops/local_data_collection_sample_output_review_decision.py` advances Local Data Collection AAS exactly one rung after the internal/admin sample output.

It consumes only `local_data_collection_internal_sample_output.json` and records the required explicit decision over that sample. The decision is a hold: `hold_not_approved_not_publishable`.

Files:

- `mcp_server/city_ops/local_data_collection_sample_output_review_decision.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/local_data_collection_sample_output_review_decision.json`
- `mcp_server/tests/city_ops/test_local_data_collection_sample_output_review_decision.py`
- exports in `mcp_server/city_ops/__init__.py`

## Boundary

The decision records:

- `explicit_hold_decision_recorded: true`
- `operator_review_recorded: true`
- `review_decision: hold_not_approved_not_publishable`

It keeps false/blocked:

- customer copy, customer delivery, and publication approval;
- public/catalog routes, controlled pilot, route registration, and launch readiness;
- pricing and dispatch;
- ERC-8004 reputation and reputation receipts;
- live Acontext/runtime parity;
- exact GPS/raw metadata release;
- dataset publication, analytics publication, statistical representativeness, continuous monitoring, official dataset certification, predictive analytics, and exactness certification;
- worker-copyable local data collection doctrine.

## Ladder position

Covered ladder steps now are:

1. `narrow_concierge_offer_card`
2. `fixture_spec`
3. `review_gate_checklist`
4. `reviewed_output_schema`
5. `local_reviewed_fixture`
6. `internal_package_record`
7. `coverage_summary_or_read_only_operator_surface`
8. `customer_output_schema_gate`
9. `internal_sample_output`
10. `explicit_approval_or_hold_decision`

Promotion remains false. The only next promotion-facing proof would be a separate human-operator customer-delivery approval artifact, if Saúl explicitly authorizes it later.

## Guardrails

The builder/loader fail closed if:

- the source sample promotes publication, delivery, dispatch, reputation, live runtime, exact-location/raw-metadata, dataset, analytics, representativeness, monitoring, certification, prediction, exactness, or worker-doctrine readiness;
- the source sample already records an approval/hold decision;
- the verdict changes away from hold;
- approval/publication/customer-delivery flags flip true;
- route/dispatch/reputation/runtime flags flip true;
- the boundary allows customer delivery, public route, dispatch, reputation, exact-location/raw-metadata, dataset/analytics/representativeness/monitoring/certification/prediction/exactness claims;
- findings stop requiring hold;
- a forbidden safe claim appears or safe/blocked claims overlap;
- forbidden representative-dataset, monitoring, certification, prediction, exactness, exact-location, raw-metadata, dispatch, or reputation language appears.

## Verification

Focused Local Data Collection internal-sample + review-decision tests: `28 passed`.

## Next safe slice

Do not publish or customer-deliver this sample by default. If customer exposure is desired later, create a separate human-operator approval artifact naming the exact sample text, redactions, delivery path, and still-blocked claims.
