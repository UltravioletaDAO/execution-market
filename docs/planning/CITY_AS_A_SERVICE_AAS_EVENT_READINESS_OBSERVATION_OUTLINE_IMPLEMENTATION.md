# City-as-a-Service — AAS Event Readiness Observation Outline

> Date: 2026-06-06 07:00 America/New_York
> Safe claim: `internal_admin_aas_event_readiness_observation_outline_landed`
> Scope: internal/admin AAS concept outline only — no operator answer, no approval, no answer receipt, no customer/public/worker copy, no event-site access authorization, no permit/security/vendor/venue decision, no capacity/safety/attendance/outcome/SLA certification, no dispatch, no runtime movement.

## Why this slice exists

`DREAM-PRIORITIES.md` is the active dream authority. It keeps dream work inside Execution Market AAS / City-as-a-Service and explicitly blocks AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2. This pass intentionally did not pull, analyze, edit, expand, test, commit, or use those projects.

The June 6 06:00 final wrap named the next safe no-answer slice, if any, as Event Readiness observation outline:

```text
event_readiness -> attendance_readiness_observation_outline_no_safety_or_guarantee_language
```

The source roadmap rank-5 row is stricter:

```text
event_readiness -> observed_pre_event_blocker_outline_no_permit_security_or_outcome_claim
```

This implementation expands only that concept action. It keeps Event Readiness as low-authority visible-state / blocker vocabulary, not a product launch, permit workflow, security clearance, vendor commitment, attendance guarantee, venue authority, or dispatch route.

## Files added

- `mcp_server/city_ops/aas_event_readiness_observation_outline.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_event_readiness_observation_outline.json`
- `mcp_server/tests/city_ops/test_aas_event_readiness_observation_outline.py`
- `docs/planning/CITY_AS_A_SERVICE_AAS_EVENT_READINESS_OBSERVATION_OUTLINE_IMPLEMENTATION.md`

## Source consumed

The outline consumes `aas_concept_gap_implementation_roadmap.json` by digest and requires the rank-5 roadmap row:

```text
aas_family: event_readiness
planning_sequence_rank: 5
roadmap_next_planning_slice: observed_pre_event_blocker_outline_no_permit_security_or_outcome_claim
next_allowed_without_human_answer: concept_outline_only
```

If the source roadmap promotes operator state, changes rank/action, drops blocked claims, or weakens the stopped-project firewall, the builder fails closed.

## What the artifact records

The artifact records an internal/admin observation outline for visible pre-event readiness indicators only:

- event identifier placeholder without private location;
- scheduled window placeholder without contact or private context;
- visible setup presence/absence observed;
- apparent staging or wayfinding state observed;
- apparent access/obstruction observed without access authority;
- visible vendor/equipment presence observed without performance claim;
- photo/screenshot reference placeholder after redaction review;
- explicit unknowns and unresolved observations.

Safe internal language is limited to statements like:

- `visible event-readiness observation outline only`
- `permit security and outcome claims blocked`
- `visible setup does not certify operational readiness`
- `venue vendor and crowd-control authority not claimed`
- `future answer receipt required before event delivery or customer use`

Forbidden language remains blocked:

- `permit approved`
- `security cleared`
- `event guaranteed`
- `crowd safety confirmed`
- `vendor confirmed`
- `venue authorized`
- `attendee ready`
- `dispatch ready`

## What it does not do

This is not:

- Saúl's operator answer;
- operator approval;
- an answer receipt;
- selected future answer;
- customer/public/worker copy;
- event-site access authorization;
- permit, security, vendor, venue, legal, municipal, or crowd-control decision;
- capacity, safety, attendance, outcome, guarantee, or SLA certification;
- catalog/pricing/quote/route/queue/dispatch readiness;
- ERC-8004 reputation or Worker Skill DNA;
- payment/production reverification;
- live Acontext/IRC/session-manager mutation;
- exact GPS/raw metadata/private-context/PII release;
- worker-copyable doctrine;
- AutoJob, Frontier Academy, KK v2, or KarmaCadabra integration.

## Connection insight

The 7 AM pattern is that Event Readiness must be safer than the event itself is urgent. Time pressure makes permit, safety, crowd, vendor, and outcome overclaims easy. The useful AAS slice is therefore a digest-backed observation vocabulary that names what is visible and what remains unknown, while preserving every authority boundary for a later explicit operator answer.

That grammar can later inform packaging, worker instructions, and reputation only after separate explicit gates. For now, it is a conservative source-backed vocabulary rung.

## Next gate

Before any Event Readiness customer, worker, event, or dispatch movement:

```text
separate_explicit_operator_answer_receipt_then_event_readiness_customer_or_dispatch_gate
```

Until that exists, the recommended posture stays:

```text
concept_outline_only
```

## Verification

The intended verification gate for this slice:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_event_readiness_observation_outline.py
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
```
