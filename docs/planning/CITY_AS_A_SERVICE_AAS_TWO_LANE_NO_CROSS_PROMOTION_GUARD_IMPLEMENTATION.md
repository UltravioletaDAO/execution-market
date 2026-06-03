# City-as-a-Service — AAS Two-Lane No-Cross-Promotion Guard Implementation

**Date:** 2026-06-02 23:00 ET
**Status:** Landed as internal/admin proof block only
**Safe claim:** `internal_admin_aas_two_lane_no_cross_promotion_guard_landed`

## Why this slice exists

Two adjacent AAS workstreams now exist:

1. **Runtime-memory no-answer observability** — an internal/admin rubric can score whether a no-answer handoff preserved blocked claims and kept runtime mutation held.
2. **Retail Reality product-exposure candidate review** — an internal/admin gate can select exactly one boundary family for human review while preserving default-off product exposure.

Those two lanes are useful together, but dangerous if accidentally conflated. A high observability score must not become Retail Reality product approval. A selected Retail Reality candidate must not become runtime-memory wiring approval.

This proof block creates the explicit seam between them.

## What landed

- `mcp_server/city_ops/aas_two_lane_no_cross_promotion_guard.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_two_lane_no_cross_promotion_guard.json`
- `mcp_server/tests/city_ops/test_aas_two_lane_no_cross_promotion_guard.py`
- Exported builder/loader/writer from `mcp_server/city_ops/__init__.py`

## Source artifacts consumed

- `aas_no_answer_observability_rubric_fixture.json`
- `aas_product_exposure_boundary_candidate_review_gate.json`

The guard records deterministic SHA-256 digests for both sources and fails closed if either source drifts into approval, runtime mutation, customer/public/worker exposure, or stopped-project integration.

## Guard contract

The landed guard proves only this:

```text
two_lanes_remain_internal_admin_only_no_cross_promotion_no_answer_no_approval_no_customer_public_worker_runtime_reputation_payment_dispatch_or_stopped_project_promotion
```

The lane contract is intentionally narrow:

- Runtime-memory observability may produce only an internal/admin boundary-preservation score.
- Retail Reality product candidate review may produce only one internal/admin human-review candidate.
- Neither lane may promote the other.
- No operator answer or approval is recorded.
- If no human answer exists, both lanes remain held.

## Safe to claim

```text
internal_admin_aas_no_answer_observability_rubric_fixture_landed
internal_admin_aas_product_exposure_boundary_candidate_review_gate_landed
internal_admin_aas_two_lane_no_cross_promotion_guard_landed
```

Meaning only: the internal/admin guard exists, consumes both deterministic sources, preserves their blocked claims, and prevents score/candidate cross-promotion.

## Still blocked

```text
two_lane_guard_records_operator_answer
two_lane_guard_records_operator_approval
two_lane_guard_treats_observability_score_as_product_approval
two_lane_guard_treats_product_candidate_selection_as_runtime_approval
two_lane_guard_approves_retail_reality_product_exposure
two_lane_guard_selects_design_only_wiring
two_lane_guard_executes_bounded_activation_test
two_lane_guard_registers_or_enables_runtime_adapter
two_lane_guard_mutates_irc_session_manager
two_lane_guard_writes_or_retrieves_live_acontext
two_lane_guard_creates_dashboard_or_public_metric
two_lane_guard_creates_customer_public_or_worker_surface
two_lane_guard_registers_catalog_pricing_queue_or_dispatch
two_lane_guard_emits_erc8004_reputation_or_worker_skill_dna
two_lane_guard_reverifies_payment_or_production
two_lane_guard_releases_exact_gps_or_raw_metadata
two_lane_guard_releases_private_context
two_lane_guard_grants_domain_authority_claims
two_lane_guard_publishes_worker_copyable_doctrine
two_lane_guard_integrates_stopped_projects
```

Inherited blocked claims from both source artifacts remain blocked as well.

## Product boundary preservation

The following surfaces remain explicitly non-authorized:

- `/public/catalog/pricing/dispatch`
- `/legal/emergency/safety/repair/insurance/SLA`
- customer/public/worker surfaces
- dashboard/public metrics
- queue/dispatch
- reputation / Worker Skill DNA
- payment/production claims
- exact GPS/raw metadata release
- private-context release
- authority claims
- worker-copyable doctrine
- stopped-project integration

`/analyzed/edited` state remains internal/admin state only, not product exposure.

## Verification

```text
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_two_lane_no_cross_promotion_guard.py \
  mcp_server/tests/city_ops/test_aas_no_answer_observability_rubric_fixture.py \
  mcp_server/tests/city_ops/test_aas_product_exposure_boundary_candidate_review_gate.py

36 passed
```

## Next good AAS step

Create a **separate operator answer schema** for exactly one next decision:

1. keep both lanes held,
2. create a real Retail Reality answer/hold record,
3. create a real runtime-memory answer record, or
4. pause AAS proof layering.

Do not infer that answer from this guard.
