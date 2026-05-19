# Execution Market AAS Portfolio Implementation Plan — 2026-05-18

> Scope: Execution Market AAS planning only, grounded in existing City-as-a-Service and adjacent-AAS artifacts.  
> Status: internal/admin implementation plan; not public copy; not a customer catalog; not a dispatch plan; not live Acontext/runtime parity; not ERC-8004 reputation; not worker doctrine.  
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`.

## 1. Planning posture

Execution Market already has enough AAS proof discipline to plan a small portfolio, but not enough to expose that portfolio to customers or workers. The correct interpretation is:

```text
CaaS proof ladder = reusable control pattern
three adjacent families = internal/admin proof tracks
customer exposure = separate human-approved gate
runtime memory = separate Acontext parity gate
```

The portfolio plan below expands AAS implementation beyond the current City-as-a-Service ladder while preserving the current evidence boundary. It treats Compliance Desk, Document / Handoff Logistics, and Incident Verification as the first reusable adjacent families because they already have local artifacts through explicit hold decisions.

## 2. Current artifact map

### 2.1 Strategy and guardrail docs

| Artifact | Role in the portfolio plan | Safe meaning only |
|---|---|---|
| `EXECUTION_MARKET_AAS_CONCEPT_MAP_2026_05_08.md` | Maps CaaS primitives into adjacent AAS concepts. | Adjacent vertical concepts exist; they are not product approvals. |
| `EXECUTION_MARKET_AAS_MINIMUM_LADDER_TEMPLATE_IMPLEMENTATION.md` | Defines the required promotion ladder for adjacent AAS families. | A template exists; no family can skip gates. |
| `EXECUTION_MARKET_AAS_GAP_MAP_2026_05_12.md` | Tracks proof gaps and blocked claims. | Internal gap map; not customer readiness. |
| `CITY_AS_A_SERVICE_THREE_FAMILY_AAS_READINESS_MATRIX_2026_05_14.md` | Summarizes the three adjacent families at the same held boundary. | Review shortcut only; no customer/public route. |
| `CITY_AS_A_SERVICE_AAS_BLOCKED_CLAIM_TO_PROOF_MAP_2026_05_16.md` | Routes blocked claims to exact next proofs. | Implementation routing; not authority to publish, dispatch, or attach reputation. |
| `CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_05_18.md` and `CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_18.md` | Current handoff entrypoints. | One Compliance Desk text boundary has an internal approval record; all delivery/public/runtime claims stay blocked. |

### 2.2 Adjacent-family implementation artifacts

| Family | Current artifact chain | Latest safe claim | Current proof boundary |
|---|---|---|---|
| Compliance Desk | `compliance_desk_fixture_review_gate.json` -> `compliance_desk_local_reviewed_fixture.json` -> `compliance_desk_internal_package_record.json` -> `compliance_desk_operator_read_surface.json` -> `compliance_desk_customer_output_schema_gate.json` -> `compliance_desk_internal_sample_output.json` -> `compliance_desk_sample_output_review_decision.json` -> `aas_single_boundary_human_operator_approval_record.json` | `aas_single_boundary_human_operator_approval_record_landed` | Exactly one package-label text boundary is internally approved: `Visible posting / notice compliance snapshot`; authorized delivery path remains `none_no_customer_delivery_authorized`. |
| Document / Handoff Logistics | `document_handoff_fixture_review_gate.json` -> `document_handoff_local_reviewed_fixture.json` -> `document_handoff_internal_package_record.json` -> `document_handoff_operator_read_surface.json` -> `document_handoff_customer_output_schema_gate.json` -> `document_handoff_internal_sample_output.json` -> `document_handoff_sample_output_review_decision.json` | `document_handoff_sample_output_review_decision_landed` | Internal/admin sample output is held. No delivery, publication, legal-service, notarial, identity, guaranteed-acceptance, custody, or filing-success claim. |
| Incident Verification | `incident_verification_fixture_review_gate.json` -> `incident_verification_local_reviewed_fixture.json` -> `incident_verification_internal_package_record.json` -> `incident_verification_operator_read_surface.json` -> `incident_verification_customer_output_schema_gate.json` -> `incident_verification_internal_sample_output.json` -> `incident_verification_sample_output_review_decision.json` | `incident_verification_sample_output_review_decision_landed` | Internal/admin sample output is held. No emergency, safety, repair, insurance, SLA, official-report, fault/liability, dispatch, or public claim. |

### 2.3 Shared portfolio control artifacts

| Artifact | Reuse purpose | What it does not prove |
|---|---|---|
| `aas_three_family_packaging_review_packet.json` | Compares labels, pricing inputs, and workflow questions across the three held families. | Does not approve packages, quotes, catalog, routes, queues, dispatch, or worker copy. |
| `aas_packaging_pricing_operator_workflow_review_board.json` | Internal/admin board for package/pricing/workflow review questions. | Does not create public pricing, customer quotes, or operator queue launch. |
| `aas_single_boundary_human_operator_approval_request.json` | Selects one Compliance Desk text boundary for possible review. | Does not approve the boundary. |
| `aas_single_boundary_approval_record_schema_gate.json` | Defines required fields for a future approval record. | Does not satisfy those fields. |
| `aas_single_boundary_approval_record_validator.json` | Fail-closed validator contract for a future real approval record. | Does not create approval. |
| `aas_single_boundary_human_operator_approval_record.json` | Records one narrow internal Compliance Desk package-label approval. | Does not approve delivery, publication, route/catalog, pricing, queue, dispatch, reputation, live runtime, GPS/raw metadata release, domain authority, or worker doctrine. |

## 3. Reusable proof ladder for every AAS family

Every AAS family must use this ladder before any customer or worker surface exists:

```text
1. narrow concierge offer card
2. fixture/review gate
3. reviewed-output schema
4. local reviewed fixture
5. internal package record
6. read-only operator surface or coverage summary
7. customer-output schema gate
8. internal/admin sample output
9. explicit hold or one-boundary approval decision
10. delivery/publication gate, only if a human-approved boundary exists
11. route/catalog/pilot/queue/dispatch/reputation/runtime gates, each separate and fail-closed
```

Rules that travel through every rung:

- `safe_to_claim[]` and `do_not_claim_yet[]` must stay adjacent.
- Source artifact IDs and digests should travel forward when available.
- Declared-vs-verified badges must not be collapsed into confidence language.
- A route, read surface, or review board may render proof state; it may not interpret itself into readiness.
- CaaS proof discipline is reusable; CaaS proof coverage is not automatically transferable to another family.

## 4. Per-family implementation plan

### 4.1 Compliance Desk as a Service

**Current state.** This is the most advanced adjacent family. It has the full internal/admin ladder and one internal package-label approval record for `Visible posting / notice compliance snapshot`.

**Immediate next proof if customer exposure is desired.** Build a separate delivery/publication gate that consumes only `aas_single_boundary_human_operator_approval_record.json` and proves:

1. approved text parity against the approval record;
2. redaction evidence rechecked at delivery time;
3. explicit delivery path authorization, if any;
4. publication/customer-delivery approval, if granted by a human operator;
5. all unrelated flags still false.

**Immediate next proof if customer exposure is not desired.** Keep the boundary internal and add an internal review decision over package label, pricing input, and operator workflow question only.

**Blocked after the next proof unless separately gated.** Legal compliance, regulator acceptance, official inspection, filing success, city influence, public catalog, public pricing, queue launch, dispatch, reputation, live runtime/Acontext, exact GPS/raw metadata release, and worker-copyable compliance doctrine.

### 4.2 Document / Handoff Logistics as a Service

**Current state.** The family has the full internal/admin ladder through a held sample-output review decision for `document_handoff_proof_run`.

**Immediate next proof if this family becomes the next customer-exposure candidate.** Do not reuse the Compliance Desk approval. Create a new single-boundary approval request for exactly one Document / Handoff text boundary, then require the same schema gate, operator brief, fail-closed validator, and real human approval record sequence.

**Immediate next proof if kept internal.** Create a Document / Handoff package-review decision that answers only:

1. which internal label remains safest;
2. which handoff evidence fields are allowed in a future customer-output schema;
3. which custody, identity, notarial, legal-service, and acceptance phrases remain forbidden;
4. which exact next gate would be needed before any delivery path exists.

**Blocked after the next proof unless separately gated.** Legal service, notarial act, private identity verification, guaranteed acceptance, custody guarantee outside documented windows, filing success, public/customer readiness, dispatch routing, reputation receipts, and worker-copyable handoff doctrine.

### 4.3 Incident Verification as a Service

**Current state.** The family has the full internal/admin ladder through a held sample-output review decision for `one_location_incident_state_snapshot`.

**Immediate next proof if this family becomes the next customer-exposure candidate.** Create a new single-boundary approval request for exactly one Incident Verification text boundary. The approval chain must explicitly reject emergency, safety, repair, insurance, SLA, official-report, and fault/liability language before any delivery gate is considered.

**Immediate next proof if kept internal.** Create an Incident Verification package-review decision that focuses on severity taxonomy, uncertainty language, follow-on-task triggers, and what must be routed to a specialist or emergency channel instead of Execution Market.

**Blocked after the next proof unless separately gated.** Emergency response, safety certification, repair diagnosis/completion, insurance adjustment, SLA uptime, official incident report, fault/liability finding, public/customer readiness, dispatch, reputation, live runtime, exact GPS/raw metadata release, and worker-copyable incident doctrine.

## 5. Customer-exposure gates

AAS customer exposure is not a boolean. It must be broken into gates:

| Gate | Required input | Allowed output | Must remain false unless independently proven |
|---|---|---|---|
| Text-boundary approval | One held sample/output or package-label boundary, one human approval record, validator pass. | Approval for exactly the named text boundary. | Delivery, publication, route, price, queue, dispatch, reputation, runtime, GPS/raw metadata, domain authority, worker doctrine. |
| Delivery/publication gate | Valid text-boundary approval plus delivery-time redaction/domain-authority checks. | Exact authorized delivery path and publication/customer-delivery decision, if human-approved. | Catalog, pilot, queue launch, dispatch, reputation, runtime parity, worker instructions. |
| Public/catalog route gate | Delivery/publication decision plus route preflight and fail-closed rendering. | A route may render only approved text and blocked claims. | Pricing, queue launch, autonomous dispatch, reputation, runtime memory, legal/regulator authority. |
| Pricing/quote gate | Separate price policy and operator approval. | Internal or customer-visible price only for the named scope. | Launch queue, dispatch, worker doctrine, acceptance/authority claims. |
| Queue/dispatch gate | Separate operator workflow authorization and worker-copyability review. | A bounded operator queue or dispatch instruction, if approved. | Autonomous routing, reputation receipts, domain authority, exact metadata exposure. |
| Reputation gate | Separate event-source, signer, identity, privacy, and rollback semantics. | Reputation receipt eligibility for exactly the proven event. | Customer truth, payment freshness, legal authority, worker doctrine. |

For May 18, only the first row has a narrow Compliance Desk internal/admin record. The delivery/publication row is still the next unproven gate.

## 6. Runtime / Acontext blocker path

Runtime memory is an independent launch-control switch. It must not be inferred from package progress.

**Current blocker summary.** Existing Acontext artifacts show progress in diagnostics, not readiness:

- Docker and Compose assets exist.
- A dedicated SDK virtualenv exists.
- GHCR manifests are reachable and advertise `linux/arm64`.
- Docker/buildx are locally reachable.
- The first GHCR Acontext image pull still timed out silently in bounded retries.
- Required image inventory, compose startup, API/dashboard reachability, empty readiness gate, and live write/retrieve parity remain unproven.

**Only allowed runtime path:**

```text
fix/bypass Docker layer-fetch stall or use trusted image cache/mirror
-> verify all required Acontext images are locally present
-> start compose
-> healthcheck local API and dashboard
-> rerun read-only preflight
-> rebuild blocker delta/read surface/readiness gate
-> run exactly one live write/retrieve parity pass only if the rebuilt gate has empty blockers
-> record safe + blocked claims together
```

Even a successful runtime parity pass would not approve customer delivery, public routes, pricing, queue launch, dispatch, reputation, payment/production freshness, GPS/raw metadata release, domain authority, or worker doctrine.

## 7. Portfolio sequencing recommendation

### Default morning path

1. Treat `CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_05_18.md` as the current entrypoint.
2. Choose exactly one lane:
   - **Customer-exposure lane:** build the Compliance Desk delivery/publication gate over the existing approval record.
   - **Runtime-memory lane:** clear Acontext image/service prerequisites and attempt one gated parity pass only if blockers are empty.
   - **Internal portfolio lane:** keep all families held and add one package-review decision for Document / Handoff or Incident Verification.
3. Do not mix lanes in one proof. Each lane has different authority and different failure modes.

### Recommended next no-human/no-live-runtime slice

If no human delivery approval and no Acontext runtime fix are available, the safest next implementation is:

```text
Document / Handoff Logistics package-review decision
```

Reason: it exercises the portfolio pattern beyond Compliance Desk while staying internal/admin, has a complete held ladder, and forces the chain-of-custody/legal-service/notarial/identity blocked claims to stay explicit before any future approval request.

### Recommended next human-review slice

If a human operator is available, the most constrained next proof is:

```text
Compliance Desk delivery/publication gate over the already approved package-label boundary
```

The gate should default to `delivery_path=none` unless explicitly approved, and should stop after recording the decision. It should not create a catalog route, price, queue, dispatch, reputation receipt, runtime write, or worker instruction.

### Recommended next runtime slice

If runtime memory is the priority, do not touch the adjacent-family package ladder. Work only on trusted Acontext image inventory and local service health until a rebuilt readiness gate is empty.

## 8. Morning handoff checklist

Before the next agent claims progress, verify the chosen lane against this checklist:

- [ ] One lane chosen: customer-exposure, runtime-memory, or internal portfolio.
- [ ] Source artifact IDs named.
- [ ] Latest safe claim named exactly.
- [ ] Blocked claims repeated beside the safe claim.
- [ ] No customer/public/dispatch/reputation/runtime/payment/GPS/domain-authority/worker-doctrine claim introduced without a separate gate.
- [ ] Pre-existing `scripts/sign_req.mjs` remains untouched.
- [ ] If docs only, run doc sanity checks rather than broad tests.

## 9. Stop conditions

Stop and produce only an internal handoff if any of these appear:

- a customer-facing phrase is drafted before a delivery/publication gate exists;
- delivery path is implied instead of explicitly authorized;
- a read surface adds interpretation instead of pass-through state;
- a package review turns into public pricing, queue launch, or dispatch instructions;
- a runtime-memory claim appears before local Acontext API/dashboard health and a single gated write/retrieve pass;
- exact GPS/raw metadata, raw transcript authority, private operator context, legal/regulator authority, emergency/safety/repair/insurance/SLA/official-report/fault-liability language, or worker-copyable doctrine would be exposed.

This plan is therefore a portfolio implementation plan, not a launch plan: it tells the next agent how to advance one exact proof without converting internal/admin evidence into customer, dispatch, runtime, reputation, legal, GPS, payment, or worker-doctrine claims.
