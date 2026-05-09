# Execution Market AAS Concept Map — CaaS-Derived Adjacent Verticals (2026-05-08)

> Scope: Execution Market AAS planning only.  
> Status: internal concept map, not public copy, not customer-facing claims.  
> Lead wedge: City-as-a-Service remains primary.

## 1. Source inventory

Inspected sources:

- `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`
- `docs/planning/MASTER_PLAN_CITY_AS_A_SERVICE.md`
- `docs/planning/CITY_AS_A_SERVICE_AAS_PACKAGING_AUDIT_2026_05_07.md`
- `docs/planning/CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`
- `docs/planning/CITY_AS_A_SERVICE_SERVICE_CATALOG.md`
- `docs/planning/CITY_AS_A_SERVICE_GO_TO_MARKET.md`
- `docs/planning/CITY_AS_A_SERVICE_TEMPLATE_SPECS.md`
- `docs/planning/CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_08.md`
- `docs/planning/CITY_AS_A_SERVICE_MORNING_BRIEF_2026_05_08.md`
- `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
- `docs/planning/CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`
- `docs/planning/CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
- `docs/task-templates/physical-verification.json`

This artifact only maps adjacent AAS packaging ideas. It does not authorize expansion away from the CaaS wedge or any live-readiness claim.

## 2. Reusable CaaS primitives to carry forward

CaaS has clarified a reusable Execution Market pattern:

1. **Concierge offer card** — one narrow sellable service, manually reviewed.
2. **Structured intake** — exact question, target, fallback, success definition, and evidence contract.
3. **Proof artifact** — reviewed output with `safe_to_claim[]` beside `do_not_claim_yet[]`.
4. **Outcome normalization** — accepted / rejected / redirected / blocked / inconclusive, or vertical-specific equivalents.
5. **Operator review summary** — source type, next step, follow-on trigger, and blocked claim preservation.
6. **Registry / coverage summary** — read-only count of which offer types have reviewed proof support.
7. **Parity gates** — local fixture proof first; live transport/readiness only after preservation of claims, tone, provenance, and blocked claims is verified.

The adjacent verticals below should reuse those primitives rather than inventing new product logic.

## 3. Short taxonomy of viable AAS verticals besides CaaS

### 3.1 Property Ops as a Service

**Plan.** Package recurring property reality checks for operators who need trusted field state: exterior condition, access blockers, posted notices, vacancy signals, repair completion snapshots, and move-in/move-out condition evidence. This is adjacent to CaaS because many property tasks touch municipal compliance, but the buyer pain is broader: “tell me what is actually happening at this asset, with proof I can act on.”

The first product should be a concierge property evidence desk, not automated property management. Start with one-site checks and reviewed evidence packets. The output should normalize observed state, blockers, severity, confidence, and the next operational step.

- **First sellable concierge offer:** Single-Site Condition Reality Check.
- **Required proof artifact:** reviewed property-condition packet with wide/close photos, source type, issue taxonomy, severity, access status, and `safe_to_claim[]` / `do_not_claim_yet[]`.
- **CaaS primitive reused:** `site_audit`, `capture_notice`, `posting_proof`, reviewed outcome contract, follow-on task trigger.
- **Blocked / forbidden claims:** no appraisal, code/legal sufficiency, tenant determination, insurance adjustment, trespass/access guarantee, remediation completion guarantee, or regulator acceptance.

### 3.2 Retail Reality as a Service

**Plan.** Package physical retail verification for businesses, agents, marketplaces, and data teams that need reliable ground truth: store open/closed status, hours drift, inventory shelf presence, price checks, display compliance, and local promotion visibility. This can reuse EM’s existing physical-verification templates while borrowing CaaS’s evidence discipline.

The first motion should sell “verified storefront facts with structured discrepancies,” not broad market research. Each order should answer one operational question and return normalized evidence, confidence, and follow-on routing.

- **First sellable concierge offer:** Storefront Hours + Availability Check.
- **Required proof artifact:** reviewed retail reality packet with storefront/status photo, posted-hours proof, observed open/closed state, optional staff answer source type, discrepancy summary, and next-step recommendation.
- **CaaS primitive reused:** `verify_place`, `counter_question`, `site_audit`, source-type separation, outcome normalization.
- **Blocked / forbidden claims:** no guaranteed inventory availability beyond observation window, no brand compliance certification, no employee performance judgment, no consumer-safety certification, no permanent business-status claim from one visit.

### 3.3 Field Asset Ops as a Service

**Plan.** Package inspections of real-world assets that agents cannot observe remotely: kiosks, ATMs, chargers, vending machines, lockers, signs, sensors, and other distributed equipment. The buyer needs operational truth: present, accessible, powered, damaged, out of service, blocked, or needing dispatch.

The CaaS lesson is to avoid vague “go check this” tasks. Each asset check should have an evidence schema, failure taxonomy, severity label, and repair/escalation trigger. The first package should remain a reviewed concierge verification, not an automated maintenance network.

- **First sellable concierge offer:** Asset Functionality + Obstruction Check.
- **Required proof artifact:** reviewed asset-state packet with identity/location confirmation, functional status, obstruction/damage taxonomy, timestamped photos, and escalation recommendation.
- **CaaS primitive reused:** `verify_place`, `site_audit`, `measurement`, proof observability, operator-reviewed next step.
- **Blocked / forbidden claims:** no technical diagnosis beyond visible/testable observations, no repair completion, no warranty or safety certification, no authority to manipulate restricted equipment, no SLA uptime guarantee.

### 3.4 Event Readiness as a Service

**Plan.** Package pre-event and day-of physical readiness checks: venue access, signage placement, queue state, booth setup, posted notices, vendor arrival proof, and handoff confirmations. This is a good AAS candidate because failures are time-sensitive and agents can coordinate checklists well, but physical presence remains necessary.

The first wedge should be a narrow “readiness check with blockers and next actions,” not full event production. Outputs should preserve what was observed, what staff said, what was documented, and which blockers require follow-up.

- **First sellable concierge offer:** Venue Readiness Snapshot.
- **Required proof artifact:** reviewed event-readiness packet with checklist pass/fail, venue/access proof, blocker list, source type, urgency rating, and follow-on task trigger.
- **CaaS primitive reused:** `site_audit`, `capture_notice`, `queue_wait`, `handoff_proof`, structured ambiguity policy.
- **Blocked / forbidden claims:** no crowd-safety certification, no permit/legal compliance guarantee, no vendor contract enforcement, no unlimited waiting, no emergency/security authority, no guarantee that event operations will remain stable after the check.

### 3.5 Document Logistics as a Service

**Plan.** Package physical document movement and handoff proof: printing, pickup, delivery, wet-signature relay, notarization coordination where legally and operationally allowed, certified mailing preparation, and receipt capture. This vertical is close to CaaS packet submission but can serve non-municipal workflows too.

The product should be an evidence-backed chain-of-custody concierge offer. It should prove transfer attempts and outcomes, not promise legal sufficiency or successful acceptance by third parties.

- **First sellable concierge offer:** Document Handoff Proof Run.
- **Required proof artifact:** reviewed handoff packet with pickup/drop-off timestamps, recipient/source type, receipt/stamp/photo when available, failed-handoff reason, and next-step recommendation.
- **CaaS primitive reused:** `submit_packet`, `handoff_proof`, `queue_wait`, accepted/rejected/redirected/blocked taxonomy, review packet promotion policy.
- **Blocked / forbidden claims:** no legal service, no notarial act unless separately credentialed and scoped, no guaranteed acceptance, no identity verification beyond scoped evidence, no custody guarantee outside documented handoff windows.

### 3.6 Local Data Collection as a Service

**Plan.** Package measurement and observation loops that produce small trusted datasets: parking counts, shelf counts, construction activity snapshots, signage inventories, public-space condition checks, and localized price observations. This is the most “data product” adjacent vertical, but it must stay rooted in reviewed evidence rather than bulk unverified submissions.

The first wedge should be a concierge micro-survey for one place/time/question. It can later become repeatable if the registry shows proof coverage and review quality across repeated runs.

- **First sellable concierge offer:** One-Location Field Measurement Snapshot.
- **Required proof artifact:** reviewed measurement packet with count/method, timestamp window, context photo, uncertainty note, and repeatability guidance.
- **CaaS primitive reused:** `measurement`, `site_audit`, proof block scorecard, registry coverage summary, claim-limit survival.
- **Blocked / forbidden claims:** no statistically representative survey claim, no continuous monitoring claim, no official dataset certification, no exactness claim where counting method has known ambiguity, no predictive analytics claim.

## 4. Cross-vertical mapping table

| AAS concept | First concierge offer | Required proof artifact | CaaS primitive reused | Must not claim |
|---|---|---|---|---|
| Property Ops AAS | Single-Site Condition Reality Check | reviewed property-condition packet | `site_audit`, `capture_notice`, `posting_proof` | appraisal, code/legal sufficiency, access guarantee |
| Retail Reality AAS | Storefront Hours + Availability Check | reviewed retail reality packet | `verify_place`, `counter_question`, `site_audit` | permanent business status, inventory guarantee, certification |
| Field Asset Ops AAS | Asset Functionality + Obstruction Check | reviewed asset-state packet | `verify_place`, `site_audit`, `measurement` | repair/diagnosis/SLA readiness |
| Event Readiness AAS | Venue Readiness Snapshot | reviewed event-readiness packet | `site_audit`, `queue_wait`, `handoff_proof` | safety/legal/event outcome guarantee |
| Document Logistics AAS | Document Handoff Proof Run | reviewed handoff packet | `submit_packet`, `handoff_proof`, `queue_wait` | legal service, guaranteed acceptance, unscope custody |
| Local Data Collection AAS | One-Location Field Measurement Snapshot | reviewed measurement packet | `measurement`, `site_audit`, scorecard/registry | representative dataset, continuous monitoring, exactness |

## 5. Recommended sequencing

CaaS should remain the lead wedge.

Reason: it has the strongest current planning stack, concrete Phase 1 offer cards, fixture-backed reviewed outputs, and a clear operator-learning thesis. The adjacent AAS concepts are useful packaging maps, but none should become the main build lane until the CaaS proof ladder is stronger.

Recommended order:

1. Keep CaaS Phase 1 as the active proving ground.
2. Strengthen the reviewed-fixture registry and operator/admin summary so coverage, safe claims, and blocked claims are visible without reopening raw context.
3. Prove live parity gates before any vertical claims live memory, retrieval, dispatch automation, or customer-copy readiness.
4. Only then promote one adjacent AAS vertical as a reuse test, preferably the one that most directly reuses an already-proven CaaS primitive and can ship as a concierge reviewed offer.

The near-term AAS strategy is therefore not “launch many verticals.” It is:

> Use CaaS to harden Execution Market’s reviewed-real-world-execution primitive, then reuse that primitive conservatively across adjacent AAS packages.

## 6. Guardrails for future work

- Keep adjacent AAS work as Execution Market packaging strategy, not new project drift.
- Preserve safe and blocked claims together in every artifact.
- Do not turn one local reviewed fixture into worker-copyable doctrine.
- Do not publish customer-facing copy from this document.
- Do not claim live transport, runtime parity, autonomous dispatch, legal sufficiency, regulator acceptance, or broad marketplace readiness until the relevant gates pass.

## 7. May 8 operator coverage gate for adjacent AAS reuse

The first reusable AAS control-plane pattern after CaaS Phase 1 is now clearer:

```text
reviewed fixtures
-> reviewed fixture registry
-> read-only operator coverage summary
-> only then internal read surface or vertical reuse test
```

The operator coverage summary pattern matters for every adjacent AAS vertical because it prevents a common marketplace mistake: turning a handful of reviewed examples into public claims, routing automation, worker doctrine, reputation updates, or customer-facing copy too early.

Before any adjacent AAS concept above is promoted from packaging idea to build lane, it should have the same minimum conservative ladder:

1. one narrow concierge offer card
2. one deterministic fixture spec
3. one reviewed output schema
4. one local reviewed fixture
5. one registry row that keeps `safe_to_claim[]` beside `do_not_claim_yet[]`
6. one read-only operator coverage summary with all readiness flags false

This makes the promotion rule explicit:

> A vertical can be visible to operators before it is visible to customers, dispatch automation, live memory, reputation, worker Skill DNA, or worker instructions.

For now, CaaS remains the only active proving ground. The adjacent verticals should borrow the pattern only after CaaS preserves claim boundaries through at least one thin read-only operator/admin surface or persisted summary artifact.
