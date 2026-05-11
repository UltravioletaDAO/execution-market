# City as a Service — Pre-Dawn Synthesis 2026-05-11

> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`  
> Branch: `feat/operator-route-regret-panel`  
> Synthesis time: 05:00 America/New_York

## 1. Priority reconciliation

The cron payload still carried old priorities for AutoJob, Frontier Academy, KK v2, and other tracks. `~/clawd/DREAM-PRIORITIES.md` explicitly says those are stopped during dreams, so the night stayed on Execution Market AAS / City-as-a-Service.

No AutoJob integration, Frontier guide expansion, KK v2 work, or KarmaCadabra v2 work was performed.

## 2. What the night actually built

The night moved Phase 1 City Counter Ops from internal package coverage to a held, reviewable customer-output ladder:

1. **All three internal package records exist**
   - Packet Submission Attempt
   - Counter Reality Check
   - Posting Compliance Check
2. **Customer-output schema review gate exists**
   - allowed fields are narrow and customer-safe
   - forbidden fields include exact GPS, raw metadata, raw transcript authority, legal sufficiency, regulator acceptance, dispatch instructions, and reputation receipts
3. **Operator-reviewed internal sample outputs exist**
   - one per offer
   - privacy/legal/non-guarantee review flags stay explicit
4. **Sample publication approval checklist exists**
   - records required gates without granting approval
5. **Customer-facing draft packet exists**
   - copy-shaped but internal/admin-only
   - not customer copy, not ready, not publishable
6. **Draft packet hold decision exists**
   - `review_decision=hold_not_approved_not_publishable`
   - `operator_review_recorded=true`
   - `operator_review_granted=false`
   - every offer card held for explicit human operator review

## 3. Safe claims now available

Only these new Phase 1 claims are safe from tonight's CaaS work:

- `phase1_counter_reality_check_internal_package_record_landed`
- `phase1_posting_compliance_internal_package_record_landed`
- `phase1_customer_output_schema_review_gate_landed`
- `phase1_operator_reviewed_sample_outputs_landed`
- `phase1_sample_publication_approval_checklist_landed`
- `phase1_customer_facing_draft_packet_landed`
- `phase1_draft_packet_operator_review_decision_landed`

Plain English: the internal/admin proof ladder exists, and it is intentionally holding before customer exposure.

## 4. Still not safe to claim

Do **not** claim any of the following yet:

- operator approval or publication approval
- customer delivery approval
- customer copy readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA
- worker-copyable municipal doctrine
- legal sufficiency, regulator acceptance, filing success, broad office reuse, city relationship, or guaranteed approval
- exact GPS/raw metadata exposure

## 5. Strategic interpretation

This was not a route-building night. It was a **claim-boundary hardening** night.

That matters because customer-facing municipal assistance is risky in two ways:

1. It is easy to overclaim outcomes: approval, acceptance, legal sufficiency, or city influence.
2. It is easy to leak operational knowledge: raw metadata, exact location, private operator context, or reusable municipal playbooks.

The new ladder makes the future customer-output path reviewable without making it public or sellable by accident.

## 6. Daytime recommendation

If Saúl wants to move toward customer exposure, the next daytime slice should be narrow:

> create a separate human operator approval artifact for exactly one offer card.

That artifact should name:

1. which offer card is approved,
2. the exact approved text or section IDs,
3. which privacy/redaction checks passed,
4. the authorized delivery path,
5. which claims remain blocked.

Do not flip `publication_approved` from the hold artifact. Do not create a public route, customer catalog, pilot landing page, dispatch integration, reputation receipt, or Acontext runtime claim as part of that approval.

## 7. Verification state

Latest gates:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_draft_packet_operator_review_decision.py
# 12 passed

/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 336 passed
```

Repo note: the pre-existing untracked `scripts/sign_req.mjs` remains untouched.
