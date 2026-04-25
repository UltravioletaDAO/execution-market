# City as a Service — Pilot Blueprint

> Last updated: 2026-04-25
> Parent plan: `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> Companion docs:
> - `CITY_AS_A_SERVICE_TEMPLATE_SPECS.md`
> - `CITY_AS_A_SERVICE_EVIDENCE_SCHEMAS.md`
> - `CITY_AS_A_SERVICE_JURISDICTION_MODEL.md`
> - `CITY_AS_A_SERVICE_OPERATOR_PLAYBOOK.md`
> Status: implementation-oriented draft

## 1. Why this doc exists

The CaaS planning set now covers:
- what the vertical is
- which templates exist
- how evidence should be normalized
- how jurisdiction memory should accumulate
- how operators should run the workflow

What is still missing is the bridge from strategy to an actual first live pilot.
This document defines that bridge.

The goal is not to launch a national municipal platform.
The goal is to run one narrow, profitable, evidence-rich pilot that teaches EM how to become a real city-ops product.

## 2. Pilot thesis

The first CaaS pilot should prove three things:
1. customers will pay for verified municipal-world execution
2. EM can convert messy city interactions into structured next-step decisions
3. each run improves routing, evidence quality, and office memory for the next run

If the pilot cannot compound learning, it is only local labor.
If it does compound learning, it becomes municipal infrastructure.

## 3. Pilot shape

### 3.1 Geography
Start with **one metro area only**.
Recommended default: **Miami-area city/compliance workflows**.

Why:
- local density of repeatable demand
- timezone and operating familiarity
- easier operator review and pattern recognition
- faster memory accumulation per office

### 3.2 Customer wedge
Start with **permit and compliance-adjacent SMB workflows**.

Best initial customer types:
- restaurants
- contractors
- property operators
- permit expediters needing overflow field capacity

### 3.3 Pilot promise
Do not promise “we solve all city workflows.”
Promise something tighter:

> We handle the physical city steps your software and staff cannot do quickly: office verification, counter questions, packet submissions, and posting proof — with structured evidence and a clear next step.

## 4. In-scope templates

Pilot should start with exactly three templates:
1. **Counter Question**
2. **Packet Submission**
3. **Posting Proof**

These three are enough to create a real loop:
- verify routing/requirements
- attempt submission
- prove compliance state after or around submission

### 4.1 Why not start with all five templates?
Because early success depends on high review quality, not breadth.
Site Audit and Queue Wait + Handoff can follow once the core evidence/review loop is stable.

## 5. Pilot workflow loops

### 5.1 Loop A — Requirement clarification loop
1. customer/operator defines desired municipal outcome
2. Counter Question task verifies live requirement or routing
3. result is normalized into `source_type`, `structured_answer`, and `redirect_target`
4. operator decides whether to prepare or repair packet

### 5.2 Loop B — Submission loop
1. Packet Submission task attempts real filing
2. result is normalized into `accepted`, `rejected`, or `redirected`
3. if rejected, rejection reasons are classified
4. next step becomes repair, reroute, or follow-up

### 5.3 Loop C — Compliance proof loop
1. Posting Proof confirms required public display or visible compliance state
2. pass/fail output becomes replayable evidence
3. failures create remediation or revisit tasks

## 6. Minimum product requirements for the pilot

The pilot does **not** need a giant new product surface.
It does need a strict minimum contract.

### 6.1 Required task metadata
Every pilot CaaS task should capture:
- `vertical = city_ops`
- `workflow_template`
- `jurisdiction_name`
- `office_name` when known
- `required_outcome`
- `follow_on_allowed`

### 6.2 Required result metadata
Every pilot result should capture:
- `outcome_status`
- `source_type`
- `next_step_recommendation`
- attachments proving the primary result

### 6.3 Required specialized fields by template
**Counter Question**
- `structured_answer`
- `answer_confidence`
- `redirect_target`

**Packet Submission**
- `submission_result`
- `rejection_reasons[]`
- `redirect_target`
- `next_required_step`

**Posting Proof**
- `posting_present`
- `posting_legible`
- checklist result fields

## 7. Pilot operating rules

### 7.1 Manual review on all non-clean outcomes
During the pilot, every `rejected`, `redirected`, `blocked`, or `inconclusive` task should receive operator review before closure.

### 7.2 No closure without a decision artifact
A pilot task cannot close with “worker visited.”
It closes only with:
- success proof
- rejection diagnosis
- redirect target
- explicit blocked condition

### 7.3 Distinguish three truth classes everywhere
Operators and workers must keep these separate:
- `observed`
- `heard`
- `documented`

That discipline matters because municipal rumor is expensive.

### 7.4 Keep scope narrow when redirected
If an office redirects the worker, do not allow complex improvisation by default.
Return the redirect clearly and re-dispatch intentionally.
That preserves auditability.

## 8. Office memory seed model

The pilot should write a minimal reusable memory object after every meaningful episode.

### 8.1 Minimum office-memory row
- jurisdiction
- office
- workflow template
- outcome status
- rejection reasons[]
- redirect target
- queue minutes if relevant
- photo policy note if learned
- captured_at

### 8.2 Why this matters
The pilot only becomes a product wedge if the second run at the same office is better than the first.
That requires memory discipline from day one.

## 9. Worker network recommendations

### 9.1 Early worker profile
Prefer workers who can:
- follow structured instructions exactly
- report uncertainty honestly
- capture legible evidence
- avoid over-interpreting city staff answers

### 9.2 Early worker specialization tags
Use lightweight pilot tags such as:
- `permit_runner`
- `city_counter`
- `posting_verifier`
- `bilingual_es_en` when relevant

### 9.3 Training note
Do not overbuild worker training at first.
A short field guide is enough if it teaches:
- observed vs heard vs documented
- how to report redirects
- how to handle evidence restrictions
- how to avoid inventing certainty

## 10. Risk boundaries

### 10.1 What the pilot should avoid
Avoid starting with:
- complex legal interpretation tasks
- workflows needing deep domain expertise before a first attempt
- cities/offices with no realistic repeat demand
- tasks where the office outcome is impossible to evidence at all

### 10.2 Acceptable ambiguity
Some ambiguity is fine.
The pilot should support `inconclusive`.
It should not pretend ambiguity is success.

## 11. Metrics for pilot success

### 11.1 Operational metrics
- first-attempt routing accuracy
- packet acceptance rate
- redirect rate by office
- percent of tasks with machine-usable next step
- evidence completeness rate

### 11.2 Learning metrics
- repeat office memory reuse rate
- drop in avoidable redirects over time
- drop in repeated rejection reasons after memory accumulation
- percent of follow-on tasks created from structured outputs instead of manual retelling

### 11.3 Business metrics
- repeat customer usage
- time saved versus customer self-handling
- average bounty uplift for urgent/high-friction offices
- margin after operator review cost

## 12. Suggested rollout sequence

### Step 1 — Internal pilot spec lock
Freeze:
- three pilot templates
- one rejection taxonomy
- one memory write format
- one review checklist

### Step 2 — Operator trial runs
Run a handful of controlled tasks with strict review.
Goal: test evidence quality and memory usefulness, not scale.

### Step 3 — Narrow external customer pilot
Offer the service to a tiny group of repeat-need users.
Goal: validate willingness to pay and identify the highest-frequency workflow.

### Step 4 — Productize the strongest loop
Once one workflow shows repeated reuse and clean memory accumulation, convert it into a first-class dashboard/API surface.

## 13. Product decisions this pilot should answer

By the end of the pilot, EM should know:
1. which template generates the cleanest repeat demand
2. which offices justify stored playbooks first
3. which fields operators actually use in review
4. whether Packet Submission should be the true hero surface
5. what pricing multipliers correlate with friction and success

## 14. Sharp recommendation

If there is only enough bandwidth to operationalize one thing next, operationalize this:

**A Miami-area pilot around Counter Question + Packet Submission, with mandatory normalized rejection/redirect outputs and office-memory writes after every meaningful run.**

That is the smallest version of CaaS that can teach EM something durable.
