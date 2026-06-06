# City-as-a-Service — AAS Concept Gap Implementation Roadmap (2026-06-05 23:00)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Safe claim: `internal_admin_aas_concept_gap_implementation_roadmap_landed`.
> Status: source-backed implementation sequence; not an operator answer, approval record, answer receipt, customer/public/worker surface, pricing/catalog route, queue/dispatch, reputation, payment, runtime/Acontext/IRC mutation, exact GPS/raw-metadata/private-context release, authority claim, worker doctrine, or stopped-project integration.

## Why this exists

`CITY_AS_A_SERVICE_AAS_CONCEPT_GAP_MATRIX_2026_06_05.md` widened the AAS concept map without promoting any lane. This 23:00 slice turns that matrix into a deterministic planning sequence so future AAS work has a clear order of operations instead of scattered concept expansion.

The active no-answer boundary remains:

```text
pause_aas_proof_layering
keep_both_lanes_held
```

This roadmap does **not** create the missing human/operator answer. It only says which internal/admin planning slice would be safest next if work continues, and what must stay blocked.

## What landed

- `mcp_server/city_ops/aas_concept_gap_implementation_roadmap.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_concept_gap_implementation_roadmap.json`
- `mcp_server/tests/city_ops/test_aas_concept_gap_implementation_roadmap.py`

The roadmap consumes the persisted `aas_concept_gap_matrix.json` by digest and validates that the source matrix still records no answer, no approval, no answer receipt, no runtime/product movement, and no stopped-project expansion.

## Roadmap sequence

| Rank | AAS lane | Next planning slice | Boundary |
| --- | --- | --- | --- |
| 1 | Retail Reality | answer-receipt prerequisite checklist only if an explicit operator answer arrives | no answer/hold record from roadmap alone |
| 2 | Document Handoff | redaction and delivery-path gap note maintenance | no legal/notarial/custody authority |
| 3 | Compliance Desk | delivery-path hold gap review without customer copy | no regulator/legal sufficiency or publication claim |
| 4 | Field Asset Ops | visible asset-state fixture outline | no repair, warranty, SLA, or safety claim |
| 5 | Event Readiness | observed pre-event blocker outline | no permit, security, vendor, safety, or outcome claim |
| 6 | Incident Verification | observation/uncertainty language maintenance | no emergency, official report, fault, liability, or repair claim |
| 7 | Local Data Collection | measurement uncertainty rubric outline | no dataset publication or representativeness claim |
| 8 | Property Ops | blocked-claim quarantine vocabulary only | no appraisal, code/legal, access, insurance, or remediation claim |
| 9 | Runtime Memory / Acontext | read-only prerequisite inventory only after explicit runtime-memory answer | no live write/retrieve, parity, Docker repair, or IRC/session mutation |

Ranks are planning order only. They are not approval order, launch order, quote order, dispatch order, or product priority.

## Sequence rules

1. Use ranks as planning order only, never approval order.
2. Do not create an answer receipt unless an explicit operator answer exists outside this roadmap.
3. Do not turn roadmap rows into customer, public, worker, pricing, queue, dispatch, reputation, payment, or runtime surfaces.
4. Prefer observation vocabulary and blocked-claim quarantine over domain-authority language.
5. Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.

## Safe claim

```text
internal_admin_aas_concept_gap_implementation_roadmap_landed
```

Meaning only: a deterministic internal/admin roadmap now orders AAS concept-gap planning rows and preserves the existing no-answer, no-approval, no-product, no-runtime, no-private-context, no-authority, no-worker-doctrine, and stopped-project firewall.

## Verification

```bash
git diff --check
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_concept_gap_matrix.py \
  mcp_server/tests/city_ops/test_aas_concept_gap_implementation_roadmap.py
```

No deploy is required because this is an internal/admin planning artifact and fixture only.
