# City as a Service — Local Data Collection Internal Sample Output Implementation

**Date:** 2026-05-26 22:00 America/New_York
**Status:** Landed internal/admin sample output only
**Safe claim:** `local_data_collection_internal_sample_output_landed`

## What landed

`mcp_server/city_ops/local_data_collection_internal_sample_output.py` advances Local Data Collection AAS exactly one rung after the customer-output schema gate.

It consumes only `local_data_collection_customer_output_schema_gate.json` and creates one synthetic internal/admin sample output for a bounded `one_window_count_or_measurement_snapshot`.

Files:

- `mcp_server/city_ops/local_data_collection_internal_sample_output.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/local_data_collection_internal_sample_output.json`
- `mcp_server/tests/city_ops/test_local_data_collection_internal_sample_output.py`
- exports in `mcp_server/city_ops/__init__.py`

## Boundary

The sample populates only the Local Data Collection schema-gate allowed fields:

- `plain_language_status`
- `place_or_context_summary`
- `observation_window_summary`
- `count_or_measurement_question`
- `observed_value_summary`
- `method_summary`
- `uncertainty_and_ambiguity_summary`
- `what_was_checked`
- `what_was_not_checked`
- `limitations_and_non_guarantees`
- `recommended_next_step`
- `operator_review_notice`
- `privacy_redaction_notice`

The artifact remains synthetic, non-authoritative, non-jurisdiction-specific, and internal/admin only. It does not create customer copy, customer delivery, publication approval, a catalog, a route, pricing, dispatch, reputation, live runtime parity, exact GPS/raw metadata release, dataset publication, analytics, statistical representativeness, continuous monitoring, official certification, prediction, exactness certification, or worker-copyable local data collection doctrine.

## Guardrails

The builder/loader fail closed if:

- the source schema gate promotes readiness or drops required blocked claims;
- the sample consumes anything other than the schema-gate artifact;
- a disallowed output field is populated;
- privacy, limitations, uncertainty, non-guarantee, method-boundary, exact-location/raw-metadata, dataset/analytics/prediction, or publication/delivery hold signals are removed;
- any readiness flag flips true;
- a forbidden safe claim appears or safe/blocked claims overlap;
- forbidden representative-dataset, monitoring, certification, prediction, exactness, exact-location, raw-metadata, dispatch, reputation, or worker-doctrine language appears.

## Verification

Focused Local Data Collection internal-sample + review-decision tests: `28 passed`.

## Next safe slice

Record a separate explicit hold/approval decision over this exact sample. Default remains hold; do not publish, deliver, route, price, dispatch, attach reputation receipts, expose exact GPS/raw metadata, release dataset/analytics output, or claim customer/catalog/pilot/representativeness/monitoring/certification/prediction/exactness readiness.
