# City-as-a-Service — AAS Incident Verification Observation/Uncertainty Maintenance

> Date: 2026-06-06 22:00 America/New_York
> Safe claim: `internal_admin_aas_incident_verification_observation_uncertainty_maintenance_landed`
> Scope: internal/admin AAS language-maintenance only — no operator answer, no approval, no answer receipt, no customer/public/worker copy, no incident-site access authorization, no emergency/safety decision, no official report, no fault/liability/insurance claim, no repair/remediation claim, no dispatch, no runtime movement.

## Why this slice exists

`DREAM-PRIORITIES.md` is the active dream authority. It keeps dream work inside Execution Market AAS / City-as-a-Service and explicitly blocks AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2. This pass intentionally did not pull, analyze, edit, expand, test, commit, or use those projects.

The 07:00 Event Readiness observation outline already landed at commit `fb100ce7`, so this 22:00 pass did **not** duplicate Event Readiness. After re-reading the current board, source-of-truth index, and concept-gap roadmap, the next single low-authority roadmap row after Event Readiness is rank 6:

```text
incident_verification -> observation_uncertainty_language_maintenance_only
```

This implementation expands only that maintenance action. It keeps Incident Verification as observation/uncertainty language hygiene, not an approval artifact, incident authority, emergency workflow, official report, repair instruction, insurance/fault/liability finding, customer output, or dispatch route.

## Files added

- `mcp_server/city_ops/aas_incident_verification_observation_uncertainty_maintenance.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_incident_verification_observation_uncertainty_maintenance.json`
- `mcp_server/tests/city_ops/test_aas_incident_verification_observation_uncertainty_maintenance.py`
- `docs/planning/CITY_AS_A_SERVICE_AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_IMPLEMENTATION.md`

## Source consumed

The maintenance artifact consumes `aas_concept_gap_implementation_roadmap.json` by digest and requires the rank-6 roadmap row:

```text
aas_family: incident_verification
planning_sequence_rank: 6
roadmap_next_planning_slice: observation_uncertainty_language_maintenance_only
next_allowed_without_human_answer: maintenance_only_no_approval_record
```

If the source roadmap promotes operator state, changes rank/action, drops blocked claims, or weakens the stopped-project firewall, the builder fails closed.

## What the artifact records

The artifact records an internal/admin maintenance vocabulary for incident observation and uncertainty only:

- incident identifier placeholder without private location or parties;
- observation window placeholder without private context;
- visible condition/state observed without cause assignment;
- source-type placeholder after redaction review;
- required uncertainty/ambiguity statement;
- non-authority disclaimer for emergency, safety, fault, and liability;
- photo/screenshot/text reference placeholder after redaction review;
- explicit unknowns and unresolved observations.

Safe internal language is limited to statements like:

- `incident observation uncertainty language maintenance only`
- `emergency official-report fault and repair claims blocked`
- `visible condition does not assign cause or liability`
- `uncertainty statement required before any future review`
- `future answer receipt required before incident delivery or customer use`

Forbidden language remains blocked:

- `emergency verified`
- `official report complete`
- `fault assigned`
- `liability confirmed`
- `repair required`
- `safe condition certified`
- `insurance ready`
- `dispatch ready`

## What it does not do

This is not:

- Saúl's operator answer;
- operator approval;
- an answer receipt;
- selected future answer;
- customer/public/worker copy;
- incident-site access authorization;
- emergency, safety, legal, insurance, SLA, official-report, fault, or liability authority;
- repair, remediation, or completion instruction;
- catalog/pricing/quote/route/queue/dispatch readiness;
- ERC-8004 reputation or Worker Skill DNA;
- payment/production reverification;
- live Acontext/IRC/session-manager mutation;
- exact GPS/raw metadata/private-context/PII release;
- worker-copyable doctrine;
- AutoJob, Frontier Academy, KK v2, or KarmaCadabra integration.

## Connection insight

The 22:00 pattern is that Incident Verification is valuable only if uncertainty stays first-class. The useful internal/admin slice is not “verify incidents faster”; it is “preserve language that separates observation from cause, fault, emergency response, official reporting, insurance, repair, and dispatch.”

That grammar can later inform a customer or worker path only after a separate explicit operator answer receipt. For now, it is a conservative maintenance rung over an already-sensitive AAS family.

## Next gate

Before any Incident Verification customer, worker, incident, or dispatch movement:

```text
separate_explicit_operator_answer_receipt_then_incident_verification_customer_or_dispatch_gate
```

Until that exists, the recommended posture stays:

```text
maintenance_only_no_approval_record
```

## Verification

The intended verification gate for this slice:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_incident_verification_observation_uncertainty_maintenance.py
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
```
