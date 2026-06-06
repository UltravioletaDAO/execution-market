# City-as-a-Service — Retail Reality Answer Prerequisite Checklist Implementation

> Date: 2026-06-06 02:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Safe claim: `internal_admin_aas_retail_reality_answer_prerequisite_checklist_landed`.
> Status: prerequisite checklist only; not an operator answer, approval record, answer receipt, customer/public/worker surface, catalog/pricing/queue/dispatch route, reputation signal, payment/production reverification, runtime/Acontext/IRC mutation, exact GPS/raw-metadata/private-context release, domain-authority claim, worker doctrine, or stopped-project integration.

## Why this exists

The June 5 AAS concept-gap roadmap ranked Retail Reality first, but only as:

```text
answer_receipt_prerequisite_checklist_only_if_explicit_operator_answer_arrives
```

That wording matters. The next safe move is not to invent an answer, not to create a hold record, and not to expose a product lane. The safe move is to make the missing prerequisites explicit so a future operator answer can be handled without accidentally promoting internal planning into customer, worker, catalog, dispatch, runtime, or reputation surfaces.

The active no-answer default remains:

```text
keep_both_lanes_held
```

## What landed

- `mcp_server/city_ops/aas_retail_reality_answer_prerequisite_checklist.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_retail_reality_answer_prerequisite_checklist.json`
- `mcp_server/tests/city_ops/test_aas_retail_reality_answer_prerequisite_checklist.py`

The checklist consumes `aas_concept_gap_implementation_roadmap.json` by digest and freezes the rank-1 Retail Reality row as source truth.

## Checklist rows

The artifact records seven future prerequisites, all marked unsatisfied by this checklist:

1. explicit operator answer;
2. answer source trace;
3. product exposure scope;
4. redaction and metadata boundary;
5. catalog / pricing / queue / dispatch boundary;
6. authority-language boundary;
7. runtime and stopped-project boundary.

Each row says what a future operator would need to provide and what the safe default is if it is missing. None of the rows create an answer, approval, external surface, or runtime move.

## Boundary posture

The implementation hard-fails if the source roadmap or persisted checklist tries to claim any of these as complete:

- operator answer;
- operator approval;
- answer receipt;
- future answer selection;
- Retail Reality answer or hold record;
- product exposure approval;
- customer/public/worker copy;
- catalog, pricing, quote, queue, or dispatch;
- ERC-8004 reputation or Worker Skill DNA;
- payment/production reverification;
- runtime/Acontext/IRC mutation;
- exact GPS, raw metadata, or private-context release;
- retail/legal/regulator/safety/SLA authority;
- worker-copyable doctrine;
- AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2 expansion.

## Safe claim

```text
internal_admin_aas_retail_reality_answer_prerequisite_checklist_landed
```

Meaning only: a deterministic internal/admin checklist now identifies the future prerequisites required before any separate Retail Reality answer/hold record can be created. The checklist itself does not satisfy those prerequisites.

## Verification

```bash
git diff --check
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_concept_gap_matrix.py \
  mcp_server/tests/city_ops/test_aas_concept_gap_implementation_roadmap.py \
  mcp_server/tests/city_ops/test_aas_retail_reality_answer_prerequisite_checklist.py
```

No deploy is required because this is an internal/admin planning artifact and fixture only.
