# City-as-a-Service — Pre-Dawn Synthesis (2026-05-19)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled the session. The stale cron payload requested AutoJob, Frontier Academy, and KK v2 work, but the active dream priority file explicitly stops those tracks. They were not pulled, analyzed, edited, or expanded.

Work stayed inside Execution Market AAS / City-as-a-Service.

## Night pattern

Tonight tightened the adjacent-AAS package ladder instead of expanding into public surfaces:

1. **Document / Handoff** moved from package-review decision to a pending human-operator approval request and then to a read-only internal/admin approval-request surface.
2. **Incident Verification** moved from sample-output hold to package-review decision.
3. **Compliance Desk** remains the only family with an actual single-boundary human-operator approval record, and even that record authorizes no customer delivery path.

The important synthesis: the AAS ladder now has three conservative family lanes with comparable proof posture:

| Family | Current strongest internal artifact | Customer/public exposure? | Next safe gate |
| --- | --- | --- | --- |
| Compliance Desk | single-boundary human-operator approval record for `Visible posting / notice compliance snapshot` | No. `authorized_delivery_path=none_no_customer_delivery_authorized` | separate delivery/publication gate or explicit delivery-path approval |
| Document / Handoff | pending approval-request read surface for `Document handoff proof run` | No. request is pending, not approved | real approval record only after human review; otherwise route/mount preflight remains internal-only |
| Incident Verification | package-review decision for `One-location incident state snapshot` | No. package decision requires separate human approval before any delivery path | approval request/read surface, or keep held for packaging review |

## What connected tonight

The earlier CaaS proof ladder has become a reusable AAS packaging discipline:

- **Fixture → package record → operator/read surface → customer-output schema → internal sample → explicit hold/package decision → approval request/approval record → delivery gate.**
- Each rung preserves `safe_to_claim` beside `do_not_claim_yet`.
- A family is not customer-ready merely because it has copy-shaped fields, sample outputs, package labels, or an approval request.
- Even a human approval record is not a delivery authorization unless it explicitly names redactions, exact text, delivery path, and still-blocked claims.

This makes Execution Market AAS safer to scale: new verticals can reuse the ladder without accidentally claiming public launch, legal authority, dispatch readiness, live memory parity, or worker-copyable doctrine.

## Current safe claims from tonight

```text
document_handoff_package_review_decision_landed
document_handoff_human_operator_approval_request_landed
document_handoff_approval_request_read_surface_landed
incident_verification_package_review_decision_landed
```

These claims are internal/admin-only.

## Still blocked

Do not infer any of the following from tonight's work:

```text
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
controlled_pilot_ready
public_pricing_or_customer_quote_ready
operator_queue_launch_ready
autonomous_dispatch_ready
erc8004_reputation_ready
worker_skill_dna_ready
live_acontext_runtime_parity
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
raw_transcript_authority
legal_or_regulator_or_notarial_or_custody_authority
emergency_or_safety_or_repair_or_insurance_or_sla_or_official_report_authority
worker_copyable_aas_doctrine
```

## Daytime recommendations

### 1. Customer-exposure path, if Saúl wants it

Start from the **existing Compliance Desk approval record**, not Document / Handoff or Incident Verification. Build a separate delivery/publication gate over:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_human_operator_approval_record.json
```

The gate should stay held unless a real delivery path is explicitly authorized. It must prove exact approved text, redaction status, delivery-path authorization, and still-blocked claims.

### 2. Internal ladder path, if no customer exposure today

Keep all families internal/admin-only and add one narrow proof-support artifact:

- Document / Handoff route/mount preflight over the approval-request read surface, failing closed for public/customer access; or
- Incident Verification approval request/read surface over the package-review decision; or
- a cross-family packaging/pricing/operator-workflow comparison that keeps every delivery flag false.

### 3. Runtime-memory path

Acontext remains blocked on Docker Desktop / containerd / network / layer-fetch behavior or a trusted image cache/mirror. Do not attempt a live write/retrieve parity pass until the image inventory, compose startup, API/dashboard health, and rebuilt readiness gate are clean.

## Morning handoff

The daytime handoff is conservative by design: Execution Market AAS has better packaging proof, but not launch readiness. The best next move is to choose one branch explicitly:

1. **Compliance Desk delivery gate** for the one already approved text boundary; or
2. **No-exposure internal packaging review** across the three AAS families; or
3. **Acontext prerequisite repair** before any runtime-memory claims.

AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped for dream work by `DREAM-PRIORITIES.md`.
