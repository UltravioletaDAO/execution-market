# City-as-a-Service — Retail Reality Fixture Review Gate Implementation

> Date: 2026-05-23 1 AM dream session
> Scope: Execution Market AAS / City-as-a-Service internal/admin proof work only
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`
> Status: implemented internal fixture/review-gate artifact; not customer copy; not public/catalog route; not pricing; not queue/dispatch/reputation/runtime approval; not worker doctrine.

## Priority ruling

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled the session. The stale cron payload asked for AutoJob, Frontier Academy, and KK v2 work, but the active priority file explicitly stops those tracks. This implementation stayed inside the allowed Execution Market AAS lane.

## Source planning context

The immediate source concept is:

```text
docs/planning/EXECUTION_MARKET_AAS_NEXT_CONCEPTS_2026_05_21_10PM.md
```

That plan recommended the safest next internal/admin concept slice:

```text
Retail Reality AAS fixture/review gate planning packet
Boundary: Storefront hours + availability check
```

The implementation turns that planning packet into a deterministic city-ops artifact and test fixture without promoting any customer-facing or worker-facing authority.

## What landed

### New module

```text
mcp_server/city_ops/retail_reality_fixture_review_gate.py
```

Safe claim:

```text
retail_reality_fixture_review_gate_landed
```

The module builds, writes, loads, and validates a conservative fixture/review gate for:

```text
Retail Reality as a Service
Offer: Storefront Hours + Availability Check
```

It covers only the first three ladder steps:

1. `narrow_concierge_offer_card`
2. `fixture_spec`
3. `review_gate_checklist`

It requires all later promotion steps to remain pending:

- reviewed output schema
- local reviewed fixture
- internal package record
- read-only operator surface / coverage summary
- customer-output schema gate
- internal/admin sample output
- explicit approval or hold decision

### New persisted fixture

```text
mcp_server/city_ops/fixtures/aas_package_ladder/retail_reality_fixture_review_gate.json
```

The fixture records the evidence contract for one storefront, one observation window, and one availability/hours question. It keeps evidence fields source-bounded and review-gated:

- storefront context photo or permitted visual snapshot
- posted-hours/open-closed proof
- observation window
- staff answer source type, if available
- availability/service observed state
- discrepancy summary
- uncertainty note
- what was not checked

### New tests

```text
mcp_server/tests/city_ops/test_retail_reality_fixture_review_gate.py
```

Coverage includes:

- deterministic artifact matches persisted fixture;
- source concept doc and Retail Reality boundary are named;
- required evidence/output fields are preserved;
- forbidden fields remain blocked;
- review checklist cannot silently pass;
- customer delivery/publication cannot be enabled;
- readiness flags remain false;
- forbidden safe claims are rejected;
- dropped blocked claims are rejected.

## Explicit blocked claims

The gate keeps the global AAS blocked claims adjacent to Retail Reality-specific blocked claims:

```text
customer_copy_ready
customer_visible_catalog_ready
public_service_catalog_ready
controlled_concierge_pilot_ready
customer_pilot_exposure_ready
front_door_sku_ready
pilot_authorized
catalog_customer_ready
operator_publish_approval
customer_delivery_approval
publication_approved
live_acontext_ready
runtime_parity_proven
autonomous_dispatch_ready
erc8004_reputation_ready
worker_skill_dna_ready
exact_gps_or_raw_metadata_exposure_allowed
permanent_business_status_claim
inventory_guarantee
brand_compliance_certification
employee_performance_judgment
consumer_safety_claim
worker_copyable_retail_doctrine
```

## Why this is valuable

Retail Reality is a lower-authority AAS family than legal/custody/emergency-heavy concepts. It expands the portfolio beyond the three active adjacent families while exercising the same proof discipline:

```text
simple observable reality -> reviewed fixture boundary -> explicit blocked claims -> no launch inference
```

This gives Execution Market a reusable path for storefront/state observations without making risky claims about permanent business status, inventory, brand compliance, employee performance, or consumer safety.

## Verification

Targeted gate:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_retail_reality_fixture_review_gate.py
```

Result:

```text
11 passed
```

Full city-ops suite should be run before final push if code continues changing in this lane.

## Next smallest proof

Create one local reviewed Retail Reality fixture for a scoped storefront hours + availability check that fills this evidence contract while keeping all promotion and customer/public readiness flags false.

Do not create customer copy, catalog routes, public pricing, queue launch, dispatch, reputation receipts, live Acontext writes, exact GPS/raw metadata exposure, or worker-copyable retail doctrine from this gate.
