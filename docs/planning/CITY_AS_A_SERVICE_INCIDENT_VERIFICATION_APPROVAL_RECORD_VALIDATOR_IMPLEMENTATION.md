# City-as-a-Service — Incident Verification Approval-Record Validator Implementation

**Date:** 2026-05-20 02:00 America/New_York
**Scope:** Execution Market AAS / City-as-a-Service / Incident Verification
**Status:** Implemented as an internal/admin validator contract only

## What landed

Added the next conservative rung after the Incident Verification approval-record schema gate:

- `mcp_server/city_ops/incident_verification_approval_record_validator.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/incident_verification_approval_record_validator.json`
- `mcp_server/tests/city_ops/test_incident_verification_approval_record_validator.py`
- exports in `mcp_server/city_ops/__init__.py`

The validator consumes only:

- `incident_verification_approval_record_schema_gate.json`

It produces only:

- a deterministic internal/admin validator artifact
- a callable validator for a **future** real human-created approval record

It does **not** create the approval record.

## Safe claim

Only this claim is newly safe:

- `incident_verification_approval_record_validator_landed`

## Why this rung matters

The 01:00 schema gate defined what a future Incident Verification human approval record must contain. The 02:00 validator turns that contract into executable guardrails before any record can be accepted.

This is intentionally different from approval:

| Artifact | Meaning | What it does not do |
|---|---|---|
| Approval request | asks for review | does not approve |
| Read surface | shows the pending request | does not approve |
| Schema gate | defines future record shape | does not approve |
| Validator | rejects invalid future records | does not approve |
| Human approval record | future separate artifact only | still would not authorize delivery/publication |

## Accepted future boundary

The validator can only accept a future record for exactly:

- `selected_text_boundary_key`: `incident_verification_internal_package_label`
- `approved_text_boundary`: `internal_package_label_only`
- `exact_approved_text`: `One-location incident state snapshot`

Any text drift fails closed.

## Future record requirements

A future human-created record must include:

- schema and allowed record status
- source schema-gate ID + digest
- source surface/request IDs + digest
- exact selected text boundary
- human operator approval reference
- UTC approval timestamp
- all required pre-approval checks passed with evidence references
- all redaction/authority checks passed with evidence references
- explicit incident-authority limits
- allowed delivery path: `still_none_unless_a_separate_delivery_approval_gate_exists`
- approval scope: `incident_verification_text_boundary_only_not_customer_delivery_publication_dispatch_or_incident_authority`
- all false flags preserved
- all blocked claims carried forward

## Fail-closed checks

The validator rejects:

- missing human approval reference
- invalid or non-UTC timestamp
- source gate/surface/request digest drift
- selected text drift
- missing precheck evidence
- missing redaction/authority evidence
- any delivery/publication/incident-authority authorization in redaction rows
- customer delivery/publication/route/catalog/pilot promotion
- public price/customer quote promotion
- queue launch or dispatch promotion
- reputation attachment promotion
- live Acontext/runtime parity promotion
- exact GPS/raw metadata release promotion
- raw transcript authority promotion
- emergency/safety/repair/insurance/SLA/official-report/fault-liability authority
- worker-copyable incident doctrine
- coordinate/private-authority leakage substrings

## Still blocked

This implementation still does **not** authorize:

- human approval record creation by the validator
- selected-boundary approval by the validator
- customer copy
- customer delivery
- publication
- public/catalog routes
- controlled pilot/front-door SKU
- public pricing/customer quotes
- operator queue launch
- dispatch
- ERC-8004 reputation
- worker Skill DNA
- live Acontext/runtime parity
- exact GPS/raw metadata release
- raw transcript authority
- emergency response
- safety certification
- repair diagnosis/completion
- insurance adjustment
- SLA uptime or availability guarantees
- official incident report issuance
- fault/liability assignment
- worker-copyable incident doctrine

## Verification

Focused verification:

```bash
.venv/bin/python -m pytest \
  mcp_server/tests/city_ops/test_incident_verification_approval_record_validator.py \
  mcp_server/tests/city_ops/test_incident_verification_approval_record_schema_gate.py \
  mcp_server/tests/city_ops/test_incident_verification_approval_request_read_surface.py
```

Result: `35 passed`

Full city-ops suite was also run after implementation.
