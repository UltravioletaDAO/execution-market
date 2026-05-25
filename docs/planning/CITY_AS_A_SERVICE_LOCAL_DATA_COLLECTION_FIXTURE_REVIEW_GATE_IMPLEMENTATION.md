# City-as-a-Service — Local Data Collection Fixture Review Gate Implementation

> Date: 2026-05-25 midnight dream session  
> Scope: Execution Market AAS / City-as-a-Service internal/admin proof work only  
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`  
> Status: implemented internal fixture/review-gate artifact; not a dataset product; not analytics; not customer copy; not public/catalog route; not pricing; not queue/dispatch/reputation/runtime approval; not worker doctrine.

## Priority ruling

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled the session. The stale cron payload asked for AutoJob, Frontier Academy, and KK v2 work, but the active priority file explicitly stops those tracks. This implementation stayed inside the allowed Execution Market AAS / City-as-a-Service lane.

## Source planning context

The immediate source plan is:

```text
docs/planning/EXECUTION_MARKET_AAS_NEXT_LOW_AUTHORITY_PACKAGING_PLAN_2026_05_23_10PM.md
```

That plan ranked **Local Data Collection AAS** as the next low-authority packaging family after the Retail Reality continuation lane. The recommended smallest implementation slice was:

```text
Local Data Collection fixture/review gate planning packet
Boundary: one place + one observation window + one count/measurement question
```

This implementation turns that planning packet into a deterministic city-ops artifact and test fixture without promoting a customer dataset, analytics surface, route, dispatch path, reputation receipt, live runtime claim, exact GPS/raw metadata release, or worker-copyable data-collection doctrine.

## What landed

### New module

```text
mcp_server/city_ops/local_data_collection_fixture_review_gate.py
```

Safe claim:

```text
local_data_collection_fixture_review_gate_landed
```

The module builds, writes, loads, and validates a conservative fixture/review gate for:

```text
Local Data Collection as a Service
Offer: One-Window Count / Measurement Snapshot
```

It covers only the first three ladder steps:

1. `narrow_concierge_offer_card`
2. `fixture_spec`
3. `review_gate_checklist`

It requires all later promotion steps to remain pending:

- reviewed output schema
- local reviewed fixture
- internal package record
- coverage summary or read-only operator surface
- customer-output schema gate
- internal/admin sample output
- explicit approval or hold decision

### New persisted fixture

```text
mcp_server/city_ops/fixtures/aas_package_ladder/local_data_collection_fixture_review_gate.json
```

The fixture records the evidence contract for one place, one observation window, and one count/measurement question. It keeps the observation method bounded and uncertainty-aware:

- single place/context reference without public exact coordinates
- single observation window
- single count or measurement question
- allowed observation method
- permitted visual/context snapshot
- raw count or measurement value with units where applicable
- method note and uncertainty range
- ambiguity or occlusion note
- what was not checked

### New tests

```text
mcp_server/tests/city_ops/test_local_data_collection_fixture_review_gate.py
```

Coverage includes:

- deterministic artifact matches persisted fixture;
- source plan and Local Data Collection boundary are named;
- count/measurement evidence and output fields are preserved;
- exact GPS/raw metadata, dataset, analytics, prediction, and worker-doctrine fields remain forbidden;
- review checklist cannot silently pass;
- customer delivery/publication/dataset publication/analytics publication cannot be enabled;
- readiness flags remain false;
- forbidden safe claims are rejected;
- dropped blocked claims are rejected.

### Export update

`mcp_server/city_ops/__init__.py` now exports the Local Data Collection fixture-review-gate build/load/write helpers for consistency with the other AAS ladder artifacts.

## Explicit blocked claims

The gate keeps the global AAS blocked claims adjacent to Local Data Collection-specific blocked claims:

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
statistical_representativeness
continuous_monitoring
official_dataset_certification
exactness_beyond_observed_method
predictive_analytics
public_dataset_ready
worker_copyable_data_collection_doctrine
```

## Why this is valuable

Local Data Collection is a reusable adjacent-AAS family: many agents need small real-world measurements, counts, and observations, but the dangerous product temptation is to overstate a single observation as a representative dataset or automated analytics product.

This gate preserves the useful part:

```text
one place -> one window -> one question -> method + uncertainty -> explicit blocked claims
```

…and blocks the risky part:

```text
single observation -> statistical claim -> dataset product -> public analytics -> worker doctrine
```

The result is a low-authority proof rung that can later support local reviewed fixtures without implying customer readiness.

## Verification

Focused gate:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_local_data_collection_fixture_review_gate.py
```

Result:

```text
11 passed
```

Full city-ops suite:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

Result:

```text
1261 passed
```

## Next smallest proof

Create one synthetic local reviewed fixture for the scoped One-Window Count / Measurement Snapshot. It should fill the evidence contract for one place, one observation window, and one count/measurement question while keeping all promotion and customer/public readiness flags false.

Do not create a dataset product, analytics claim, customer output, catalog route, price, queue launch, dispatch path, reputation receipt, live Acontext/runtime proof, exact GPS/raw metadata exposure, or worker-copyable data-collection doctrine from this gate.
