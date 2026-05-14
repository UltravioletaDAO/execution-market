# City-as-a-Service — Incident Verification Local Fixture Implementation

**Date:** 2026-05-13  
**Status:** Implemented as internal/admin proof ladder rung  
**Scope:** Adjacent AAS package expansion for Execution Market, not customer copy

## Why this slice matters

The active AAS plan needs more than City-as-a-Service itself. It needs reusable adjacent service families that inherit the same proof discipline without accidentally becoming public SKUs, autonomous dispatch, reputation claims, or worker-copyable doctrine too early.

This slice advances **Incident Verification as a Service** from a fixture boundary into one reviewed local fixture shape. It gives operators a deterministic internal artifact for a one-location incident state snapshot while keeping every public/customer/runtime claim explicitly blocked.

## Implemented artifacts

- `mcp_server/city_ops/incident_verification_fixture_review_gate.py`
- `mcp_server/city_ops/incident_verification_local_reviewed_fixture.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/incident_verification_fixture_review_gate.json`
- `mcp_server/city_ops/fixtures/aas_package_ladder/incident_verification_local_reviewed_fixture.json`
- `mcp_server/tests/city_ops/test_incident_verification_fixture_review_gate.py`
- `mcp_server/tests/city_ops/test_incident_verification_local_reviewed_fixture.py`

The new local fixture covers exactly these ladder steps:

1. `narrow_concierge_offer_card`
2. `fixture_spec`
3. `review_gate_checklist`
4. `reviewed_output_schema`
5. `local_reviewed_fixture`

The next required steps remain:

1. `internal_package_record`
2. `coverage_summary_or_read_only_operator_surface`
3. `customer_output_schema_gate`
4. `internal_sample_output`
5. `explicit_approval_or_hold_decision`

## Conservative boundaries preserved

The implementation keeps these claims blocked:

- customer/public catalog readiness
- controlled concierge pilot readiness
- live Acontext/runtime parity readiness
- autonomous dispatch readiness
- ERC-8004 reputation readiness
- worker Skill DNA / worker-copyable doctrine readiness
- exact GPS/raw metadata exposure
- emergency response
- safety certification
- repair diagnosis or completion
- insurance adjustment
- SLA uptime
- official incident reporting

The reviewed fixture is synthetic and local. It intentionally avoids exact public coordinates, private addresses, raw media metadata, private identities, raw transcripts as authority, and operational dispatch instructions.

## Acceptance tests

Validated with:

```bash
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

Result: `590 passed`.

## Next smallest proof

Create `incident_verification_internal_package_record.py` that consumes `incident_verification_local_reviewed_fixture.json` and produces an internal package record with:

- inherited safe claims only:
  - `incident_verification_local_reviewed_fixture_landed`
  - `incident_verification_fixture_review_gate_landed`
  - `aas_minimum_ladder_template_landed`
- all customer/public/dispatch/reputation/live-memory/emergency/safety/repair/insurance/SLA/official-report/worker-doctrine flags still false
- a read-only operator summary of what the local fixture proves and what remains blocked

Do **not** create customer copy, public catalog routes, live dispatch, reputation writes, or worker doctrine until a later explicit approval/hold decision artifact exists.
