# City as a Service — Phase 1 Offer Card Pack

> Created: 2026-05-08 23:00 dream session
> Scope: Execution Market AAS / City-as-a-Service only
> Parent docs:
> - `CITY_AS_A_SERVICE_AAS_PACKAGING_AUDIT_2026_05_07.md`
> - `CITY_AS_A_SERVICE_SERVICE_CATALOG.md`
> - `CITY_AS_A_SERVICE_GO_TO_MARKET.md`
> - `CITY_AS_A_SERVICE_PILOT_BLUEPRINT.md`
> - `CITY_AS_A_SERVICE_PROOF_BLOCK_READINESS_IMPLEMENTATION.md`
> Status: internal Phase 1 packaging pack; not live sales copy

## 1. Why this pack exists

The CaaS planning stack now has enough shape to package a narrow concierge pilot, but not enough proof to sell broad automation, multi-jurisdiction playbooks, or autonomous city dispatch.

This pack converts the May 7 packaging audit into three one-page offer cards that can guide internal sales, scoping, review, and dispatch without overclaiming readiness.

The safe Phase 1 package is:

> **City Counter Ops — verified municipal errands with structured next steps.**

Customer-facing promise:

> We promise a verified attempt window, evidence of what happened, and a structured next-step output — not city cooperation, approval, or legal sufficiency we cannot control.

## 2. Shared Phase 1 rules

These rules apply to all three launch cards.

### 2.1 Operating model

- Concierge/manual operator review only.
- One metro area for the initial pilot.
- One primary municipal objective per base order.
- One office/site per base order unless an explicit redirect add-on is sold.
- All rejected, redirected, blocked, or inconclusive outcomes require operator review before customer-facing closure.
- Follow-on work is suggested as a new task or add-on; it is not silently included.

### 2.2 Required output posture

Every completed order returns:

- `outcome_status`
- `evidence_summary`
- `source_type`
- `operator_review_status`
- `structured_next_step`
- `follow_on_task_trigger` when applicable
- `proof_status_label`
- `forbidden_claims_preserved=true`

### 2.3 Shared outcome statuses

Use these statuses consistently:

- `accepted`
- `rejected`
- `redirected`
- `blocked`
- `inconclusive`
- `verified_present`
- `verified_absent`
- `verified_partial`

### 2.4 Shared source types

Separate what was seen, heard, or documented:

- `observed`
- `heard_from_staff`
- `documented`
- `customer_supplied`
- `mixed`

### 2.5 Shared forbidden claims

No Phase 1 card may imply:

- guaranteed approval
- legal advice or legal sufficiency
- city relationship, influence, or preferential access
- unlimited retries
- broad multi-office handling in one base order
- live Acontext readiness
- autonomous dispatch readiness
- multi-jurisdiction playbook readiness
- worker-copyable municipal doctrine derived from one proof anchor

## 3. Offer Card 1 — Counter Reality Check

### Buyer pain

City websites, forms, office routes, windows, and staff instructions drift. A business or agent may need to know what the office actually requires today before risking a filing attempt.

### Sellable promise

We verify the current counter/office reality for one defined municipal question and return a structured answer with evidence, source type, redirect target if any, and reviewed next step.

### Best for

- confirming the correct office, desk, window, or route
- checking whether an online instruction is stale
- validating which form/version is currently being accepted
- deciding whether a packet submission attempt is ready or should be repaired first

### Required intake fields

- `jurisdiction`
- `office_name_or_suspected_office`
- `office_address_if_known`
- `workflow_type`
- `exact_primary_question`
- `acceptable_answer_format`
- `urgency_window`
- `fallback_question_if_staff_refuse`
- `redirect_instruction`
- `customer_success_definition`

### Included deliverables

- one in-person office visit attempt
- office presence/open-state proof when observable
- one primary structured question
- one backup clarification question if needed
- normalized answer
- source type: `observed`, `heard_from_staff`, `documented`, or `mixed`
- redirect target if staff or signage routes elsewhere
- operator-reviewed next-step recommendation

### Explicit exclusions

- legal interpretation of the answer
- guaranteed definitive answer if staff conflict or refuse
- packet submission during the same base order
- more than one office visit unless redirected follow-through is purchased
- official city record retrieval unless separately scoped

### Review gate

Operator must verify before closure that:

- the exact question asked matches intake or the deviation is explained
- source type is explicit
- contradiction/refusal is preserved when present
- redirect information is not upgraded into certainty without evidence
- customer-facing next step is phrased as an operational recommendation, not legal advice

### Customer-facing output fields

```json
{
  "offer": "counter_reality_check",
  "outcome_status": "verified_present|verified_absent|redirected|blocked|inconclusive",
  "answer_summary": "string",
  "source_type": "observed|heard_from_staff|documented|mixed",
  "evidence_summary": ["string"],
  "redirect_target": "string|null",
  "operator_review_status": "reviewed",
  "structured_next_step": "string",
  "follow_on_task_trigger": "packet_submission_attempt|office_redirect_follow_through|null",
  "proof_status_label": "planning_supported",
  "forbidden_claims_preserved": true
}
```

### Follow-on task triggers

- `packet_submission_attempt` when the office confirms readiness or required packet contents.
- `office_redirect_follow_through` when staff/signage directs the customer elsewhere.
- `rejection_diagnosis_prep` only if the check reveals a likely repair path for a rejected or stale packet.

### Proof status

`planning_supported`

This card is commercially supported by the service catalog and pilot plan, but it still needs a first proof fixture before it can support automation, replay claims, or office-memory doctrine.

## 4. Offer Card 2 — Packet Submission Attempt

### Buyer pain

A prepared filing or municipal packet may be accepted, rejected, redirected, or blocked for reasons that are hard to discover remotely. Customers need proof of attempt and a clear repair or reroute path.

### Sellable promise

We attempt one packet submission at the scoped municipal office and return evidence of what happened, an accepted/rejected/redirected/blocked classification, captured reason when available, and reviewed next step.

### Best for

- permit packet filing attempts
- renewal submission attempts
- counter drop-off proof
- validating whether a packet is accepted as prepared
- capturing rejection or redirect details for repair

### Required intake fields

- `jurisdiction`
- `target_office`
- `office_address_if_known`
- `workflow_type`
- `packet_checklist`
- `named_documents_included`
- `acceptance_criteria_if_known`
- `documents_prepared_status`
- `municipal_fee_policy`
- `what_to_do_if_redirected`
- `what_to_do_if_rejected_for_fixable_reason`
- `deadline_or_urgency_level`
- `customer_success_definition`

### Included deliverables

- one in-person submission attempt
- structured outcome: `accepted`, `rejected`, `redirected`, `blocked`, or `inconclusive`
- receipt, stamped copy, or equivalent acceptance evidence when available
- rejection reason capture when rejected
- redirect target when redirected
- clear blocked reason when the attempt cannot proceed
- operator-reviewed next-step recommendation

### Explicit exclusions

- document drafting, repair, or legal review
- guarantee that the city accepts the packet
- payment of municipal fees unless explicitly included and funded
- more than one submission office in a single base order
- retry/resubmission unless explicitly purchased
- interpreting whether the city was legally correct

### Review gate

Operator must verify before closure that:

- outcome status matches evidence
- absence of receipt/stamp is explicitly explained
- rejection/redirect wording preserves uncertainty and staff source when relevant
- customer-facing next step is actionable but not legal advice
- any reusable learning is operator-only unless separately proven by fixture breadth

### Customer-facing output fields

```json
{
  "offer": "packet_submission_attempt",
  "outcome_status": "accepted|rejected|redirected|blocked|inconclusive",
  "attempt_summary": "string",
  "source_type": "observed|heard_from_staff|documented|mixed",
  "acceptance_evidence": ["string"],
  "rejection_reason": "string|null",
  "redirect_target": "string|null",
  "blocked_reason": "string|null",
  "operator_review_status": "reviewed",
  "structured_next_step": "string",
  "follow_on_task_trigger": "rejection_diagnosis_resubmission_prep|office_redirect_follow_through|permit_follow_through_bundle|null",
  "proof_status_label": "local_anchor_supported_redirect_outdated_packet_only",
  "forbidden_claims_preserved": true
}
```

### Follow-on task triggers

- `rejection_diagnosis_resubmission_prep` when the packet is rejected for fixable missing/stale/incorrect contents.
- `office_redirect_follow_through` when the submission is redirected to another office/window/channel.
- `permit_follow_through_bundle` only after repeated accepted or repairable flows justify bundling.

### Proof status

`local_anchor_supported_redirect_outdated_packet_only`

The existing proof anchor `redirect_outdated_packet_001` supports conservative packaging for redirect/outdated-packet behavior. It does **not** support broad claims about all submission types, guaranteed filing success, worker-copyable doctrine, or autonomous dispatch.

## 5. Offer Card 3 — Posting Compliance Check

### Buyer pain

Public postings, permit notices, storefront notices, and job-site compliance materials may be missing, damaged, hidden, expired, or illegible. Remote teams need timestamped proof and a clear pass/fail checklist.

### Sellable promise

We verify whether one scoped posting is visible and legible at the target site, return wide/close evidence, classify pass/fail/partial state, and provide reviewed next-step guidance.

### Best for

- storefront notice verification
- construction permit posting checks
- public notice visibility proof
- recurring proof that required postings remain visible and legible
- property/compliance teams needing field evidence

### Required intake fields

- `site_address`
- `posting_type`
- `posting_location_expectation`
- `visibility_rules_or_customer_checklist`
- `legibility_requirements`
- `required_photo_angles`
- `recurrence_cadence_if_repeat`
- `failure_threshold_for_escalation`
- `access_constraints`
- `customer_success_definition`

### Included deliverables

- context/wide photo evidence
- close-up legibility evidence when safely accessible
- timestamped proof bundle
- pass/fail/partial checklist
- visibility notes
- missing/damaged/illegible classification when applicable
- operator-reviewed next-step recommendation

### Explicit exclusions

- creating, printing, fixing, or reposting the notice
- legal sufficiency opinions beyond the provided checklist
- interior inspections unless separately scoped
- confrontation with occupants/staff unless explicitly scoped and safe
- guarantee that a regulator will accept the posting as sufficient

### Review gate

Operator must verify before closure that:

- wide/close evidence is sufficient for the claimed checklist outcome
- access constraints or visibility limits are preserved
- pass/fail/partial status does not exceed what the evidence proves
- customer-facing next step distinguishes remediation suggestion from legal determination
- no exact GPS/location metadata is exposed in customer copy beyond scoped site confirmation

### Customer-facing output fields

```json
{
  "offer": "posting_compliance_check",
  "outcome_status": "verified_present|verified_absent|verified_partial|blocked|inconclusive",
  "checklist_result": "pass|fail|partial|blocked|inconclusive",
  "source_type": "observed",
  "evidence_summary": ["wide_context_photo", "close_legibility_photo"],
  "visibility_notes": "string",
  "failure_reason": "missing|damaged|illegible|access_blocked|wrong_location|null",
  "operator_review_status": "reviewed",
  "structured_next_step": "string",
  "follow_on_task_trigger": "posting_recheck|multi_site_posting_verification_bundle|permit_follow_through_bundle|null",
  "proof_status_label": "planning_supported",
  "forbidden_claims_preserved": true
}
```

### Follow-on task triggers

- `posting_recheck` when remediation is expected and proof should be refreshed.
- `multi_site_posting_verification_bundle` only after repeated single-site checks establish operational rhythm.
- `permit_follow_through_bundle` when posting state is tied to an active filing or inspection flow.

### Proof status

`planning_supported`

This card is commercially supported by the service catalog and pilot plan, but it needs its own first proof fixture before automation, recurring compliance claims, or broad checklist doctrine should be sold.

## 6. Internal SKU summary

| Offer | Internal SKU | Proof status | Phase 1 sellable? | Automation claim? |
|---|---|---|---|---|
| Counter Reality Check | `caas_counter_reality_check_v0` | `planning_supported` | Yes, concierge/operator-reviewed only | No |
| Packet Submission Attempt | `caas_packet_submission_attempt_v0` | `local_anchor_supported_redirect_outdated_packet_only` | Yes, concierge/operator-reviewed only | No |
| Posting Compliance Check | `caas_posting_compliance_check_v0` | `planning_supported` | Yes, concierge/operator-reviewed only | No |

## 7. How to use this pack

### 7.1 Sales/scoping use

Use the cards as internal scoping constraints before writing any customer-facing copy. If an opportunity does not fit a card, treat it as custom operator work, not a repeatable SKU.

### 7.2 Product/build use

Use the fields as the first schema shape for:

- template intake forms
- review-console output preview
- customer closure packets
- proof fixture creation
- follow-on task suggestions

### 7.3 Proof-building use

Next fixture priorities:

1. Counter Reality Check fixture with contradictory/stale online guidance and a safe redirect or confirmation result.
2. Posting Compliance Check fixture with wide/close evidence and a partial/fail outcome.
3. Second Packet Submission Attempt fixture that is not an outdated-packet redirect, so the card stops relying on one narrow anchor.

## 8. Daytime pickup

Best next daytime task:

> Convert these offer cards into three fixture specs plus one review-output JSON schema draft, without changing live customer copy.

Acceptance gate:

- all fixture specs preserve `safe_to_claim[]` and `do_not_claim_yet[]`
- all three customer outputs preserve source type and review status
- Packet Submission Attempt keeps its proof label narrow
- no generated UI/copy mentions live Acontext, autonomous dispatch, multi-jurisdiction playbooks, or worker-copyable doctrine

---

## 9. 2026-05-08 00:00 fixture-spec continuation

The Daytime pickup above is now landed as deterministic fixture specs and a summary guardrail:

- `mcp_server/city_ops/phase1_offer_fixture_specs.py`
- `mcp_server/tests/city_ops/test_phase1_offer_fixture_specs.py`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/counter_reality_check.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/packet_submission_attempt.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/posting_compliance_check.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/phase1_offer_fixture_spec_summary.json`
- `CITY_AS_A_SERVICE_PHASE_1_FIXTURE_SPECS_IMPLEMENTATION.md`

New safe internal claim:

```text
phase_1_offer_fixture_specs_landed
```

Proof labels were deliberately sharpened rather than broadened:

- Counter Reality Check: `planning_supported_needs_first_fixture`
- Packet Submission Attempt: `local_anchor_supported_redirect_outdated_packet_only`
- Posting Compliance Check: `planning_supported_needs_first_fixture`

The next proof-building order is now explicit:

1. Counter Reality Check proof fixture.
2. Posting Compliance Check proof fixture.
3. Non-redirect Packet Submission Attempt proof fixture.

Do not change live customer copy, add front-door SKUs, claim live Acontext readiness, claim autonomous dispatch, or produce worker-copyable municipal doctrine before those fixture proofs exist.
