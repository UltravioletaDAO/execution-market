# Execution Market AAS — Portfolio Promotion Map (2026-05-26 11 PM)

> Scope: Execution Market AAS / City-as-a-Service internal planning only.  
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`.  
> Status: no-customer-exposure promotion map; not public copy; not a customer catalog; not pricing; not queue/dispatch/reputation/runtime approval; not worker doctrine.

## 1. Why this doc exists

The May 26 22:00 rung completed the Local Data Collection internal sample output and explicit hold decision. That closed the immediate May 25 daytime recommendation. The planning risk has now shifted from “what is the next Local Data Collection step?” to “which AAS family should be promoted next, and which gate is allowed to move without accidentally implying launch readiness?”

This map gives the next agents a single promotion ledger across the active AAS families. It deliberately favors narrow internal/admin proof seams over customer exposure.

## 2. Source posture

Read before writing:

- `~/clawd/DREAM-PRIORITIES.md` — controlling priority; AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped for dream work.
- `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md` — latest May 26 22:00 Local Data Collection status.
- `EXECUTION_MARKET_AAS_PORTFOLIO_IMPLEMENTATION_PLAN_2026_05_18.md` — reusable proof ladder and gate definitions.
- `EXECUTION_MARKET_AAS_NEXT_LOW_AUTHORITY_PACKAGING_PLAN_2026_05_23_10PM.md` — low-authority ranking that promoted Retail Reality and Local Data Collection.
- `CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_05_25.md` — Local Data Collection method-boundary synthesis.
- Current persisted artifacts in `mcp_server/city_ops/fixtures/aas_package_ladder/`.

No stopped repository or stopped project was inspected or edited for this map.

## 3. Current family ledger

| Family / lane | Current highest safe boundary | Current decision posture | Safe meaning only | Still not allowed |
|---|---|---|---|---|
| Compliance Desk | Single-boundary human-operator approval record for one internal package-label text boundary | Narrow internal approval exists, but no delivery path exists | One text boundary can be referred to internally as operator-approved for label review | Customer delivery, publication, catalog route, pricing, queue, dispatch, reputation, runtime, raw metadata, legal/regulator authority, worker doctrine |
| Document / Handoff Logistics | Internal sample output + explicit hold decision | Held | A sample wording shape exists for internal review | Legal service, notarial act, identity verification, custody guarantee, filing success, customer delivery, route, price, dispatch, reputation, runtime, worker doctrine |
| Incident Verification | Internal sample output + explicit hold decision | Held | A sample wording shape exists for internal review | Emergency response, safety certification, repair diagnosis, insurance/SLA/official report, fault/liability, customer delivery, dispatch, reputation, runtime, worker doctrine |
| Retail Reality | Pending human-operator approval request + pending-status card | Pending review, not approved | An exact selected boundary is queued for possible human review and can be displayed internally without candidate text values | Human approval, customer copy/delivery/publication, catalog route, pricing, queue, dispatch, reputation, runtime, exact GPS/raw metadata, retail authority, worker doctrine |
| Local Data Collection | Internal sample output + explicit hold decision | Held | A method-bounded synthetic sample and hold record exist for one-window count/measurement wording | Dataset publication, analytics, statistical representativeness, continuous monitoring, official certification, predictive analytics, exactness certification, customer delivery, dispatch, reputation, runtime, exact GPS/raw metadata, worker doctrine |

## 4. Promotion principles from here

1. **Do not promote by age.** The oldest held family is not automatically next. Promote the family whose next gate creates the most reusable safety pattern.
2. **Do not skip from sample to public.** A held sample needs either a human approval artifact or an explicit decision to remain held. It does not become copy.
3. **Treat approval as narrower than delivery.** Even Compliance Desk's approval record does not imply a delivery path, publication, catalog, queue, or dispatch.
4. **Separate human review from runtime repair.** Acontext parity can improve memory confidence, but it cannot approve customer exposure or worker doctrine.
5. **Keep family-specific blocked claims family-specific.** Retail Reality blocked claims are not the same as Local Data Collection blocked claims; do not collapse them into a generic “safe” badge.

## 5. Recommended next gates

### 5.1 Default no-human/no-runtime gate: portfolio promotion ledger artifact

If there is no live human operator decision and no repaired Acontext runtime, the safest next implementation is a deterministic internal/admin portfolio promotion ledger that consumes the five family boundary artifacts and emits:

- source artifact IDs and digests;
- family current boundary;
- decision posture (`approved_internal_label_only`, `held`, `pending_human_review_not_approved`);
- exact latest safe claims;
- family-specific blocked claims;
- one recommended next gate per family;
- fail-closed summary counts.

This should be a read-only artifact, not a route, UI, price sheet, dispatch board, reputation event, runtime memory write, or worker instruction.

**Proposed output file**

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_portfolio_promotion_ledger.json
```

**Proposed module**

```text
mcp_server/city_ops/aas_portfolio_promotion_ledger.py
```

**Safe claim**

```text
admin_aas_portfolio_promotion_ledger_landed
```

**Required summary counters**

```text
families_tracked = 5
families_with_customer_delivery_authorization = 0
families_publishable = 0
families_with_public_or_catalog_routes = 0
families_ready_for_pricing_or_customer_quote = 0
families_ready_for_queue_or_dispatch = 0
families_ready_for_reputation_attachment = 0
families_with_live_acontext_runtime_parity = 0
families_allowed_to_release_exact_gps_or_raw_metadata = 0
families_with_worker_copyable_doctrine = 0
```

**Stop line**

Stop after the persisted ledger and tests. Do not mount a route or create customer copy in the same slice.

### 5.2 If a human operator is available: choose exactly one review

Preferred human-review candidate order:

1. **Retail Reality selected-boundary approval record** — because it already has a pending approval request and a pending-status card. Keep approval narrower than delivery.
2. **Compliance Desk delivery/publication gate** — only if the human operator explicitly authorizes an exact delivery path for the already-approved package label. Default remains `delivery_path=none`.
3. **Local Data Collection human review** — lower priority because dataset/analytics/exactness overclaims are more tempting; review should start with hold unless a specific selected text boundary is named.

Do not ask a human to approve a family generically. The review must name one exact boundary, one redaction posture, one delivery path decision, and still-blocked claims.

### 5.3 If runtime repair is the priority: keep it isolated

Runtime repair should use the existing Acontext blocker sequence only:

```text
Docker/socket/buildx/image inventory -> compose health -> API/dashboard reachability -> read-only readiness gate -> exactly one live write/retrieve parity pass if blockers are empty
```

A successful parity pass would still not approve customer delivery, catalog routes, pricing, queue, dispatch, reputation, exact-location/raw-metadata release, domain authority, or worker-copyable doctrine.

## 6. Family-by-family next gate specification

### 6.1 Compliance Desk

**Best next gate if customer exposure is desired:** delivery/publication gate over the existing approval record.

Required checks:

- consume only `aas_single_boundary_human_operator_approval_record.json`;
- prove selected text parity against the approval record;
- name exact delivery path or record `none_no_customer_delivery_authorized`;
- verify redaction and domain-authority exclusions at delivery time;
- keep all route/catalog/pricing/queue/dispatch/reputation/runtime/raw-metadata/worker-doctrine flags false.

**Best next gate if no customer exposure:** include it in the portfolio promotion ledger only.

### 6.2 Document / Handoff Logistics

**Best next gate:** package-review decision, not approval.

The decision should answer:

- safest internal package label;
- allowed future customer-output fields;
- forbidden custody/notarial/legal/identity/acceptance phrases;
- exact approval-request prerequisites if this family is ever selected for exposure.

### 6.3 Incident Verification

**Best next gate:** package-review decision focused on triage language.

The decision should answer:

- safe severity taxonomy terms;
- uncertainty and “what was not checked” language;
- follow-on-task trigger taxonomy;
- mandatory escalation-to-specialist/emergency-channel exclusions;
- exact approval-request prerequisites if this family is ever selected for exposure.

### 6.4 Retail Reality

**Best next gate if human operator exists:** human-operator approval record for the already selected boundary.

Required constraints:

- consume only the pending approval request;
- record approved or held for the exact selected boundary;
- keep delivery path absent unless separately approved;
- do not expose candidate text in a status surface;
- no permanent business status, inventory guarantee, brand-compliance certification, employee-performance judgment, consumer-safety certification, continuous monitoring, exact GPS/raw metadata, or worker doctrine.

**Best next gate without human operator:** include pending state in the portfolio promotion ledger.

### 6.5 Local Data Collection

**Best next gate:** no customer exposure; include the hold posture in the portfolio promotion ledger.

If later selected for human review, require a selected text boundary that preserves:

- one place/context reference without exact public coordinates;
- one observation window;
- one count/measurement question;
- method and uncertainty range;
- ambiguity/occlusion note;
- explicit no-dataset/no-analytics/no-representativeness/no-monitoring/no-certification/no-prediction/no-exactness claims.

## 7. Anti-overclaim checklist

Before any next implementation says “ready,” verify all of these remain false unless a separate gate exists:

```text
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
public_route_ready
controlled_pilot_ready
public_pricing_or_customer_quote_ready
operator_queue_launch_ready
autonomous_dispatch_ready
erc8004_reputation_ready
worker_skill_dna_ready
live_acontext_runtime_parity
acontext_sink_ready
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
private_operator_context_release_allowed
raw_transcript_authority
legal_or_regulator_authority
emergency_or_safety_authority
repair_or_insurance_or_sla_authority
worker_copyable_aas_doctrine
```

## 8. Next-session pickup order

1. Re-read `~/clawd/DREAM-PRIORITIES.md` first.
2. Sync repositories.
3. Stay inside Execution Market AAS / City-as-a-Service.
4. If no human review/runtime repair is available, implement the portfolio promotion ledger artifact and tests.
5. Update `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md` with the exact safe claim and blocked claims.
6. Run focused tests plus `git diff --check`.
7. Stage explicit files only; never `git add -A` or `git add .`.

## 9. Bottom line

The safest high-leverage continuation is not a new public package. It is a portfolio promotion ledger that lets Execution Market see all active AAS families at once without turning any of them into customer exposure by inference. That gives Saúl a clean morning choice: approve one exact boundary, repair runtime parity, or keep compounding the internal proof ladder.
