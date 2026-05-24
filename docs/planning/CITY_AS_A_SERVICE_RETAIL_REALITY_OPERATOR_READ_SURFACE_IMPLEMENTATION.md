# City-as-a-Service — Retail Reality Operator Read Surface Implementation

> Date: 2026-05-23 23:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin only
> Safe claim: `retail_reality_operator_read_surface_landed`

## Priority ruling

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this dream session. The cron payload included stale requests for AutoJob, Frontier Academy, and KK v2, but the active priority file explicitly stops those tracks. They were not analyzed, edited, or expanded.

Allowed lane used: Execution Market AAS / City-as-a-Service only.

## What landed

Retail Reality AAS advanced exactly one safe rung after the internal package record:

```text
fixture/review gate -> local reviewed fixture -> internal package record -> read-only operator surface
```

New internal/admin artifacts:

```text
mcp_server/city_ops/retail_reality_operator_read_surface.py
mcp_server/city_ops/fixtures/aas_package_ladder/retail_reality_operator_read_surface.json
mcp_server/tests/city_ops/test_retail_reality_operator_read_surface.py
```

The read surface is exported from:

```text
mcp_server/city_ops/__init__.py
```

## Exact safe meaning

The only new safe claim is:

```text
retail_reality_operator_read_surface_landed
```

Conservative meaning:

- one Retail Reality internal package record can be rendered as a deterministic internal/admin operator surface;
- the surface consumes only `retail_reality_internal_package_record.json`;
- operator cards are pass-through views, not customer copy or semantic reinterpretation;
- source artifact IDs and a stable package digest are preserved;
- `safe_to_claim[]` and `do_not_claim_yet[]` stay adjacent;
- all readiness flags remain false;
- no route is registered.

## What remains blocked

The surface does **not** prove or authorize:

```text
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
public_route_ready
controlled_pilot_ready
public_pricing_or_customer_quote_ready
operator_queue_launch_ready
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
worker_copyable_retail_doctrine
```

Retail-specific blocked claims also travel beside the read surface, including public/customer/catalog/pricing/dispatch/reputation/runtime/permanent-status/inventory/compliance/safety/worker-doctrine readiness claims.

## Pattern insight

This is a useful low-authority AAS rung because it proves the packaging grammar can become an operator-facing artifact without becoming a product launch claim.

```text
internal package record -> operator visibility -> still no publication, pricing, dispatch, reputation, runtime, or doctrine
```

That matters because AAS needs internal operator leverage before it needs customer/public surfaces. The read surface lets operators inspect evidence, reviewed output, package state, safe claims, and blocked claims in one deterministic payload while keeping the authority boundary intact.

## Verification

Targeted Retail Reality suite:

```bash
.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_retail_reality_fixture_review_gate.py \
  mcp_server/tests/city_ops/test_retail_reality_local_reviewed_fixture.py \
  mcp_server/tests/city_ops/test_retail_reality_internal_package_record.py \
  mcp_server/tests/city_ops/test_retail_reality_operator_read_surface.py
```

Result:

```text
54 passed
```

Full city-ops suite:

```bash
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

Result after this implementation:

```text
1187 passed
```

## Next smallest proof

Create a Retail Reality customer-output schema gate over this read surface **only if** a customer-output path is desired. It must remain internal/admin, define allowed future fields, forbid exact-location/raw-metadata/customer delivery/publication/pricing/dispatch/reputation/runtime/permanent-status/inventory/compliance/safety/worker-doctrine claims, and stop before customer copy.
