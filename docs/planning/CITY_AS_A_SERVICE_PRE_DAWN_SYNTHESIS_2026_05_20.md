# City-as-a-Service — Pre-Dawn Synthesis (2026-05-20)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled the session. The cron payload still referenced AutoJob, Frontier Academy, and KK v2, but the active dream priority file explicitly stops those tracks. They were not pulled, analyzed, edited, or expanded.

Work stayed inside Execution Market AAS / City-as-a-Service.

## Night pattern

Tonight tightened two separate AAS control loops without turning either into customer/public readiness:

1. **Incident Verification approval loop** moved from a pending request into a complete internal validation shell for a future real human approval record.
2. **Coordination observability loop** converted the existing success-metrics board into a deterministic read-only internal/admin surface for future agents and daytime operators.

The key synthesis is that Execution Market AAS now has both:

- a stronger **single-family approval boundary** for Incident Verification; and
- a stronger **cross-session coordination boundary** for future AAS work.

Neither boundary authorizes delivery, publication, routing, dispatch, reputation, live runtime, exact GPS/raw metadata release, or worker-copyable doctrine.

## What connected tonight

The Incident Verification ladder now mirrors the Compliance Desk and Document / Handoff discipline, but remains deliberately held:

```text
package-review decision
→ pending human-operator approval request
→ read-only approval-request surface
→ future approval-record schema gate
→ executable approval-record validator
→ real approval record only after real human review
→ delivery/publication gate only after explicit delivery authorization
```

The coordination metrics surface adds a second reusable pattern:

```text
stable reviewed IDs
+ declared-vs-verified badges
+ sticky safe/blocked claims
+ one next-proof slot
= agent handoff that compounds without reopening raw transcripts or mutating runtime state
```

This is the product connection: AAS can scale safely only if service-family approval gates and agent-coordination handoffs use the same proof grammar. Every artifact should say what it proves, what it does not prove, and exactly what the next proof is.

## Current safe claims from tonight

```text
incident_verification_human_operator_approval_request_landed
incident_verification_approval_request_read_surface_landed
incident_verification_approval_record_schema_gate_landed
incident_verification_approval_record_validator_landed
admin_aas_coordination_observability_success_metrics_read_surface_landed
```

These claims are internal/admin-only.

## Still blocked

Do not infer any of the following from tonight's work:

```text
human_approval_created_by_validator
selected_boundary_approved_by_validator
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_or_public_route_ready
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
emergency_or_safety_or_repair_or_insurance_or_sla_or_official_report_or_fault_liability_authority
legal_or_regulator_or_notarial_or_custody_authority
worker_copyable_aas_doctrine
```

## Daytime recommendations

### 1. Best customer-exposure fork

Use the already-existing **Compliance Desk single-boundary human approval record**, not the Incident Verification validator, as the first delivery/publication-gate candidate:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_human_operator_approval_record.json
```

Expected default result: held, because the current approval record still says `authorized_delivery_path=none_no_customer_delivery_authorized`.

The delivery/publication gate should prove exact approved text, fresh redaction status, delivery-path authorization, and still-blocked claims. It should not create public routes, catalog readiness, dispatch, reputation receipts, live-runtime claims, or domain-authority claims.

### 2. Best no-exposure fork

Keep all families internal/admin-only and add a cross-family approval-state matrix:

- Compliance Desk: has one approval record, no delivery path.
- Document / Handoff: has pending approval request/read surface, no approval record.
- Incident Verification: has pending request/read surface/schema/validator, no approval record.

This would give daytime a compact dashboard of exactly where each AAS family sits without introducing customer/public claims.

### 3. Runtime-memory fork

Acontext remains blocked until Docker image pull/cache or trusted mirror, compose startup, localhost API/dashboard reachability, and a rebuilt empty readiness gate are proven. Do not attempt or claim live write/retrieve parity before those prerequisites are real.

## Morning handoff

Daytime should treat May 20 as a choice between three narrow moves:

1. **Compliance Desk delivery/publication gate** over the one real approval record, expected held by default.
2. **Cross-family approval-state matrix** preserving all blocked claims.
3. **Acontext prerequisite repair** before any runtime-memory parity attempt.

Verification after synthesis: `.venv/bin/python -m pytest -q mcp_server/tests/city_ops` passed with `1018 passed`.

AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped for dream work by `DREAM-PRIORITIES.md`.
