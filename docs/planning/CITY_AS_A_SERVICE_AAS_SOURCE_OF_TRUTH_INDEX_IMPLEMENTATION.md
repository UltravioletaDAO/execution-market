# City-as-a-Service — AAS Source-of-Truth Index Implementation

> Date: 2026-06-03 02:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`.
> Safe claim: `internal_admin_aas_source_of_truth_index_landed`.

## What landed

Added `mcp_server/city_ops/aas_source_of_truth_index.py`, which builds a deterministic read-only source-of-truth index over the latest two-lane operator-answer schema:

- Source artifact consumed: `mcp_server/city_ops/fixtures/aas_package_ladder/aas_two_lane_operator_answer_schema.json`
- New persisted artifact: `mcp_server/city_ops/fixtures/aas_package_ladder/aas_source_of_truth_index.json`
- New tests: `mcp_server/tests/city_ops/test_aas_source_of_truth_index.py`

The index exists to prevent future AAS dream/checkpoint work from extending stale docs as if they were current launch authority.

## Current entrypoints marked

The index marks these as current/near-current entrypoints, with SHA-256 digests persisted in the fixture:

1. `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
2. `docs/planning/CITY_AS_A_SERVICE_10PM_AAS_NEXT_STEPS_2026_06_02.md`
3. `docs/planning/CITY_AS_A_SERVICE_AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_IMPLEMENTATION.md`
4. `docs/planning/CITY_AS_A_SERVICE_AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_IMPLEMENTATION.md`
5. `docs/planning/CITY_AS_A_SERVICE_AAS_SOURCE_OF_TRUTH_INDEX_IMPLEMENTATION.md`

## Historical context demoted

The index explicitly demotes older docs to historical context only, including:

- `MASTER_PLAN_CITY_AS_A_SERVICE.md` — taxonomy/background only, not launch authority.
- `CITY_AS_A_SERVICE_SERVICE_CATALOG.md` — service family taxonomy only, not public catalog/pricing authority.
- Older AAS next-concept and packaging plans — not current next-step drivers.
- June 1 product-fork selector and June 2 final wrap — useful context, but superseded by the two-lane operator-answer schema.

It also carries a stale-pattern ban list for older May pre-dawn syntheses, May final wraps, generic single-boundary docs, and system-integration flywheel route docs.

## Boundary posture

This artifact records:

- no operator answer;
- no operator approval;
- no selected future decision;
- no Retail Reality product exposure;
- no runtime-memory wiring;
- no runtime adapter registration/enabling;
- no IRC/session-manager mutation;
- no live Acontext write/retrieval;
- no customer/public/worker surface;
- no catalog/pricing/queue/dispatch;
- no ERC-8004 reputation or Worker Skill DNA;
- no payment/production reverification;
- no exact GPS/raw metadata/private-context release;
- no authority claim;
- no worker-copyable doctrine;
- no stopped-project integration.

Default no-answer posture remains:

```text
keep_both_lanes_held_internal_admin_only
```

## Verification

Focused verification:

```text
./.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_source_of_truth_index.py \
  mcp_server/tests/city_ops/test_aas_two_lane_operator_answer_schema.py

24 passed
```

Full city-ops verification:

```text
./.venv/bin/python -m pytest -q mcp_server/tests/city_ops

1860 passed
```

## Next safe move

If no real human/operator answer exists, stop at this hold posture or append a read-only final-wrap/handoff. Do not add more product, runtime, dispatch, reputation, payment, private-context, location, authority, worker-doctrine, or stopped-project claims.

If a real answer exists later, create a separate answer record against `aas_two_lane_operator_answer_schema.json`; do not mutate this source index into an answer or approval artifact.
