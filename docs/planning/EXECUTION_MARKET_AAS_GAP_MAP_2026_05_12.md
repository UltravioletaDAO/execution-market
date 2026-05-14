# Execution Market AAS Gap Map — CaaS-Derived Package Families (2026-05-12)

> Scope: Execution Market AAS / City-as-a-Service planning only.  
> Status: internal gap map; no runtime code change; not public copy; not customer-facing readiness.  
> Governing priority: `~/clawd/DREAM-PRIORITIES.md` keeps dream work on Execution Market AAS / CaaS and blocks stopped projects.

## 1. Current CaaS ladder inventory

### 1.1 Strategic and packaging spine

| Layer | Landed surface | References | Conservative meaning |
|---|---|---|---|
| CaaS master plan / thesis | Municipal concierge proof service, not broad city automation | `docs/planning/MASTER_PLAN_CITY_AS_A_SERVICE.md`, `docs/planning/CITY_AS_A_SERVICE_AAS_PACKAGING_AUDIT_2026_05_07.md` | Package one narrow reviewed municipal execution desk before any platform claim. |
| Phase 1 offer family | Three City Counter Ops offers: Counter Reality Check, Packet Submission Attempt, Posting Compliance Check | `docs/planning/CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`, `docs/planning/CITY_AS_A_SERVICE_SERVICE_CATALOG.md`, `docs/planning/CITY_AS_A_SERVICE_GO_TO_MARKET.md` | Offer-card planning exists; every claim must stay tied to reviewed artifacts and exclusions. |
| AAS adjacent map | CaaS primitives mapped to adjacent AAS concepts | `docs/planning/EXECUTION_MARKET_AAS_CONCEPT_MAP_2026_05_08.md` | Adjacent verticals may reuse the proof ladder only after preserving CaaS claim boundaries. |
| Day/night operating board | Current sequencing, blockers, and safe next seams | `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`, `docs/planning/CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_11.md` | The active state is internally reviewable, held, and not customer-exposed. |

### 1.2 Proof-anchor spine

The older proof-anchor ladder is the reusable control pattern for all AAS packages:

```text
reviewed municipal result
-> compact decision object
-> coordination / reuse / observability artifacts
-> internal/admin read surfaces
-> fail-closed route/readiness gates
-> transport parity only after proof preservation
```

Key landed references:

- `mcp_server/city_ops/contracts.py`
- `mcp_server/city_ops/decision_projection.py`
- `mcp_server/city_ops/coordination.py`
- `mcp_server/city_ops/reuse.py`
- `mcp_server/city_ops/session_rebuild_consumer.py`
- `mcp_server/city_ops/acontext_transport.py`
- `mcp_server/city_ops/acontext_live_preflight.py`
- `mcp_server/city_ops/operator_debug_surface.py`
- `mcp_server/city_ops/proof_observability.py`
- `mcp_server/city_ops/coordination_intelligence.py`
- `mcp_server/city_ops/proof_block_readiness.py`
- `mcp_server/city_ops/persisted_artifact_guardrail.py`
- `mcp_server/city_ops/decision_support_readiness_matrix.py`
- `mcp_server/city_ops/decision_support_matrix_card.py`
- `mcp_server/city_ops/decision_support_matrix_route_preflight.py`
- `mcp_server/city_ops/decision_support_matrix_operator_consumer.py`
- `mcp_server/city_ops/decision_support_matrix_operator_display_adapter.py`
- `mcp_server/city_ops/decision_support_route_handoff_packet.py`

Conservative meaning: this proves internal artifact discipline, claim-boundary preservation, pass-through operator/admin surfaces, and fail-closed route gates. It does **not** prove customer readiness, live Acontext readiness, runtime parity, dispatch, reputation, legal/regulator acceptance, or worker-copyable doctrine.

### 1.3 Phase 1 offer proof ladder

| Step | Landed surface | References | Current safe claim only |
|---|---|---|---|
| Offer fixture specs | Deterministic specs for all three Phase 1 offers | `mcp_server/city_ops/phase1_offer_fixture_specs.py`; `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/{counter_reality_check,packet_submission_attempt,posting_compliance_check}.json` | Fixture specs are ready for local reviewed examples. |
| Review schemas and normalizer | Output schema bundle and review normalizer | `mcp_server/city_ops/phase1_review_output_schemas.py`; `mcp_server/city_ops/phase1_review_normalizer.py`; `docs/planning/CITY_AS_A_SERVICE_PHASE_1_REVIEW_OUTPUT_SCHEMAS.md` | Reviewed outputs can be normalized locally. |
| Reviewed fixture registry | One reviewed fixture row per Phase 1 offer plus registry summary | `mcp_server/city_ops/phase1_reviewed_fixtures.py`; `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_reviewed_fixture_registry_summary.json` | Local reviewed fixture coverage exists for the three offers. |
| Operator coverage surfaces | Summary, persisted artifact, renderer, and read surface | `mcp_server/city_ops/phase1_operator_coverage_summary.py`; `phase1_operator_coverage_renderer.py`; `phase1_operator_coverage_read_surface.py`; matching JSON artifacts under `reviewed_outputs/` | Internal/admin coverage can be inspected without promoting readiness. |
| Internal package records | Conservative package records for all three offers | `mcp_server/city_ops/phase1_packet_submission_internal_package_record.py`; `phase1_remaining_offer_internal_package_records.py`; `phase1_*_internal_package_record.json` | Each offer has an internal package record sourced only from reviewed artifacts. |
| Controlled-pilot readiness board | Board consumes the three package records | `mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py`; `phase1_controlled_pilot_readiness_board.json` | All Phase 1 offers have internal records; readiness flags remain false. |
| Customer-output schema gate | Internal/admin allowed/forbidden future output fields | `mcp_server/city_ops/phase1_customer_output_schema_review_gate.py`; `phase1_customer_output_schema_review_gate.json` | Future output shape is reviewed; it is not customer copy. |
| Operator-reviewed sample outputs | One internal sample output per offer | `mcp_server/city_ops/phase1_operator_reviewed_sample_outputs.py`; `phase1_operator_reviewed_sample_outputs.json` | Samples exist internally and are not publishable. |
| Publication checklist | Publication prerequisites named while approvals stay false | `mcp_server/city_ops/phase1_sample_publication_approval_checklist.py`; `phase1_sample_publication_approval_checklist.json` | Checklist exists; publication is not approved. |
| Draft packet and hold decision | Copy-shaped draft cards plus explicit hold decision | `mcp_server/city_ops/phase1_customer_facing_draft_packet.py`; `phase1_draft_packet_operator_review_decision.py`; matching JSON artifacts | Draft packet is held: not approved, not publishable, not customer-deliverable. |
| Single-offer approval record boundary | Human-operator approval record for exactly `counter_reality_check` text boundary | `mcp_server/city_ops/phase1_offer_card_human_operator_approval_record.py`; `phase1_offer_card_human_operator_approval_record.json`; `docs/planning/CITY_AS_A_SERVICE_PHASE_1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_IMPLEMENTATION.md` | A record exists for one internal/admin offer-card text boundary only; no customer delivery or publication approval. |

## 2. Gaps before customer exposure

These are the remaining gaps before any customer-visible CaaS or adjacent AAS surface should exist.

1. **Customer-delivery approval is still missing.** The latest single-offer approval record authorizes only an internal/admin review record for a named operator queue. `operator_publish_approval`, `customer_delivery_approval`, and `publication_approved` remain false.
2. **Only one offer-card text boundary has a human approval record.** `counter_reality_check` has an internal approval record; the Packet Submission Attempt and Posting Compliance Check cards still need separate approval records before even internal customer-delivery review.
3. **No public/catalog route gate exists for Phase 1 offer cards.** Current route work is internal/admin proof-chain discipline. It must not be reused as customer catalog readiness.
4. **No controlled pilot authorization artifact exists.** The readiness board intentionally keeps pilot/customer exposure false.
5. **No live Acontext/runtime parity proof should be inferred.** Existing Acontext artifacts define contracts, transport fixtures, and preflight blockers; they do not prove a live sink or runtime parity.
6. **No dispatch or worker-instruction surface is approved.** The proof ladder preserves operator learning but blocks autonomous dispatch, worker Skill DNA, and worker-copyable municipal doctrine.
7. **Privacy/redaction gates are not customer-release gates.** The samples pass internal privacy/legal/non-guarantee checks, but exact GPS/raw metadata exposure remains blocked and publication remains false.
8. **No legal/regulator/filing-success claim is approved.** Output can describe reviewed evidence and limitations only; it cannot claim legal sufficiency, regulator acceptance, filing success, city influence, or approval.
9. **Adjacent AAS families have concept coverage, not their own proof coverage.** They must start with local fixtures, reviewed outputs, package records, and internal coverage summaries before any customer-facing package claim.

## 3. AAS package families that reuse the CaaS proof ladder

Promotion rule for every family below:

```text
one narrow concierge offer card
-> fixture spec
-> reviewed-output schema
-> local reviewed fixture
-> internal package record
-> coverage summary / read-only operator surface
-> customer-output schema gate
-> internal sample output
-> explicit approval/hold decision
```

No family may skip directly to public catalog, live dispatch, live memory, reputation, or worker instructions.

### 3.1 Compliance Desk as a Service

**Adjacent use case.** Evidence-backed checks for visible compliance state: posted notices, required signage, window/door notices, deadline-visible postings, and remediation proof snapshots.

**First concierge offer.** Visible Posting / Notice Compliance Snapshot.

**Required evidence.** Wide/context photo, close notice/photo proof, timestamp window, checklist of required visible elements, source type (`observed`, `documented`, `heard`), obstruction/legibility notes, reviewed limitations.

**Review gates.** Fixture spec; reviewed-output schema; privacy/redaction check; non-guarantee/legal-advice exclusion; internal package record; coverage row; customer-output schema gate; explicit hold/approval record.

**Explicit blocked claims.** Legal compliance, regulator acceptance, filing success, official inspection, city influence, continuous monitoring, exact GPS/raw metadata exposure, dispatch readiness, ERC-8004 reputation, worker-copyable compliance doctrine.

### 3.2 Property / Permit Desk as a Service

**Adjacent use case.** Property-facing permit and office reality checks: office/window routing, document pickup/drop-off attempt, posted permit state, exterior condition blocker, access condition, and next-step handoff.

**First concierge offer.** Single-Site Permit / Office Reality Check.

**Required evidence.** Target/site identifier, allowed access boundary, wide/close condition photos where permitted, office/window or portal state, form/version or routing evidence, accepted/rejected/redirected/blocked/inconclusive outcome status, next-step recommendation.

**Review gates.** Counter Reality Check and Packet Submission Attempt CaaS gates reused; package record must cite reviewed fixture IDs; schema gate must forbid legal sufficiency and filing success; human operator approval must name exactly one offer card before customer-delivery review.

**Explicit blocked claims.** Approval guarantee, permit approval, legal sufficiency, appraisal, tenant determination, trespass/access guarantee, broad office reuse, multi-jurisdiction playbook readiness, customer catalog readiness, worker-copyable municipal doctrine.

### 3.3 Incident Verification as a Service

**Adjacent use case.** Time-bound incident-state verification for a visible issue: damaged sign, blocked access, water leak evidence, outage-visible storefront, queue/closure state, obstruction, or before/after remediation snapshot.

**First concierge offer.** One-Location Incident State Snapshot.

**Required evidence.** Incident question, place/time window, wide/context photo, close evidence photo, severity taxonomy, uncertainty note, what was not checked, recommended next action, follow-on task trigger if another visit or specialist is needed.

**Review gates.** New fixture family should reuse CaaS `site_audit`, `measurement`, and proof-observability patterns; reviewed output must keep `safe_to_claim[]` adjacent to `do_not_claim_yet[]`; operator sample outputs must pass privacy and non-guarantee review before any approval record.

**Explicit blocked claims.** Emergency response, safety certification, repair diagnosis, repair completion, insurance adjustment, SLA uptime, official incident report, exact GPS/raw metadata exposure, live dispatch, reputation receipt, worker-copyable incident doctrine.

### 3.4 Document / Handoff Logistics as a Service

**Adjacent use case.** Bounded physical document movement: print/pickup/drop-off attempt, stamped receipt capture, certified-mail prep proof, wet-signature relay, and failed-handoff classification.

**First concierge offer.** Document Handoff Proof Run.

**Required evidence.** Chain-of-custody events inside scoped windows, pickup/drop-off timestamp, recipient/source type, receipt/stamp/photo where available, failed-handoff reason, queue/wait boundary, recommended next action.

**Review gates.** Reuse Packet Submission Attempt taxonomy; require reviewed handoff packet; forbid raw transcript authority; require customer-output schema gate before any draft; separate approval record per offer card.

**Explicit blocked claims.** Legal service, notarial act unless separately credentialed/scoped, guaranteed acceptance, identity verification beyond scoped evidence, custody guarantee outside documented windows, filing success, customer readiness, dispatch routing, ERC-8004 reputation.

### 3.5 Procurement / Admin Ops as a Service

**Adjacent use case.** Small administrative field operations that need verified local facts: vendor quote pickup, posted price check, counter availability, inventory-visible check, queue/wait estimate, pickup-ready proof, and receipt capture.

**First concierge offer.** Admin Counter / Vendor Reality Check.

**Required evidence.** Buyer question, target office/vendor, observed open/closed state, posted-hours or counter-status proof, quote/receipt/photo where allowed, source-type split, discrepancy summary, limitations, next-step recommendation.

**Review gates.** Reuse Counter Reality Check source-type separation and outcome normalization; add fixture spec before package record; require operator coverage summary and customer-output schema review before samples; hold publication until explicit approval record exists.

**Explicit blocked claims.** Procurement authority, vendor contract enforcement, guaranteed pricing/inventory beyond observation window, employee performance judgment, legal/compliance certification, unlimited waiting, public catalog readiness, live dispatch, worker-copyable vendor doctrine.

## 4. Recommended next 3 dream-sized implementation slices

All three slices are conservative and doc/planning or local-artifact oriented. None should create customer routes, public copy, dispatch, live Acontext writes, reputation receipts, exact GPS/raw metadata exposure, or worker-copyable doctrine.

1. **Phase 1 offer-card approval coverage matrix.** Add one internal planning/artifact slice that compares the three draft cards against the current approval-record boundary: approved fields, missing approvals, redaction checks, delivery-path limits, and still-blocked claims. Keep approvals false for unapproved offers.
2. **Adjacent AAS minimum-ladder template.** ✅ Landed at 2026-05-12 01:00 as `mcp_server/city_ops/aas_minimum_ladder_template.py`, with persisted artifact `mcp_server/city_ops/fixtures/aas_package_ladder/aas_minimum_ladder_template.json`, tests, and implementation note `docs/planning/EXECUTION_MARKET_AAS_MINIMUM_LADDER_TEMPLATE_IMPLEMENTATION.md`. Safe claim: `aas_minimum_ladder_template_landed` only.
3. **One adjacent-family fixture stub, held.** ✅ Compliance Desk landed at 2026-05-12 02:00 as `mcp_server/city_ops/compliance_desk_fixture_review_gate.py`, with persisted artifact `mcp_server/city_ops/fixtures/aas_package_ladder/compliance_desk_fixture_review_gate.json`, tests, and implementation note `docs/planning/EXECUTION_MARKET_COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_IMPLEMENTATION.md`. Safe claim: `compliance_desk_fixture_review_gate_landed` only.

### 4.1 Update after May 14 05:00 dream continuation

The adjacent-family ladder has now been exercised through an explicit internal/admin hold decision across three families:

- Compliance Desk has advanced through fixture gate, local reviewed fixture, internal package record, read-only operator surface, customer-output schema gate, internal sample output, and explicit hold decision. Safe latest claim: `compliance_desk_sample_output_review_decision_landed` only; still no customer/public/pilot/dispatch/reputation/live-runtime/GPS/legal/regulator/inspection/compliance/worker-doctrine readiness.
- Document / Handoff Logistics has advanced through fixture gate, local reviewed fixture, internal package record, read-only operator surface, customer-output schema gate, internal sample output, and explicit hold decision. Safe latest claim: `document_handoff_sample_output_review_decision_landed` only; still no customer/public/pilot/dispatch/reputation/live-runtime/GPS/legal-service/notarial/private-identity/guaranteed-acceptance/filing-success/custody-guarantee/worker-doctrine readiness.
- Incident Verification has advanced through fixture gate, local reviewed fixture, internal package record, read-only operator surface, customer-output schema gate, internal/admin sample output, and explicit hold decision. Safe latest claim: `incident_verification_sample_output_review_decision_landed` only; still no customer/public/pilot/dispatch/reputation/live-runtime/GPS/emergency-response/safety-certification/repair/insurance/SLA/official-report/fault-liability/worker-doctrine readiness.

Current next safe implementation slice: do **not** publish by default. If customer exposure is desired, create a separate human-operator approval artifact for exactly one held sample/text boundary, naming exact approved text, redactions, authorized delivery path, and still-blocked claims. If customer exposure is not desired, create an internal three-family AAS readiness matrix that summarizes current ladder step, latest safe claim, blocked authority class, readiness flags, and next smallest gate without broadening routes, dispatch, reputation, live runtime, exact GPS/raw metadata exposure, or worker-copyable doctrine.

### 4.2 Update after May 14 06:00 final seal

The internal three-family readiness matrix now exists as `docs/planning/CITY_AS_A_SERVICE_THREE_FAMILY_AAS_READINESS_MATRIX_2026_05_14.md`. It summarizes Compliance Desk, Document / Handoff Logistics, and Incident Verification at the same conservative ladder boundary: explicit internal/admin sample-output hold decision. This is a review shortcut only; it does not create customer copy, customer delivery approval, public/catalog routes, pilot exposure, dispatch, reputation, live Acontext/runtime parity, exact GPS/raw metadata release, domain-authority claims, or worker-copyable doctrine.

Daytime should treat the matrix as the decision fork: either approve exactly one held text boundary through a separate human-operator artifact, or keep all families held while packaging/pricing/operator workflow is reviewed.


## 5. Standing blocked claims

Until separate gates prove otherwise, every CaaS and adjacent AAS artifact must continue blocking:

- public readiness, customer readiness, customer-visible catalog, front-door SKU, controlled pilot exposure
- legal approval, legal sufficiency, filing success, regulator acceptance, city relationship or influence
- live dispatch, autonomous dispatch, worker Skill DNA, worker-copyable doctrine
- exact GPS/raw metadata exposure or raw transcript authority
- live Acontext sink readiness, runtime parity, durable live memory writes
- ERC-8004 reputation or reputation receipt attachment

The safe product direction remains: use CaaS to harden Execution Market's reviewed real-world execution primitive, then reuse that primitive cautiously across adjacent AAS packages only when each package carries its own reviewed evidence and blocked claims beside any safe claims.
