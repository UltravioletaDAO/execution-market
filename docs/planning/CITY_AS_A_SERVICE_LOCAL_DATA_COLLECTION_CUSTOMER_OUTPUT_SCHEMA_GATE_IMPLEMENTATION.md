# City as a Service — Local Data Collection Customer Output Schema Gate Implementation

**Date:** 2026-05-25 04:00 America/New_York
**Status:** Landed internal/admin schema boundary only
**Safe claim:** `local_data_collection_customer_output_schema_gate_landed`

## What landed

`mcp_server/city_ops/local_data_collection_customer_output_schema_gate.py` advances Local Data Collection AAS exactly one rung after the operator read surface.

It consumes only `local_data_collection_operator_read_surface.json` and defines a conservative future customer-output field boundary for one-window count / measurement snapshots.

Allowed future customer-output fields are bounded to plain-language, method-limited observation summaries:

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

Forbidden fields explicitly block exact GPS/raw metadata, private context, representative dataset claims, continuous monitoring, official certification, exactness certification, predictive analytics, trend inference, dispatch instructions, reputation receipts, worker-copyable doctrine, and public/catalog readiness.

## Boundary

This gate creates no customer copy and grants no approval to deliver, publish, route, price, dispatch, attach reputation, expose exact location/raw metadata, claim live runtime parity, certify representativeness/exactness, or publish worker doctrine.

## Verification

Focused Local Data Collection ladder through schema gate: `66 passed`.

## Next safe rung

One synthetic internal/admin sample output against this schema, followed by a separate explicit hold/approval decision. Default remains hold.
