# City-as-a-Service — AAS Field Asset Ops Visible-State Fixture Outline

> Date: 2026-06-06 04:00 America/New_York
> Safe claim: `internal_admin_aas_field_asset_visible_state_fixture_outline_landed`
> Scope: internal/admin AAS concept outline only — no operator answer, no approval, no answer receipt, no customer/public/worker copy, no field access authorization, no inspection/repair/remediation, no safety/warranty/SLA certification, no dispatch, no runtime movement.

## Why this slice exists

`DREAM-PRIORITIES.md` is the active dream authority. It keeps dream work inside Execution Market AAS / City-as-a-Service and explicitly blocks AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2. The stale 4 AM cron payload still named those stopped tracks; this pass intentionally did not pull, analyze, edit, expand, test, commit, or use those projects.

The latest AAS strength-roadmap connection board says the next useful move is to choose exactly one internal/admin planning slice from the ranked roadmap after rechecking the priority file. Rank 4 is Field Asset Ops:

```text
field_asset_ops -> visible_asset_state_fixture_outline_no_repair_or_sla_language
```

This implementation expands only that concept action. It keeps Field Asset Ops as low-authority observed-state vocabulary, not a product, repair workflow, SLA promise, safety certification, or dispatch route.

## Files added

- `mcp_server/city_ops/aas_field_asset_visible_state_fixture_outline.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_field_asset_visible_state_fixture_outline.json`
- `mcp_server/tests/city_ops/test_aas_field_asset_visible_state_fixture_outline.py`
- `docs/planning/CITY_AS_A_SERVICE_AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_IMPLEMENTATION.md`

## Source consumed

The outline consumes `aas_concept_gap_implementation_roadmap.json` by digest and requires the rank-4 roadmap row:

```text
aas_family: field_asset_ops
planning_sequence_rank: 4
roadmap_next_planning_slice: visible_asset_state_fixture_outline_no_repair_or_sla_language
next_allowed_without_human_answer: concept_outline_only
```

If the source roadmap promotes operator state, changes rank/action, drops blocked claims, or weakens the stopped-project firewall, the builder fails closed.

## What the artifact records

The artifact records an internal/admin fixture outline for visible asset state only:

- asset identifier placeholder without private location;
- visible presence/absence observed;
- apparent access or obstruction observed;
- apparent surface condition observed;
- visible indicator state observed without functionality certification;
- photo/screenshot reference placeholder after redaction review;
- explicit unknowns and unresolved observations.

Safe internal language is limited to statements like:

- `visible asset state outline only`
- `repair and SLA language blocked`
- `functionality not certified`
- `access or safety authority not claimed`
- `future answer receipt required before field operation or customer use`

Forbidden language remains blocked:

- `repair required`
- `safe to operate`
- `SLA met`
- `warranty valid`
- `technician dispatched`
- `asset certified`
- `customer ready`

## What it does not do

This is not:

- Saúl's operator answer;
- operator approval;
- an answer receipt;
- customer/public/worker copy;
- field visit access authorization;
- inspection, repair, remediation, or maintenance authorization;
- functionality, safety, warranty, or SLA certification;
- catalog/pricing/quote/route/queue/dispatch readiness;
- ERC-8004 reputation or Worker Skill DNA;
- payment/production reverification;
- live Acontext/IRC/session-manager mutation;
- exact GPS/raw metadata/private-context/PII release;
- property access, appraisal, or maintenance authority;
- worker-copyable doctrine;
- AutoJob, Frontier Academy, KK v2, or KarmaCadabra integration.

## Connection insight

The 4 AM pattern is that AAS value compounds when every service family gets a reusable observation grammar before it gets a product surface. For Field Asset Ops, the multiplier is not “dispatch humans faster”; it is “make visible-state evidence safe, comparable, and non-overclaiming enough that later operator-approved workflows can reuse it.”

That grammar can later inform customer packaging, worker instructions, and reputation only after separate explicit gates. For now, it is a conservative source-backed vocabulary rung.

## Next gate

Before any Field Asset Ops customer, worker, field, or dispatch movement:

```text
separate_explicit_operator_answer_receipt_then_field_asset_ops_customer_or_dispatch_gate
```

Until that exists, the recommended posture stays:

```text
concept_outline_only
```

## Verification

The intended verification gate for this slice:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_field_asset_visible_state_fixture_outline.py
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
```
