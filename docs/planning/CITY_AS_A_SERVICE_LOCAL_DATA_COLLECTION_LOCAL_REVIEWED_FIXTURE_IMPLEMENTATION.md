# City-as-a-Service — Local Data Collection Local Reviewed Fixture Implementation

> Date: 2026-05-25 01:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal planning and deterministic fixture work only.
> Status: implemented internal/admin fixture rung; not customer copy; not a dataset; not analytics; not public/catalog route; not pricing; not queue/dispatch; not ERC-8004 reputation; not live Acontext/runtime parity; not exact GPS/raw metadata release; not worker-copyable doctrine.

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first. It explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions, so this implementation stayed inside the active Execution Market AAS lane.

This continues the midnight Local Data Collection AAS fixture/review gate with the next smallest safe rung:

```text
fixture/review gate
-> reviewed-output schema inside one local fixture
-> synthetic local reviewed fixture
```

## What landed

New deterministic code and tests:

- `mcp_server/city_ops/local_data_collection_local_reviewed_fixture.py`
- `mcp_server/tests/city_ops/test_local_data_collection_local_reviewed_fixture.py`
- exported through `mcp_server/city_ops/__init__.py`

New persisted artifact:

- `mcp_server/city_ops/fixtures/aas_package_ladder/local_data_collection_local_reviewed_fixture.json`

Safe claim added:

```text
local_data_collection_local_reviewed_fixture_landed
```

Inherited safe claims:

```text
local_data_collection_fixture_review_gate_landed
aas_minimum_ladder_template_landed
```

## Fixture boundary

The fixture is synthetic and non-site-specific. It records only:

```text
one place/context reference without exact public coordinates
one observation window
one count/measurement question
one method note
one uncertainty range
one ambiguity/occlusion note
one reviewed output shape
```

The example output is a bounded count range for visible queue positions inside a synthetic window. It is deliberately useful enough to exercise the review contract, but too narrow to become a product promise.

## Explicitly still blocked

The fixture keeps these classes false/blocked:

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

- the source fixture/review gate is promoted;
- a customer/public/dataset/analytics/dispatch/reputation/runtime/worker-doctrine flag flips true;
- required evidence or reviewed-output fields disappear;
- forbidden payload keys like latitude/longitude/raw metadata are added;
- a blocked claim is moved into `safe_to_claim[]`;
- review checks stop blocking later promotion.

## Verification

Focused gate after implementation:

```text
.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_local_data_collection_fixture_review_gate.py \
  mcp_server/tests/city_ops/test_local_data_collection_local_reviewed_fixture.py
```

Result:

```text
24 passed
```

Full city-ops verification after implementation:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

Result:

```text
1274 passed
```

## Next smallest safe proof

```text
Local Data Collection internal package record
```

It should consume only `local_data_collection_local_reviewed_fixture.json`, summarize evidence coverage, preserve source lineage and safe/blocked claim adjacency, and keep all customer/public/dataset/analytics/pricing/dispatch/reputation/runtime/GPS/exactness/worker-doctrine claims false.

Do not create a customer dataset, analytics product, route, price, queue, dispatch path, reputation receipt, live memory claim, exact-location release, or worker-copyable doctrine from this fixture.
