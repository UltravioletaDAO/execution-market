# City as a Service — AAS Single-Boundary Approval Record Schema Gate Implementation

> Date: 2026-05-15 00:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service internal planning only  
> Status: schema gate for a future human approval record; not approval; not customer exposure

## What landed

Added the cautious next slice after the pending single-boundary approval request:

- `mcp_server/city_ops/aas_single_boundary_approval_record_schema_gate.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_approval_record_schema_gate.json`
- `mcp_server/tests/city_ops/test_aas_single_boundary_approval_record_schema_gate.py`
- exports in `mcp_server/city_ops/__init__.py`

## Source consumed

The schema gate consumes only:

- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_human_operator_approval_request.json`

The source request must still be pending, select exactly one Compliance Desk package-label boundary, record no human approval, pass no redactions by itself, authorize no delivery path, and keep all customer/public/catalog/pilot/dispatch/reputation/live-runtime/GPS/domain-authority/worker-doctrine flags blocked.

## New safe claim

`aas_single_boundary_approval_record_schema_gate_landed`

This means only: an internal/admin schema gate now defines the required shape of a later real human approval record.

It does **not** mean a human operator approved anything.

## Future approval record contract

The future record must include these fields:

- `source_request_id`
- `source_request_digest_sha256`
- `selected_boundary_key`
- `approved_text_boundary`
- `exact_approved_text`
- `approved_text_fields`
- `human_operator_approval_recorded`
- `human_operator_approval_reference`
- `approval_timestamp_utc`
- `redaction_checks_passed`
- `authorized_delivery_path`
- `approval_scope`
- `approvals_not_granted`
- `still_blocked_claims`

The gate marks every future field as `satisfied_by_this_gate=false`.

## Selected boundary remains held

The gate carries forward the same narrow request boundary:

- family: `Compliance Desk as a Service`
- offer: `visible_posting_notice_compliance_snapshot`
- candidate boundary: `internal_package_label_only`
- candidate text value: `Visible posting / notice compliance snapshot`

The current gate values remain:

- `human_operator_approval_recorded=false`
- `selected_boundary_approved=false`
- `approved_text_boundary_recorded=false`
- `redaction_checks_passed=false`
- `authorized_delivery_path=none_until_separate_human_operator_approval_record`
- `customer_delivery_path_authorized=false`
- `operator_publish_approval_recorded=false`
- `publication_approved=false`

## What remains blocked

The gate does not approve or imply:

- future human approval record creation
- human approval recorded
- selected text boundary approved
- redactions passed
- customer copy creation/readiness
- customer delivery or delivery path authorization
- publication
- public/catalog routes
- controlled pilots or front-door SKUs
- public prices or customer quotes
- operator queue launch
- dispatch
- ERC-8004 reputation receipts
- live Acontext/runtime parity
- exact GPS/raw metadata release
- legal/regulator/inspection/domain-authority claims
- worker Skill DNA or worker-copyable doctrine

## Fail-closed coverage

Tests cover:

- persisted artifact equality
- future approval-record fields being required but not satisfied by this gate
- selected boundary and redaction contract staying non-approval
- current gate values keeping approval/delivery/publication false
- customer/public/runtime/metadata claims remaining blocked
- valid write/load in temporary artifact directories
- source request failure on approval promotion, selected-boundary promotion, redaction passing, and delivery-path expansion
- loader failure on future-field self-satisfaction, current approval flips, and redaction self-passing

## Verification

Focused/adjacent gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_single_boundary_approval_record_schema_gate.py \
  mcp_server/tests/city_ops/test_aas_single_boundary_human_operator_approval_request.py \
  mcp_server/tests/city_ops/test_aas_packaging_pricing_operator_workflow_review_board.py
# 40 passed
```

Full city-ops suite:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 708 passed
```

Compile gate:

```bash
/opt/homebrew/bin/python3.14 -m py_compile \
  mcp_server/city_ops/aas_single_boundary_approval_record_schema_gate.py \
  mcp_server/tests/city_ops/test_aas_single_boundary_approval_record_schema_gate.py
# passed
```

## Next safe step

Only a real human operator can create the next artifact: a separate approval record for this exact Compliance Desk label boundary.

That future record must cite this schema gate and still must not authorize customer delivery, publication, public pricing, catalog/routes, queue launch, dispatch, reputation, live runtime, GPS/raw metadata release, domain-authority claims, or worker-copyable doctrine unless separate proof gates exist.
