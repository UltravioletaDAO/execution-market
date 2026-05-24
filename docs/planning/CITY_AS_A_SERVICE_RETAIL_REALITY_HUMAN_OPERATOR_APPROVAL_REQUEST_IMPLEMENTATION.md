# City-as-a-Service — Retail Reality Human-Operator Approval Request Implementation

> Date: 2026-05-24 04:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin Retail Reality ladder only
> Safe claim: `retail_reality_human_operator_approval_request_landed`

## Why this exists

`~/clawd/DREAM-PRIORITIES.md` overrides the stale cron payload: AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped. This slice keeps the work strictly inside Execution Market AAS / City-as-a-Service.

Retail Reality had already reached an explicit **hold** decision over an internal/admin sample output. The next smallest safe rung was not customer exposure; it was a pending human-operator approval request that names exactly what a human could review later while still recording no approval.

## Files added

- `mcp_server/city_ops/retail_reality_human_operator_approval_request.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/retail_reality_human_operator_approval_request.json`
- `mcp_server/tests/city_ops/test_retail_reality_human_operator_approval_request.py`

`mcp_server/city_ops/__init__.py` now exports the Retail Reality ladder helpers, including the new request builder/loader/writer.

## Source artifacts

The request consumes only the existing Retail Reality internal/admin artifacts:

- `retail_reality_internal_sample_output.json`
- `retail_reality_sample_output_review_decision.json`

It validates that the source decision is still `hold_not_approved_not_publishable`, the sample is still synthetic/internal-only, and the exact selected sample-text boundary is digest-bound.

## What landed

The new artifact records:

1. `approval_request_status = pending_human_operator_review_not_approved`
2. one selected text boundary: all allowed internal sample field values only;
3. a SHA-256 digest over the selected text values;
4. required pre-approval checks, all pending/false;
5. required redaction and authority checks, all pending/false;
6. `authorized_delivery_path = none_until_separate_human_operator_approval_record`;
7. every customer/public/pricing/dispatch/reputation/runtime/location/retail-authority/worker-doctrine flag false.

## Still blocked

This request does **not** approve or imply:

- human-operator approval record;
- customer copy or customer delivery;
- publication, route, catalog, controlled pilot, or front-door SKU;
- pricing or customer quote;
- operator queue launch or dispatch;
- ERC-8004 reputation or worker Skill DNA;
- live Acontext/runtime parity;
- exact GPS/raw metadata or private retail context release;
- permanent business-status, inventory, brand-compliance, employee-performance, consumer-safety, or continuous-monitoring claims;
- worker-copyable retail doctrine.

## Pattern insight

The multiplier pattern is: **approval requests are useful product infrastructure when they preserve the exact candidate boundary and keep approval absent by construction.**

This gives Saúl a daytime decision point without accidental launch semantics:

```text
hold decision -> pending approval request -> separate approval record if and only if a human explicitly approves
```

The key is that the request carries the candidate text digest, redaction checklist, delivery-path requirement, and blocked claims together. That makes later approval auditable instead of inferred from surrounding artifacts.

## Verification

```bash
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_retail_reality_*.py
# 106 passed

.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1239 passed
```

## Next safe step

Only if Saúl wants to review Retail Reality customer exposure: create a separate Retail Reality human-operator approval record that names the exact approved text, passed redactions, authorized delivery path, and still-blocked claims. Default remains hold.
