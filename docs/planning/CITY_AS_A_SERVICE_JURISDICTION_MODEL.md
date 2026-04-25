# City as a Service — Jurisdiction Model

> Last updated: 2026-04-25
> Parent plan: `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> Companion docs: `CITY_AS_A_SERVICE_TEMPLATE_SPECS.md`, `CITY_AS_A_SERVICE_EVIDENCE_SCHEMAS.md`
> Status: implementation-oriented draft

## 1. Thesis

City as a Service becomes defensible when Execution Market remembers municipal reality better than any single operator can.

That memory has to be keyed by jurisdiction and office, not just by generic task category.
Without a jurisdiction model, every city task is an expensive one-off.
With it, each task improves routing, instructions, pricing, and success rates for the next one.

## 2. What this model needs to do

The jurisdiction layer should help EM answer:
- which office actually handles this workflow?
- what quirks or rejection patterns apply here?
- what evidence norms work at this office?
- which workers have proven familiarity here?
- when should the system reroute, escalate, or warn the operator?

## 3. Core object types

Recommended MVP object set:
1. Jurisdiction profile
2. Office profile
3. Workflow playbook
4. Observed episode
5. Worker familiarity summary

## 4. Jurisdiction profile

A jurisdiction is the policy boundary the workflow belongs to.
Examples:
- City of Miami
- Miami-Dade County
- specific authority or special district
- state licensing office

### 4.1 Fields
- `jurisdiction_id`
- `jurisdiction_name`
- `jurisdiction_type` = city | county | state_office | special_district | other
- `region_label`
- `parent_jurisdiction_id` nullable
- `timezone`
- `active_workflow_types[]`
- `difficulty_score`
- `last_verified_at`

### 4.2 Why this matters
The same business workflow may resolve differently depending on whether the real decision-maker is city, county, or state.
The model must support nested jurisdiction reality instead of assuming the city name is enough.

## 5. Office profile

The office profile is the most important operational memory object.
This is where EM learns how municipal reality actually behaves.

### 5.1 Fields
- `office_id`
- `jurisdiction_id`
- `office_name`
- `office_type`
- `location_label`
- `service_categories[]`
- `likely_hours`
- `photo_policy` = allowed | restricted | unknown | mixed
- `appointment_bias` = required | preferred | optional | unknown
- `walk_in_bias` = reliable | inconsistent | unlikely | unknown
- `queue_pattern_notes`
- `redirect_targets[]`
- `reliability_score`
- `last_observed_at`

### 5.2 Behavioral flags
- `frequently_redirects`
- `website_stale_risk`
- `receipt_issued_reliably`
- `counter_question_friendly`
- `packet_submission_friendly`
- `evidence_capture_sensitive`

## 6. Workflow playbook

A workflow playbook captures the known best path for a specific task type within a jurisdiction/office pair.

### 6.1 Fields
- `playbook_id`
- `jurisdiction_id`
- `office_id` nullable
- `workflow_template`
- `required_documents[]`
- `common_rejection_reasons[]`
- `common_redirect_targets[]`
- `expected_elapsed_minutes`
- `best_visit_windows[]`
- `photo_capture_guidance`
- `playbook_confidence`
- `version`
- `last_updated_at`

### 6.2 Why this matters
This is how EM stops relearning the same rejection loop over and over.
A good playbook turns raw evidence episodes into reusable operator advantage.

## 7. Observed episode

Every completed city task should create a structured observation record that can update the memory layer.

### 7.1 Fields
- `episode_id`
- `jurisdiction_id`
- `office_id`
- `workflow_template`
- `outcome_status`
- `source_type`
- `rejection_reasons[]`
- `redirect_target`
- `queue_minutes`
- `worker_id`
- `task_id`
- `captured_at`
- `confidence_score`
- `risk_flags[]`

### 7.2 Why this matters
The episode is the raw learning unit.
Office profiles and playbooks should be updated from accumulated episodes, not vibes.

## 8. Worker familiarity summary

CaaS needs more than location proximity.
It needs evidence that a worker handles a given municipal environment well.

### 8.1 Fields
- `worker_id`
- `jurisdiction_id`
- `office_id` nullable
- `workflow_template`
- `completed_count`
- `acceptance_rate_signal`
- `redirect_handling_score`
- `documentation_fidelity_score`
- `avg_queue_tolerance_minutes`
- `last_seen_at`

### 8.2 Matching use
This object can eventually improve dispatch by preferring workers who have already succeeded at:
- the same office
- the same workflow type
- the same style of evidence expectations

## 9. Recommended hierarchy

Use a layered hierarchy:

1. **Jurisdiction**
2. **Office**
3. **Workflow playbook**
4. **Observed episodes**
5. **Worker familiarity summaries**

This keeps static-ish metadata separate from live observed behavior.

## 10. Update rules

### 10.1 What should update automatically
From completed tasks, EM can automatically derive:
- last observed office activity
- queue-time patterns
- redirect frequencies
- common rejection frequencies
- worker familiarity counters

### 10.2 What should stay operator-reviewed at first
To avoid hallucinated memory, keep these human-reviewed initially:
- office reliability score
- likely hours summary
- formal playbook changes
- photo policy conclusions
- jurisdiction difficulty score

## 11. Confidence model

Municipal memory should carry explicit confidence.
Not every observation deserves to become doctrine.

### 11.1 Suggested confidence sources
- single episode, low confidence
- repeated consistent episodes, medium confidence
- repeated episodes across multiple workers, high confidence
- documented proof that matches field reality, highest confidence

### 11.2 Use of confidence
Low-confidence memory should inform warnings.
High-confidence memory can influence automation and pricing.

## 12. Routing logic implications

The jurisdiction model should eventually inform task routing in four ways:

### 12.1 Office targeting
If a workflow repeatedly redirects from Office A to Office B, default new tasks to Office B.

### 12.2 Worker matching
Prefer workers with demonstrated familiarity when stakes are high.

### 12.3 Pricing
Raise difficulty/urgency pricing where:
- redirect rates are high
- queue times are volatile
- evidence capture is hard

### 12.4 Escalation
Flag high-risk workflows early when a jurisdiction shows:
- chronic rejection patterns
- ambiguous office ownership
- no reliable evidence norms yet

## 13. Minimal MVP data model

If EM wants the smallest useful version, start with these fields only.

### Jurisdiction
- `jurisdiction_name`
- `jurisdiction_type`

### Office
- `office_name`
- `service_categories[]`
- `photo_policy`
- `last_observed_at`

### Episode
- `workflow_template`
- `outcome_status`
- `rejection_reasons[]`
- `redirect_target`
- `queue_minutes`
- `captured_at`

That alone is enough to start compounding learning.

## 14. Miami pilot recommendation

For a Miami-area pilot, the model should stay intentionally simple.

### Pilot scope recommendation
Track only:
- jurisdiction
- office
- workflow template
- redirect target
- rejection reason
- queue time
- photo policy note

Do not try to build a national municipal ontology on day one.
Start with one metro area and let the data model expand from real pain.

## 15. Product surfaces implied by this model

### Operator dashboard
- office cards
- common rejection reasons
- known redirect map
- last-seen queue/office activity

### Task creation UX
- jurisdiction selector
- office suggestions
- warning banners for unreliable offices
- playbook suggestions from past runs

### Worker UX
- office-specific instructions
- photo policy guidance
- redirect handling defaults

## 16. Sharp recommendation

If only one jurisdiction-memory feature ships first, make it this:

**Every city task should emit a reusable `office + workflow_template + outcome_status + rejection_reasons[] + redirect_target` episode.**

That single discipline creates the seed crystal for a real municipal intelligence moat.