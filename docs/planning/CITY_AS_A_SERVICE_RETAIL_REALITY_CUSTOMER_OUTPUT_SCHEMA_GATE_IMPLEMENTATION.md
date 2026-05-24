# City-as-a-Service — Retail Reality Customer Output Schema Gate Implementation

> Date: 2026-05-24 00:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service internal/admin only  
> Safe claim: `retail_reality_customer_output_schema_gate_landed`

## Priority ruling

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this dream session. The cron payload included stale requests for AutoJob, Frontier Academy, and KK v2, but the active priority file explicitly stops those tracks. They were not analyzed, edited, or expanded.

Allowed lane used: Execution Market AAS / City-as-a-Service only.

## What landed

Retail Reality AAS advanced exactly one safe rung after the read-only operator surface:

```text
fixture/review gate -> local reviewed fixture -> internal package record -> read-only operator surface -> customer-output schema gate
```

New internal/admin artifacts:

```text
mcp_server/city_ops/retail_reality_customer_output_schema_gate.py
mcp_server/city_ops/fixtures/aas_package_ladder/retail_reality_customer_output_schema_gate.json
mcp_server/tests/city_ops/test_retail_reality_customer_output_schema_gate.py
```

The schema gate is exported from:

```text
mcp_server/city_ops/__init__.py
```

## Exact safe meaning

The only new safe claim is:

```text
retail_reality_customer_output_schema_gate_landed
```

Conservative meaning:

- one Retail Reality operator read surface can define allowed and forbidden future customer-output fields;
- the gate consumes only `retail_reality_operator_read_surface.json`;
- it creates no customer copy, sample output, publication approval, route, price, dispatch, reputation receipt, live runtime claim, or worker doctrine;
- all readiness and approval flags remain false;
- storefront output remains bounded to one reviewed observation window, source types, limitations, and non-guarantees.

## Allowed future customer-output fields

The gate permits only a narrow future schema shape:

```text
plain_language_status
storefront_context_summary
posted_hours_summary
observed_open_closed_or_unable_to_determine_state
availability_or_service_state_summary
source_type_summary
discrepancy_summary
observation_window_summary
what_was_checked
what_was_not_checked
limitations_and_non_guarantees
recommended_next_step
operator_review_notice
privacy_redaction_notice
```

This is a field boundary only. It is not customer copy.

## What remains blocked

The gate does **not** prove or authorize:

```text
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
public_route_ready
controlled_pilot_ready
public_pricing_or_customer_quote_ready
autonomous_dispatch_ready
erc8004_reputation_ready
worker_skill_dna_ready
live_acontext_runtime_parity
acontext_sink_ready
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
permanent_business_status_claim
inventory_guarantee
brand_compliance_certification
employee_performance_judgment
consumer_safety_claim
continuous_availability_monitoring_claim
worker_copyable_retail_doctrine
```

## Pattern insight

This is a deliberately small but useful product rung: it lets Retail Reality start shaping the eventual customer-facing response contract without producing customer-facing text.

```text
operator surface -> schema boundary -> still no customer copy, approval, route, dispatch, reputation, runtime, retail authority, or doctrine
```

That separation matters. Retail Reality is commercially promising because storefront proof is low-authority compared with legal, repair, safety, or custody work, but it can still overclaim quickly if observed state becomes permanent status or inventory certainty. The schema gate keeps that pressure contained.

## Verification

Targeted Retail Reality suite:

```bash
.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_retail_reality_fixture_review_gate.py \
  mcp_server/tests/city_ops/test_retail_reality_local_reviewed_fixture.py \
  mcp_server/tests/city_ops/test_retail_reality_internal_package_record.py \
  mcp_server/tests/city_ops/test_retail_reality_operator_read_surface.py \
  mcp_server/tests/city_ops/test_retail_reality_customer_output_schema_gate.py
```

Result:

```text
66 passed
```

Full city-ops suite:

```bash
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

Result after this implementation:

```text
1199 passed
```

## Next smallest proof

Draft one Retail Reality internal/admin sample output against this schema, then record a separate explicit hold/approval decision. Keep publication, customer delivery, public/catalog routes, pricing, dispatch, reputation, runtime, exact-location/raw-metadata exposure, permanent-status, inventory, brand-compliance, employee-performance, consumer-safety, continuous-monitoring, and worker-doctrine claims blocked.
