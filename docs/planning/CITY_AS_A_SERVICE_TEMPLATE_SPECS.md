# City as a Service — Template Specs

> Last updated: 2026-04-25
> Parent plan: `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> Status: implementation-oriented draft

## 1. Purpose

This document turns the CaaS thesis into concrete task templates that Execution Market can ship as dashboard presets, API presets, and operator playbooks.

The goal is not to model every municipal workflow at once.
The goal is to define a narrow template set that:
- captures high-value city workflows
- normalizes messy real-world outcomes
- produces replayable structured evidence
- composes into multi-step municipal chains

## 2. Design principles

### 2.1 Outcome-first, not gig-first
Each template should ask:
- what municipal outcome is the customer trying to reach?
- what evidence proves success, failure, or redirect?
- what follow-on action should the system recommend?

### 2.2 Separate observation from interpretation
Every template should preserve:
- what the worker directly observed
- what a city employee said
- what document/receipt/sign proved
- what the worker thinks is likely next

### 2.3 Structured ambiguity beats fake certainty
City workflows are inconsistent. Templates must support:
- `accepted`
- `rejected`
- `redirected`
- `blocked`
- `inconclusive`

### 2.4 Templates must chain cleanly
The first MVP should already assume outputs feed later tasks.
If a submission is rejected, the template should emit machine-usable next-step hints.

## 3. Template set for MVP

Recommended first five templates:
1. Counter Question
2. Packet Submission
3. Posting Proof
4. Site Audit
5. Queue Wait + Handoff

These five are enough to cover the majority of early CaaS demand while staying narrow enough for quality control.

---

## 4. Template A — Counter Question

### 4.1 Best used for
- verifying which office/window handles a request
- confirming current form/version requirements
- clarifying real office practice when the website is stale
- asking one or two tightly scoped municipal questions

### 4.2 Typical customer prompts
- "Which permit window handles sidewalk dining renewals today?"
- "Is the 2026 revision of this form required yet?"
- "Do they require wet signatures for this submission?"

### 4.3 Required input fields
- jurisdiction name
- office name or address
- workflow category
- primary question
- optional secondary question
- acceptable proof requirements
- latest acceptable response time
- fallback instruction if redirected

### 4.4 Worker instructions
The worker should:
1. arrive at the specified office/location
2. confirm the office is open/reachable
3. ask the exact question(s) with minimal paraphrase
4. capture the answer in structured form
5. note whether the answer was heard, observed, or documented
6. record any redirect target or caveat

### 4.5 Required outputs
- `outcome_status`
- `source_type`
- `structured_answer`
- `answer_confidence`
- `redirect_target` if applicable
- office/signage photo
- timestamp proof
- short worker notes

### 4.6 Allowed statuses
- `completed`
- `redirected`
- `blocked`
- `inconclusive`

### 4.7 Common follow-on recommendations
- route to different office
- prepare new document version
- schedule packet submission
- escalate for legal/compliance review

### 4.8 Quality bar
A good Counter Question task does **not** just return prose.
It returns a normalized answer and whether that answer was:
- heard from staff
- read from posted/documented guidance
- inferred from signage/routing

---

## 5. Template B — Packet Submission

### 5.1 Best used for
- filing permit or license packets
- dropping off compliance materials
- collecting proof of acceptance/rejection
- diagnosing why a packet failed in person

### 5.2 Typical customer prompts
- "Submit this packet and tell me if it was accepted."
- "If rejected, capture the exact rejection reason and where to resubmit."

### 5.3 Required input fields
- jurisdiction name
- office name or target address
- packet checklist
- acceptance definition
- allowed payment/fee behavior
- redirect handling rule
- rejection taxonomy requested
- whether worker may wait for same-day disposition

### 5.4 Worker instructions
The worker should:
1. verify office/counter destination
2. submit the packet as instructed
3. capture whether the packet was accepted, rejected, or redirected
4. collect any receipt, stamp, or documented proof
5. record exact rejection or redirect reason if provided
6. avoid paraphrasing formal reasons when a document exists

### 5.5 Required outputs
- `outcome_status`
- `receipt_proof` or `proof_unavailable_reason`
- `submission_result` = accepted | rejected | redirected
- `rejection_reasons[]`
- `redirect_target`
- `next_step_recommendation`
- timestamped office proof
- structured notes

### 5.6 Allowed statuses
- `accepted`
- `rejected`
- `redirected`
- `blocked`

### 5.7 Follow-on triggers
- rejection → doc repair workflow
- redirect → new office task
- accepted → posting proof / inspection prep / status follow-up

### 5.8 Quality bar
The template succeeds when the result can be replayed later without calling the worker.
That means the evidence must answer:
- Was the packet accepted?
- If not, why not?
- What exact next step is now unlocked?

---

## 6. Template C — Posting Proof

### 6.1 Best used for
- storefront notice verification
- construction posting verification
- legal/public notice visibility checks
- recurring compliance re-checks

### 6.2 Typical customer prompts
- "Verify the permit is visibly posted at the storefront."
- "Capture proof that the notice remains legible from public view."

### 6.3 Required input fields
- notice/posting type
- site/location
- visibility requirement
- legibility requirement
- required photo angles
- optional repeat cadence
- pass/fail checklist

### 6.4 Worker instructions
The worker should:
1. capture a context shot showing location
2. capture a close-up proving notice identity/legibility
3. answer the checklist exactly
4. report obstructions or missing postings clearly

### 6.5 Required outputs
- `outcome_status`
- wide photo
- close-up photo
- checklist pass/fail fields
- optional obstruction notes
- timestamp proof

### 6.6 Allowed statuses
- `completed`
- `blocked`
- `inconclusive`

### 6.7 Follow-on triggers
- failed posting → remediation task
- partial visibility → site audit or repair task
- recurring proof → scheduled re-check

---

## 7. Template D — Site Audit

### 7.1 Best used for
- exterior compliance sweeps
- signage/accessibility checks
- pre-inspection readiness checks
- field verification for property/compliance ops

### 7.2 Required input fields
- site address
- checklist items
- mandatory capture angles
- fail conditions
- escalation threshold
- optional severity rubric

### 7.3 Worker instructions
The worker should:
1. inspect only the authorized observable scope
2. complete the checklist item by item
3. attach proof for every failed item and key passed items
4. flag urgent blockers separately from normal findings

### 7.4 Required outputs
- `outcome_status`
- checklist item results
- annotated observations
- photo set
- severity assessment
- recommended next action

### 7.5 Allowed statuses
- `completed`
- `blocked`
- `inconclusive`

### 7.6 Follow-on triggers
- remediation dispatch
- permit/posting proof task
- inspection readiness loop

---

## 8. Template E — Queue Wait + Handoff

### 8.1 Best used for
- standing in line
- appointment presence
- document pickup or drop-off at a specific handoff point
- time-sensitive city office presence

### 8.2 Required input fields
- arrival deadline
- office/location
- handoff condition
- max wait budget
- fallback rule if office closes or refuses service
- whether worker may switch to a question/route-probe mode

### 8.3 Worker instructions
The worker should:
1. prove arrival
2. remain present until the handoff condition or max wait threshold
3. capture elapsed time and handoff outcome
4. record exact block reason if unresolved

### 8.4 Required outputs
- `outcome_status`
- arrival proof
- elapsed wait
- handoff result
- blocked reason if applicable
- redirect target if discovered

### 8.5 Allowed statuses
- `completed`
- `redirected`
- `blocked`

### 8.6 Follow-on triggers
- new packet submission
- new counter question
- rescheduled revisit

---

## 9. Shared status model

To keep CaaS replayable across templates, the shared status vocabulary should stay tight.

### 9.1 Canonical outcome statuses
- `completed`
- `accepted`
- `rejected`
- `redirected`
- `blocked`
- `inconclusive`

### 9.2 Canonical source types
- `observed`
- `heard`
- `documented`
- `mixed`

### 9.3 Canonical next-step classes
- `resubmit_packet`
- `ask_followup_question`
- `reroute_office`
- `fix_posting`
- `schedule_revisit`
- `prepare_for_inspection`
- `human_review_required`

## 10. Minimal API shape

A thin product/API contract could look like this:

```json
{
  "vertical": "city_ops",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "[office]",
  "required_outcome": "Submit permit packet and capture acceptance or rejection",
  "inputs": {},
  "evidence_requirements": {},
  "result": {
    "outcome_status": "accepted",
    "source_type": "documented",
    "rejection_reasons": [],
    "redirect_target": null,
    "next_step_recommendation": "prepare_for_inspection"
  }
}
```

## 11. Operator/UI implications

These templates imply three concrete product surfaces:
- dashboard preset creation forms
- worker mobile structured completion forms
- operator replay views with normalized outcome summaries

The key UX rule: workers should not have to author long freeform narratives when a structured answer will do.
Freeform text should exist as support, not as the primary product.

## 12. Recommended build order

### Phase 1
- Counter Question
- Packet Submission
- Posting Proof

### Phase 2
- Site Audit
- Queue Wait + Handoff

### Phase 3
- chained workflow wrapper that connects template outputs to new task creation

## 13. Sharp implementation recommendation

If only one thing is built first, build **Packet Submission** with a high-quality rejection/redirect schema.
That template sits closest to the pain point customers will pay for and creates the strongest replayable municipal memory.