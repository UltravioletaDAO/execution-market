# City-as-a-Service — AAS Concept Gap Matrix (2026-06-05 22:00)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Safe claim: `internal_admin_aas_concept_gap_matrix_landed`.
> Status: source-backed gap matrix; not an operator answer, approval record, answer receipt, customer/public/worker surface, pricing/catalog route, queue/dispatch, reputation, payment, runtime/Acontext/IRC mutation, exact GPS/raw-metadata/private-context release, authority claim, worker doctrine, or stopped-project integration.

## Why this exists

The June 5 final wrap says the next useful unit is **not** another no-answer wrapper. The current default remains:

```text
pause_aas_proof_layering
keep_both_lanes_held
```

This slice therefore does not create another operator-answer/approval artifact. It only adds a source-backed internal/admin matrix so future AAS work can see which implementation concepts have real planning gaps and which claims must stay blocked.

## Source-backed inputs

The persisted fixture records SHA-256 digests for these reviewed planning sources:

- `EXECUTION_MARKET_AAS_CONCEPT_MAP_2026_05_08.md`
- `EXECUTION_MARKET_AAS_NEXT_LOW_AUTHORITY_PACKAGING_PLAN_2026_05_23_10PM.md`
- `CITY_AS_A_SERVICE_AAS_PRODUCT_FORK_NEXT_GATE_SELECTOR_2026_06_01.md`
- `CITY_AS_A_SERVICE_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_IMPLEMENTATION.md`
- `CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_05.md`

## What landed

- `mcp_server/city_ops/aas_concept_gap_matrix.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_concept_gap_matrix.json`
- `mcp_server/tests/city_ops/test_aas_concept_gap_matrix.py`

## Matrix use

Safe use:

```text
internal_admin_planning_index_only
```

Meaning: compare AAS families, preserve source digests, and keep concept-specific blocked claims visible.

Not safe use:

```text
operator_answer
operator_approval
answer_receipt
customer_copy
public_catalog_or_route
pricing_or_quote
queue_or_dispatch
worker_instruction
reputation_or_worker_skill_dna
payment_or_production_readiness
runtime_or_acontext_or_irc_mutation
exact_gps_or_raw_metadata_release
private_context_release
authority_claim
worker_copyable_doctrine
stopped_project_integration
```

## Small implementation-concept expansion

The matrix broadens underdeveloped AAS concepts without promoting them:

| AAS lane | Added implementation concept | Still blocked |
| --- | --- | --- |
| Field Asset Ops | visible asset-state / obstruction fixture outline | repair diagnosis, warranty, SLA, safety claims |
| Event Readiness | pre-event observed-checklist blocker schema | permit, security, vendor, safety, outcome claims |
| Property Ops | visible-condition vocabulary with high-risk claim quarantine | appraisal, code/legal, access, insurance, remediation claims |
| Local Data Collection | method/count/uncertainty rubric | dataset publication, representativeness, exactness claims |

The already-closer lanes remain held: Retail Reality needs a separate explicit human answer before any answer/hold record; Document/Handoff and Incident Verification must not receive approval artifacts without a real answer; Compliance Desk still lacks delivery-path authority; System Integration remains a support lane stopped by the route-regret panel.

## Safe claim

```text
internal_admin_aas_concept_gap_matrix_landed
```

Meaning only: a deterministic internal/admin AAS concept gap matrix exists with source-document digests, concept rows, false readiness flags, stopped-project firewall, and blocked-claim boundaries.

## Verification

```bash
git diff --check
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_concept_gap_matrix.py
```

No deploy is required because this is an internal/admin planning artifact and fixture only.
