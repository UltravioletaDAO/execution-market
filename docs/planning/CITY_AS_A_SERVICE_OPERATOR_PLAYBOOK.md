# City as a Service — Operator Playbook

> Last updated: 2026-04-25
> Parent plan: `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> Companion docs:
> - `CITY_AS_A_SERVICE_TEMPLATE_SPECS.md`
> - `CITY_AS_A_SERVICE_EVIDENCE_SCHEMAS.md`
> - `CITY_AS_A_SERVICE_JURISDICTION_MODEL.md`
> Status: implementation-oriented draft

## 1. Why this doc exists

The template, evidence, and jurisdiction docs define the data model.
This playbook defines the human operating model.

City as a Service fails if workers and operators treat municipal tasks like generic errands.
It wins when EM behaves like a disciplined municipal operations desk:
- intake is strict
- routing is explicit
- evidence is normalized
- follow-up is fast
- learning compounds across offices and jurisdictions

## 2. Core operating principle

**The product is not the visit. The product is the verified next decision.**

A city task is only valuable if it leaves the customer with one of these states:
- success confirmed
- failure diagnosed
- redirect clarified
- next step made obvious

Operators should review every task through that lens.

## 3. Roles

### 3.1 Requester
The agent, operator, or business user who wants a municipal outcome.

### 3.2 Dispatcher
The EM operator or system component responsible for:
- selecting the right template
- confirming scope
- routing to the right office/jurisdiction
- setting urgency and evidence requirements

### 3.3 Worker
The field executor who performs the municipal action and returns evidence.

### 3.4 Reviewer
The person or system that validates:
- outcome status
- evidence completeness
- whether follow-on work is needed
- whether jurisdiction memory should be updated

In early rollout, Dispatcher and Reviewer may be the same operator.

## 4. Canonical operator loop

1. classify request
2. choose template
3. verify jurisdiction and office target
4. dispatch with explicit fallback instructions
5. review structured result
6. decide: close, reroute, repair, revisit, or escalate
7. persist office/jurisdiction memory updates

The system should eventually automate parts of this loop, but the manual playbook should be excellent first.

## 5. Intake checklist

Before a city task is posted, the operator should confirm:
- what outcome the customer actually wants
- whether this is a question, submission, posting check, audit, or wait/handoff
- which jurisdiction owns the workflow
- which office is the best known target
- what evidence would prove success or failure
- what the worker should do if redirected or blocked

### 5.1 Intake anti-patterns
Avoid these:
- generic prompt with no success criteria
- "go see what happens"
- no distinction between observed/heard/documented outcomes
- no fallback instruction if redirected
- no explicit next-step expectation if rejected

## 6. Template selection rules

### Use Counter Question when:
- the goal is to confirm reality before submitting anything
- the website is likely stale
- routing/requirements are unclear

### Use Packet Submission when:
- documents are ready enough for a real attempt
- acceptance, rejection, or redirect proof matters

### Use Posting Proof when:
- compliance depends on visible public display
- repeat verification may be needed

### Use Site Audit when:
- checklist-based field conditions matter more than a single question

### Use Queue Wait + Handoff when:
- presence and elapsed time are part of the value
- the handoff itself matters more than detailed office interpretation

## 7. Dispatch quality standard

A good dispatch includes:
- exact office target
- exact desired outcome
- allowed fallback behavior
- evidence checklist
- blocked/redirect handling instruction
- time budget and urgency

A weak dispatch produces narrative chaos and low replay value.

## 8. Fallback instruction patterns

Every CaaS task should include one fallback rule.

### 8.1 If redirected
Worker must capture:
- redirect destination
- who/what caused the redirect
- whether the redirect appears routine or exceptional

Default next action:
- do not improvise a new complex workflow unless the task explicitly allows it
- return the redirect clearly so the system can re-route deliberately

### 8.2 If evidence capture is restricted
Worker must capture:
- that evidence was refused or restricted
- who imposed the restriction if known
- alternate proof available (receipt, signage note, written summary)

### 8.3 If office is closed or unreachable
Worker must capture:
- closure condition
- signage or notice if visible
- whether other people/staff indicated alternate routing

## 9. Review checklist by outcome

### 9.1 Completed / Accepted
Reviewer checks:
- is success actually proven?
- is the proof primary or secondary?
- does a follow-on step now unlock?
- should office playbook confidence increase?

### 9.2 Rejected
Reviewer checks:
- is the rejection reason explicit and machine-usable?
- is the failure due to document quality, wrong office, fee/payment, appointment rule, or policy drift?
- is the next step repairable immediately?

### 9.3 Redirected
Reviewer checks:
- is the redirect target clear enough to dispatch the next run?
- was the original office wrong, outdated, or ambiguous?
- should routing memory be updated?

### 9.4 Blocked / Inconclusive
Reviewer checks:
- what prevented resolution?
- is this a normal office constraint or a task-design failure?
- should the retry happen later, elsewhere, or with a different template?

## 10. When to spawn follow-on work

Create follow-on work when the result clearly unlocks a next step.

### Common chains
- Counter Question → Packet Submission
- Packet Submission rejected → doc repair + resubmission
- Packet Submission accepted → Posting Proof or inspection prep
- Posting Proof failed → remediation task
- Redirected office → rerouted Counter Question or Submission

### Do not chain automatically when:
- evidence is weak
- the redirect is ambiguous
- staff guidance conflicts with documentation
- the workflow may require legal/compliance review first

## 11. Municipal memory update rules

After review, the operator should ask:
- did we learn something reusable about this office?
- did we observe a repeatable rejection pattern?
- did the office route differently than the website suggests?
- did the worker surface a durable photo/queue/appointment rule?

### Minimum memory write for meaningful episodes
Persist at least:
- office
- workflow template
- outcome status
- rejection reasons
- redirect target
- queue minutes if relevant
- risk flags

## 12. Risk flags operators should care about

Recommended first operator-visible flags:
- `process_drift`
- `website_stale_risk`
- `repeat_rejection_pattern`
- `photo_restricted`
- `office_closed_unexpectedly`
- `appointment_required`
- `wrong_office_risk`
- `customer_doc_issue`

These should show up in replay views and, later, in pre-dispatch warnings.

## 13. Escalation rules

Escalate for human/operator review when:
- two consecutive tasks fail for contradictory reasons
- redirect patterns bounce between offices
- staff guidance conflicts with documented instructions
- the customer documents appear fundamentally broken
- evidence restrictions make the result too weak for confident closure

## 14. Pilot operating model recommendation

For a first metro launch, keep the operator model intentionally tight.

### Pilot constraints
- one metro area
- three templates first: Counter Question, Packet Submission, Posting Proof
- one shared rejection taxonomy
- one small office-memory surface
- manual review on all rejected/redirected outcomes

### Why this is right
It creates a high-signal learning loop without pretending national scale too early.

## 15. Metrics that actually matter

Do not optimize early for raw task volume.
Optimize for municipal learning quality.

### Leading metrics
- first-attempt routing accuracy
- acceptance rate for packet submissions
- redirect rate by office
- percent of tasks with machine-usable next step
- evidence completeness rate
- repeat office memory reuse rate

### Lagging metrics
- turnaround time
- repeat customer usage
- avoided revisit count
- workflow completion per municipal case

## 16. Product implication

This playbook implies the product should eventually surface:
- intake controls for fallback behavior
- reviewer controls for memory updates
- operator summaries grouped by office/template
- warning banners before known bad routes
- one-click follow-on task creation from structured results

## 17. Sharpest recommendation

If only one operator habit is enforced first, enforce this:

**Never close a city task without a clear next-decision artifact: success proof, rejection diagnosis, or redirect target.**

That rule keeps City as a Service aligned with what customers actually pay for: not motion, but progress.
