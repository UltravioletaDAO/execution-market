# City-as-a-Service — Incident Verification Customer-Output Schema Gate Implementation

**Date:** 2026-05-14
**Status:** Implemented as internal/admin proof ladder rung
**Scope:** Adjacent AAS package expansion for Execution Market, schema boundary only

## What landed

Advanced **Incident Verification as a Service** from a read-only internal/admin operator surface into a conservative customer-output schema gate.

Files:

- `mcp_server/city_ops/incident_verification_customer_output_schema_gate.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/incident_verification_customer_output_schema_gate.json`
- `mcp_server/tests/city_ops/test_incident_verification_customer_output_schema_gate.py`
- exports in `mcp_server/city_ops/__init__.py`

Safe claim added:

- `incident_verification_customer_output_schema_gate_landed`

Inherited safe claims include:

- `incident_verification_operator_read_surface_landed`
- `incident_verification_internal_package_record_landed`
- `incident_verification_local_reviewed_fixture_landed`
- `incident_verification_fixture_review_gate_landed`
- `aas_minimum_ladder_template_landed`

## Ladder position

This slice covers exactly these steps:

1. `narrow_concierge_offer_card`
2. `fixture_spec`
3. `review_gate_checklist`
4. `reviewed_output_schema`
5. `local_reviewed_fixture`
6. `internal_package_record`
7. `coverage_summary_or_read_only_operator_surface`
8. `customer_output_schema_gate`

The next required steps remain:

1. `internal_sample_output`
2. `explicit_approval_or_hold_decision`

## Boundary preserved

The schema gate consumes only `incident_verification_operator_read_surface.json` and defines future customer-output field boundaries.

Allowed future customer-output fields:

- plain-language status
- incident question summary
- place/time-window summary
- wide/close reviewed evidence summaries
- observational severity taxonomy
- uncertainty note
- checked / not-checked sections
- limitations and non-guarantees
- recommended next action
- follow-on task trigger
- operator review notice
- privacy redaction notice

Explicitly forbidden fields/claims include:

- exact GPS coordinates, precise private location, or raw metadata
- raw transcript authority or private operator context
- emergency response instruction
- safety certification claim
- repair diagnosis/completion claim
- insurance adjustment claim
- SLA uptime claim
- official incident report claim
- fault/liability assignment
- dispatch instruction or assignment
- ERC-8004 reputation receipt
- worker-copyable incident doctrine
- customer/public launch or catalog/pilot readiness claim

## Guardrails

The builder/loader fail closed on:

- source operator-surface schema/id/family/offer drift
- missing inherited safe claims
- forbidden safe claims or safe/blocked claim overlap
- dropped blocked claims
- source access upgrades to customer/public/worker/dispatch/reputation/worker-doctrine/emergency/safety/repair/insurance/official-report surfaces
- source-contract drift away from the operator read surface
- allowed/forbidden field drift or overlap
- readiness flag promotion
- exact-location language such as latitude/longitude
- incident overclaims such as official report filing or repair completion

## Test gates

Focused Incident Verification ladder tests:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_incident_verification_fixture_review_gate.py \
  mcp_server/tests/city_ops/test_incident_verification_local_reviewed_fixture.py \
  mcp_server/tests/city_ops/test_incident_verification_internal_package_record.py \
  mcp_server/tests/city_ops/test_incident_verification_operator_read_surface.py \
  mcp_server/tests/city_ops/test_incident_verification_customer_output_schema_gate.py
```

Result: `66 passed`.

Full city-ops suite:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
```

Result: `630 passed`.

Compile gate:

```bash
/opt/homebrew/bin/python3.14 -m py_compile \
  mcp_server/city_ops/incident_verification_customer_output_schema_gate.py \
  mcp_server/tests/city_ops/test_incident_verification_customer_output_schema_gate.py
```

Result: passed.

## Next smallest proof

Draft one internal/admin Incident Verification sample output against `incident_verification_customer_output_schema_gate.json`, then record a separate explicit hold/approval decision.

Do **not** publish, route, dispatch, attach reputation receipts, expose exact GPS/raw metadata, or claim customer/catalog/pilot/emergency/safety/repair/insurance/SLA/official-report readiness by default.
