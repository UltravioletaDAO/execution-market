# City as a Service — AAS Single-Boundary Approval Record Validator Implementation

> Date: 2026-05-15 02:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal planning only
> Status: validator contract for a future human-created approval record; not approval; not delivery; not publication

## What landed

Added the next conservative gate after the operator review brief:

- `mcp_server/city_ops/aas_single_boundary_approval_record_validator.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_approval_record_validator.json`
- `mcp_server/tests/city_ops/test_aas_single_boundary_approval_record_validator.py`
- exports in `mcp_server/city_ops/__init__.py`

## Source consumed

The validator consumes only:

- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_operator_review_brief.json`

The source brief must still be an operator checklist only: no human approval recorded, no selected-boundary approval, no redactions passed, no customer copy, no delivery authorization, no publication, no public pricing/customer quote, no queue launch, no dispatch, no reputation, no live runtime/Acontext parity, no exact GPS/raw metadata release, no domain-authority claim, and no worker-copyable doctrine.

## New safe claim

`aas_single_boundary_approval_record_validator_landed`

This means only: an internal/admin validator contract now exists for checking a future human-created approval record before it is accepted.

It does **not** mean a human approval record exists.

## What the validator may accept later

The callable validator can accept only a future record that:

1. uses schema `city_ops.aas_single_boundary_human_operator_approval_record.v1`
2. references the exact source brief id and digest
3. references the source schema-gate id and digest carried by the brief
4. approves only the Compliance Desk `internal_package_label_only` boundary
5. keeps exact approved text equal to `Visible posting / notice compliance snapshot`
6. records a non-empty human-operator approval reference
7. records a UTC approval timestamp
8. marks every required redaction check passed with an evidence reference
9. keeps delivery path equal to `none_no_customer_delivery_authorized`
10. keeps scope equal to `selected_internal_package_label_only`
11. carries forward all still-blocked claims
12. keeps all future false flags false

## What remains blocked

The validator rejects or blocks:

- approval records created by the validator itself
- records without a human reference
- records without redaction evidence
- customer delivery authorization
- publication or publishability
- public/catalog routes or pilot readiness
- public prices or customer quotes
- operator queue launch
- dispatch
- ERC-8004 reputation receipts
- live Acontext/runtime parity
- exact GPS/raw metadata release
- domain-authority claims
- worker Skill DNA or worker-copyable doctrine

## Why this is useful

The previous step correctly stopped at “a human needs to review this.” This slice prepares the acceptance boundary without pretending the human action happened. Daytime can now create a real approval record later and run it through a fail-closed validator instead of hand-waving the transition from checklist to approval.

## Fail-closed coverage

Tests cover:

- persisted validator artifact equality
- validator artifact creating no approval and satisfying no future fields
- a valid future candidate record approving only the selected label boundary
- write/load in temporary artifact directories
- source brief self-approval rejection
- approved text drift rejection
- delivery authorization rejection
- missing redaction evidence rejection
- promoted false flag rejection
- public route promotion rejection

## Verification

Focused gate:

```bash
/opt/homebrew/bin/python3.14 -m py_compile \
  mcp_server/city_ops/aas_single_boundary_approval_record_validator.py \
  mcp_server/tests/city_ops/test_aas_single_boundary_approval_record_validator.py

/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_single_boundary_approval_record_validator.py
# 10 passed
```

## Next safe step

Keep the boundary held unless a real human operator creates the separate approval record. If such a record is created, validate it with `validate_aas_single_boundary_human_operator_approval_record(...)` before allowing even the narrow internal label approval to be treated as accepted.

Even a valid record must not authorize delivery, publication, public pricing, catalog/routes, queue launch, dispatch, reputation, live runtime, exact GPS/raw metadata release, domain-authority claims, or worker-copyable doctrine unless separate proof gates exist.
