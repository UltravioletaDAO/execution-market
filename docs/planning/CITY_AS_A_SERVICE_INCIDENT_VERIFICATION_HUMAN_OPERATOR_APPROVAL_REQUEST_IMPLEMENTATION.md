# City-as-a-Service — Incident Verification Human-Operator Approval Request Implementation

Date: 2026-05-19

Scope: Execution Market AAS / City-as-a-Service internal/admin proof slice only

## What landed

Added the pending, no-approval human-operator approval-request slice for Incident Verification as a Service:

- `mcp_server/city_ops/incident_verification_human_operator_approval_request.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/incident_verification_human_operator_approval_request.json`
- `mcp_server/tests/city_ops/test_incident_verification_human_operator_approval_request.py`
- `mcp_server/city_ops/__init__.py` exports for build/load/write helpers

The request consumes only:

- `incident_verification_package_review_decision.json`

and keeps that source hold intact.

## Safe claim

```text
incident_verification_human_operator_approval_request_landed
```

Conservative meaning: an internal/admin pending request exists for a future human operator to review exactly one Incident Verification label/text boundary. It does **not** record approval.

## Current request boundary

```text
approval_request_status = pending_human_operator_review_not_approved
selected_text_boundary_count = 1
selected_text_boundary.key = incident_verification_internal_package_label
selected_text_boundary.candidate_text_value = One-location incident state snapshot
authorized_delivery_path.path = none_until_separate_human_operator_approval_record
```

The request explicitly requires later checks for source hold preservation, exact boundary preservation, field allowlist preservation, forbidden incident-authority classes, non-authorizing follow-on boundaries, privacy redaction, exact GPS/raw metadata reverification, raw transcript non-authority, and absence of emergency/safety/repair/insurance/SLA/official-report/fault-liability language.

## Still blocked

This does **not** approve customer copy, customer delivery, publication, public/catalog routes, controlled pilots, public pricing/customer quotes, queue launch, dispatch, reputation receipts, live Acontext/runtime parity, exact GPS/raw metadata release, raw transcript authority, emergency response, safety certification, repair diagnosis/completion, insurance adjustment, SLA uptime, official incident reporting, fault/liability assignment, worker Skill DNA, or worker-copyable incident doctrine.

## Guardrail fix included

While testing this slice, the Incident Verification package-review builder exposed a shallow-copy mutation hazard for `FOLLOW_ON_ESCALATION_BOUNDARIES`. The builder now copies follow-on boundary rows with `dict(row)` and checks `execution_market_action_authorized` before generic drift, so mutation tests remain deterministic and fail closed with the intended message.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest \
  mcp_server/tests/city_ops/test_incident_verification_package_review_decision.py \
  mcp_server/tests/city_ops/test_incident_verification_human_operator_approval_request.py \
  -q
# 23 passed
```

## 2026-05-19 23:25 verification update

The slice is now ready to commit with:

- `mcp_server/city_ops/__init__.py` exports for `build/load/write_incident_verification_human_operator_approval_request`
- restored `mcp_server/city_ops/__init__.py` exports for the existing delivery/publication gate helpers
- deterministic deep-copy handling for Incident Verification follow-on escalation boundary rows before embedding them in package-review artifacts

Verification rerun:

```bash
.venv/bin/python -m pytest mcp_server/tests/city_ops/test_incident_verification_package_review_decision.py mcp_server/tests/city_ops/test_incident_verification_human_operator_approval_request.py -q
# 23 passed

.venv/bin/python -m pytest mcp_server/tests/city_ops -q
# 972 passed
```
