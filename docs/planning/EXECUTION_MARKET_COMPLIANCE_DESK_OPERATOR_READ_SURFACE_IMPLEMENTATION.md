# Execution Market Compliance Desk Operator Read Surface Implementation

> Date: 2026-05-12 05:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service adjacent package planning
> Status: internal/admin read surface only; not customer copy; not a public catalog; not dispatch; not live Acontext/runtime parity; not ERC-8004 reputation; not worker doctrine.

## What landed

Advanced the Compliance Desk adjacent-AAS ladder by exactly one rung: from an internal package record to a **read-only operator surface** for `visible_posting_notice_compliance_snapshot`.

Files:

- `mcp_server/city_ops/compliance_desk_operator_read_surface.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/compliance_desk_operator_read_surface.json`
- `mcp_server/tests/city_ops/test_compliance_desk_operator_read_surface.py`
- exports in `mcp_server/city_ops/__init__.py`

Safe claim added:

- `compliance_desk_operator_read_surface_landed`

Inherited safe claim:

- `compliance_desk_internal_package_record_landed`

## Boundary

The read surface consumes exactly one artifact: `compliance_desk_internal_package_record.json`.

Covered ladder steps now are:

1. `narrow_concierge_offer_card`
2. `fixture_spec`
3. `review_gate_checklist`
4. `reviewed_output_schema`
5. `local_reviewed_fixture`
6. `internal_package_record`
7. `coverage_summary_or_read_only_operator_surface`

Still required before any promotion:

1. `customer_output_schema_gate`
2. `internal_sample_output`
3. `explicit_approval_or_hold_decision`

## Surface shape

The surface exposes internal/admin cards only:

- package position
- evidence contract
- reviewed output
- limitations
- safe claims
- blocked claims

All cards are pass-through views over the internal package record. The surface performs no semantic reinterpretation, reads no raw transcripts, reads no raw fixtures, writes no customer copy, writes no live Acontext memory, enables no dispatch, emits no reputation receipts, exposes no GPS/raw metadata, and publishes no worker doctrine.

## Still blocked

This artifact does **not** make any of these true:

- customer copy readiness
- customer delivery approval
- public service catalog readiness
- controlled pilot / customer exposure
- publication approval
- live Acontext sink readiness or runtime parity
- autonomous dispatch or route assignment
- ERC-8004 reputation / reputation receipts
- worker Skill DNA or worker-copyable compliance doctrine
- exact GPS/raw metadata exposure
- legal compliance, legal sufficiency, regulator acceptance, filing success, city influence, official inspection, continuous monitoring, or guaranteed approval

## Guardrails

The module and loader fail closed if:

- the source package promotes readiness
- the surface changes scope, source package, or ladder boundary
- a forbidden safe claim appears
- blocked claims are dropped or overlap with safe claims
- readiness flags are promoted
- access policy becomes public/customer/worker/dispatch visible
- route registration flips true
- operator cards stop being pass-through/internal-only
- raw transcript authority, exact-location language, or regulator-acceptance language appears
- review checks stop blocking later promotion gates

## Test gates

- `py_compile` for the new module and tests
- Focused Compliance Desk read-surface + package tests: `25 passed`
- Full city-ops suite: `431 passed`

## Next safe slice

Create a Compliance Desk **customer-output schema gate** that consumes this read-only surface and still keeps publication, delivery, dispatch, reputation, runtime, privacy, legal/regulator, and worker-doctrine readiness false.
