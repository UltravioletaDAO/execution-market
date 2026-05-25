# City-as-a-Service — Local Data Collection Internal Package Record Implementation

> Date: 2026-05-25 02:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal planning and deterministic fixture work only.
> Status: implemented internal/admin package rung; not customer copy; not a dataset; not analytics; not public/catalog route; not pricing; not queue/dispatch; not ERC-8004 reputation; not live Acontext/runtime parity; not exact GPS/raw metadata release; not worker-copyable doctrine.

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this dream session. It explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dreams, so this slice did not pull, inspect, edit, or expand those stopped tracks. Work stayed inside the active Execution Market AAS / City-as-a-Service lane.

This continues the May 25 Local Data Collection ladder:

```text
fixture/review gate
-> synthetic local reviewed fixture
-> internal package record
```

## What landed

New deterministic code and tests:

- `mcp_server/city_ops/local_data_collection_internal_package_record.py`
- `mcp_server/tests/city_ops/test_local_data_collection_internal_package_record.py`
- exports in `mcp_server/city_ops/__init__.py`

New persisted artifact:

- `mcp_server/city_ops/fixtures/aas_package_ladder/local_data_collection_internal_package_record.json`

Safe claim added:

```text
local_data_collection_internal_package_record_landed
```

Inherited safe claims:

```text
local_data_collection_local_reviewed_fixture_landed
local_data_collection_fixture_review_gate_landed
aas_minimum_ladder_template_landed
```

## Package boundary

The internal package record consumes only:

```text
local_data_collection_local_reviewed_fixture.json
```

It packages one synthetic One-Window Count / Measurement Snapshot into an internal/admin AAS record. The package preserves:

- one place/context reference without exact public coordinates
- one observation window
- one count/measurement question
- method summary
- uncertainty range
- ambiguity/occlusion note
- reviewed-output schema
- safe claims and blocked claims adjacent to each other

The record proves packaging continuity only. It does not authorize a customer dataset, customer report, analytics output, public/catalog SKU, pricing quote, dispatch route, reputation receipt, live runtime proof, exact-location release, statistical/exactness certification, or worker doctrine.

## Explicitly still blocked

The package keeps these classes false/blocked:

- customer copy and customer delivery
- publication, public catalog, front-door SKU, controlled pilot
- dataset publication and analytics publication
- statistical representativeness
- continuous monitoring
- official dataset certification
- exactness beyond the observed method
- predictive analytics
- pricing/quote readiness
- operator queue launch and dispatch
- ERC-8004 reputation and worker Skill DNA
- live Acontext/runtime parity
- exact GPS/raw metadata/private context release
- worker-copyable data-collection doctrine

## Contract checks

The module fails closed when:

- the source local fixture is promoted;
- a customer/public/dataset/analytics/pricing/dispatch/reputation/runtime/worker-doctrine flag flips true;
- required evidence or reviewed-output fields disappear;
- forbidden private/exact-location/dataset/analytics/reputation/worker-doctrine language appears;
- a blocked claim is moved into `safe_to_claim[]`;
- review checks stop blocking later promotion.

## Verification

Focused Local Data Collection ladder:

```text
.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_local_data_collection_fixture_review_gate.py \
  mcp_server/tests/city_ops/test_local_data_collection_local_reviewed_fixture.py \
  mcp_server/tests/city_ops/test_local_data_collection_internal_package_record.py
```

Result:

```text
37 passed
```

Full city-ops verification after implementation:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

Result:

```text
1287 passed
```

## Next smallest safe proof

```text
Local Data Collection read-only operator coverage surface
```

It should consume only `local_data_collection_internal_package_record.json`, render source lineage, packaged evidence coverage, reviewed output, safe claims, blocked claims, and false readiness flags for internal/admin operators, and keep all customer/public/dataset/analytics/pricing/dispatch/reputation/runtime/GPS/exactness/worker-doctrine claims false.

Do not create a customer dataset, analytics product, public route, price, queue, dispatch path, reputation receipt, live memory claim, exact-location release, or worker-copyable doctrine from this package record.
