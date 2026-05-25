# City-as-a-Service — Retail Reality Pending-Approval Status Card Implementation

Date: 2026-05-24 22:00 EDT

Scope: Execution Market AAS / City-as-a-Service internal/admin proof slice only

## What landed

Added the next safe Retail Reality rung after the pending human-operator approval request:

- `mcp_server/city_ops/retail_reality_pending_approval_status_card.py`
- `mcp_server/city_ops/__init__.py` exports for build/load/write helpers
- `mcp_server/city_ops/fixtures/aas_package_ladder/retail_reality_pending_approval_status_card.json`
- `mcp_server/tests/city_ops/test_retail_reality_pending_approval_status_card.py`

The card consumes only:

- `retail_reality_human_operator_approval_request.json`

and renders a deterministic internal/admin queue/status artifact for the pending request.

## Safe claim

```text
retail_reality_pending_approval_status_card_landed
```

Conservative meaning: an internal/admin status card exists for the pending Retail Reality approval request. It is read-only, digest-bound, and approval-adjacent; it does not become a human approval record or customer surface.

## Boundary preserved

```text
approval_request_status = pending_human_operator_review_not_approved
status_card_status = read_only_pending_approval_status_card_not_approval_not_customer_ready
authorized_delivery_path = none_until_separate_human_operator_approval_record
selected_text_boundary = digest + field names only
```

The status card preserves the source request digest and selected-boundary digest while hiding candidate text values.

## Internal/admin cards exposed

The artifact exposes exactly these internal/admin cards:

1. `pending_status` — source request id, source digest, and pending/not-approved status.
2. `selected_boundary_digest` — selected boundary key, digest, and field names only.
3. `review_requirements` — pre-approval/redaction/authority checks still required.
4. `blocked_claims` — inherited safe claims and still-blocked claims kept adjacent.

## What remains blocked

This does **not** record human approval, approve the selected boundary, create or rewrite customer copy, authorize customer delivery or publication, register public/catalog/network routes, enable pricing/quotes, launch a controlled pilot or operator queue, dispatch workers, attach reputation receipts, prove live runtime parity, expose exact GPS/raw metadata/private retail context, assert retail authority, or publish worker-copyable retail doctrine.

## Hardening notes

- `safe_to_claim` is checked against inherited request blockers plus status-card blockers.
- `do_not_claim_yet` must include both inherited request blockers and status-card blockers.
- Access-policy false flags include customer/public/catalog/dispatch/reputation/runtime paths plus exact-location/raw-metadata/private-context exposure.
- Queue/display cards fail closed if candidate text values are embedded.
- The loader validates the persisted status card against the pending source request before returning it.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_retail_reality_pending_approval_status_card.py \
  mcp_server/tests/city_ops/test_retail_reality_human_operator_approval_request.py
```

Result:

```text
23 passed
```

Broader suite:

```bash
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

Result:

```text
1250 passed
```

Final diff/secret checks are expected to run before commit.

## Next safe step

If no real human review exists, keep this as an internal/admin queue/status card only. Only with explicit human review should a separate Retail Reality human-operator approval record be created over the exact source boundary, passed redactions, authorized delivery path, and still-blocked claims. Do not mutate this status card into an approval record.
