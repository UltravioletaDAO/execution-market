# Execution Market AAS Minimum Ladder Template Implementation

> Date: 2026-05-12 01:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service adjacent package planning
> Status: internal/admin planning artifact only; not customer copy; not a public catalog; not dispatch; not live Acontext/runtime parity; not ERC-8004 reputation; not worker doctrine.

## What landed

Added a deterministic internal template that turns the City-as-a-Service proof ladder into the minimum required artifact sequence for adjacent AAS package families.

Files:

- `mcp_server/city_ops/aas_minimum_ladder_template.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_minimum_ladder_template.json`
- `mcp_server/tests/city_ops/test_aas_minimum_ladder_template.py`
- exports in `mcp_server/city_ops/__init__.py`

Safe claim added:

- `aas_minimum_ladder_template_landed`

## Required promotion ladder

Every adjacent AAS package must start with this sequence before any promotion:

1. `narrow_concierge_offer_card`
2. `fixture_spec`
3. `reviewed_output_schema`
4. `local_reviewed_fixture`
5. `internal_package_record`
6. `coverage_summary_or_read_only_operator_surface`
7. `customer_output_schema_gate`
8. `internal_sample_output`
9. `explicit_approval_or_hold_decision`

No adjacent family can skip directly from concept map to customer copy, catalog, public route, live dispatch, reputation, live memory, exact GPS/raw metadata exposure, legal/regulator claims, or worker-copyable doctrine.

## Covered adjacent package families

The template currently defines five CaaS-derived AAS families:

| Family | First concierge offer | CaaS source pattern |
|---|---|---|
| Compliance Desk as a Service | Visible Posting / Notice Compliance Snapshot | `posting_compliance_check` |
| Property / Permit Desk as a Service | Single-Site Permit / Office Reality Check | `counter_reality_check + packet_submission_attempt` |
| Incident Verification as a Service | One-Location Incident State Snapshot | `site_audit + measurement + proof_observability` |
| Document / Handoff Logistics as a Service | Document Handoff Proof Run | `packet_submission_attempt` |
| Procurement / Admin Ops as a Service | Admin Counter / Vendor Reality Check | `counter_reality_check` |

Each row carries required evidence, its own specific blocked claims, the shared blocked-claim list, and readiness flags that must remain false until separate family-specific artifacts prove otherwise.

## Guardrails

The module and loader fail closed if:

- a required family is missing or added out of band
- the promotion ladder changes unexpectedly
- forbidden readiness claims appear in `safe_to_claim[]`
- global or family readiness flags are promoted
- blocked claims are dropped
- a family loses its required evidence or specific blocked claims

This keeps the AAS expansion reusable without accidentally converting planning into customer-facing readiness.

## Still blocked

The template explicitly does **not** make any of these true:

- customer copy readiness
- customer-visible catalog or public service catalog
- controlled concierge pilot exposure
- operator publish approval, customer delivery approval, or publication approval
- live Acontext sink readiness or runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation / reputation receipts
- worker Skill DNA or worker-copyable doctrine
- exact GPS/raw metadata exposure
- legal sufficiency, regulator acceptance, filing success, city influence, or guaranteed approval

## Next safe slice

Pick one adjacent family and add only its fixture spec plus review-gate checklist.

Recommended first choices:

1. **Compliance Desk as a Service** — closest reuse of `posting_compliance_check`.
2. **Document / Handoff Logistics as a Service** — closest reuse of `packet_submission_attempt`.

Keep all customer/public/dispatch/reputation/privacy/worker-doctrine readiness flags false by default.
