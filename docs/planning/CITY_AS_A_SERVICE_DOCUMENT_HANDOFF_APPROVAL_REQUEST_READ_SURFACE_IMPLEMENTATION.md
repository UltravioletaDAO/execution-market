# City-as-a-Service — Document / Handoff Approval Request Read Surface Implementation

Date: 2026-05-19

Scope: Execution Market AAS / City-as-a-Service internal/admin proof slice only

## What landed

Added the next conservative Document / Handoff rung after the pending human-operator approval request:

- `mcp_server/city_ops/document_handoff_approval_request_read_surface.py`
- `mcp_server/city_ops/__init__.py` exports for build/load/write helpers
- `mcp_server/city_ops/fixtures/aas_package_ladder/document_handoff_approval_request_read_surface.json`
- `mcp_server/tests/city_ops/test_document_handoff_approval_request_read_surface.py`

The surface consumes only:

- `document_handoff_human_operator_approval_request.json`

and turns the pending approval request into read-only internal/admin operator cards.

## Safe claim

```text
document_handoff_approval_request_read_surface_landed
```

Conservative meaning: an internal/admin read surface now exists for the pending Document / Handoff approval request. It makes the exact selected boundary, unmet pre-approval checks, redaction/authority requirements, missing delivery path, and still-blocked claims visible without recording or implying human approval.

## Selected boundary preserved

```text
selected_text_boundary_key = document_handoff_internal_package_label
candidate_text_boundary = internal_package_label_only
approval_request_status = pending_human_operator_review_not_approved
surface_status = read_only_pending_request_surface_no_human_approval_recorded
authorized_delivery_path = none_until_separate_human_operator_approval_record
```

## Operator cards exposed

The surface exposes exactly these internal/admin cards:

1. `pending_boundary` — one exact text boundary, not approved.
2. `pre_approval_checks` — requirements visible, all unmet by this surface.
3. `redaction_and_authority_requirements` — requirements visible, all unmet by this surface.
4. `authorized_delivery_path` — explicit `none_until_separate_human_operator_approval_record`.
5. `review_queue` — future human-operator worklist only.
6. `claim_boundaries` — safe and blocked claims visible without softening.

## What remains blocked

This does **not** approve customer copy, customer delivery, publication, public/catalog routes, controlled pilots, public pricing/customer quotes, queue launch, dispatch, ERC-8004 reputation, worker Skill DNA, live Acontext/runtime parity, exact GPS/raw metadata release, raw transcript authority, legal service, notarial acts, private identity verification, guaranteed acceptance, filing success, custody guarantees, or worker-copyable handoff doctrine.

## Why this compounds

The previous artifact created a pending request. This slice gives operators an inspectable, deterministic read surface for that request while preserving every blocked claim. That creates a safer bridge from proof packets to a future admin UI route: the route can render the surface without becoming the approval mechanism or accidentally authorizing delivery/publication.

## Next safe step

If no human review exists, stay internal/admin only. The next smallest proof is a separate route/mount preflight or UI fixture that consumes this read surface and proves it remains non-customer-visible and unmounted from public network routes.

Only after real human review: create a separate human-operator approval record naming exact approved text, passed redactions, authorized delivery path, and still-blocked claims.

## Verification

Focused tests:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_document_handoff_approval_request_read_surface.py \
  mcp_server/tests/city_ops/test_document_handoff_human_operator_approval_request.py
```

Result:

```text
23 passed
```
