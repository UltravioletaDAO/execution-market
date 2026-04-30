# City as a Service — Acontext Memory Bridge

> Last updated: 2026-04-25
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_PILOT_BLUEPRINT.md`
> - `CITY_AS_A_SERVICE_JURISDICTION_MODEL.md`
> - `CITY_AS_A_SERVICE_OPERATOR_PLAYBOOK.md`
> - `../acontext-integration-plan.md`
> Status: implementation-oriented planning draft

## 1. Why this doc exists

The existing CaaS documents define:
- the product thesis
- the pilot shape
- the evidence schemas
- the jurisdiction memory model
- the operator workflow

What they do not yet define sharply enough is **how municipal memory becomes agent-usable context**.
This document closes that gap.

The goal is simple:

> Every meaningful city task should improve the quality of the next city task.

That requires a bridge between:
- raw execution data in Execution Market
- live coordination in IRC/swarm systems
- human/operator review
- compact retrieval-ready context for future dispatch

## 2. Core thesis

Execution Market's moat in City as a Service is not only access to workers.
It is the ability to accumulate **decision-quality municipal memory**:
- which office actually handles the workflow
- which redirects are routine
- which rejection reasons repeat
- which evidence patterns are accepted
- which workers succeed in which environments

Acontext is a strong candidate for the memory-and-observability layer that turns those episodes into reusable operational context.

## 3. System split

### 3.1 Execution Market should remain the canonical ledger

Execution Market database remains source of truth for:
- tasks
- applications
- assignments
- submissions
- approvals
- payouts
- worker and requester reputation events

### 3.2 Acontext should hold the reusable working intelligence layer

Acontext should hold:
- jurisdiction briefs
- office playbooks
- reviewed episode summaries
- workflow pattern aggregates
- compact coordination event logs
- dispatch-time retrieval artifacts

This separation matters.
Acontext should help operators and agents think better, not replace the execution ledger.

## 4. Memory objects that matter most

## 4.1 Jurisdiction brief
A compressed artifact answering:
- what kinds of workflows are common here?
- what routing traps appear often?
- which offices matter most?
- what drift/risk signals should dispatchers know?

## 4.2 Office playbook
The most important operational artifact.
It should summarize:
- workflow coverage
- redirect targets
- photo/receipt/appointment behavior
- common rejection patterns
- queue tendencies
- confidence score
- last verified date

## 4.3 Reviewed episode summary
Every meaningful reviewed task should produce a compact narrative:
- what happened
- what outcome class was reached
- what changed in our understanding
- what a future similar task should do differently

## 4.4 Workflow pattern aggregate
Cross-office or per-office aggregates such as:
- top rejection reasons for Packet Submission
- most common redirect targets for Counter Question
- failure modes for Posting Proof
- evidence completeness gaps by template

## 4.5 Worker familiarity summary
Eventually, dispatch should know not just who is nearby, but who is proven in context.
This object should summarize:
- workflow-specific completion count
- documentation fidelity
- redirect handling quality
- acceptance or closure quality signals
- recency of office familiarity

## 5. Proposed event flow

### 5.1 Execution event layer
Execution Market records task lifecycle events in the product DB.
Examples:
- task created
- worker assigned
- submission received
- review completed
- approval/rejection finalized

### 5.2 Coordination layer
IRC/swarm systems emit live human-readable coordination events.
Examples:
- operator escalated
- worker redirected
- office closed unexpectedly
- follow-on task recommended

### 5.3 Projector layer
A memory projector transforms reviewed execution into reusable artifacts.
Suggested outputs:
- office playbook delta
- jurisdiction brief delta
- episode summary
- workflow counters
- observability tags

### 5.4 Retrieval layer
Before future dispatch, the system retrieves the most relevant compressed context and injects it into operator or agent decision-making.

## 6. Write rules

Acontext writes should happen **after review**, not merely after worker upload.
That avoids baking unreviewed or ambiguous interpretations into the memory layer.

### 6.1 Safe default trigger
Best initial trigger:
- submission reviewed by operator/system
- outcome normalized into canonical structured result
- follow-on recommendation decided

### 6.2 What should be written automatically
Good candidates for automated writes:
- episode summary drafts
- rejection frequency counters
- redirect counters
- office last-seen timestamps
- evidence completeness metrics

### 6.3 What should remain operator-reviewed initially
Keep these human-reviewed at first:
- office reliability score
- office policy conclusions
- likely-hours summaries
- playbook confidence increases
- difficulty scores

## 7. Retrieval rules at dispatch time

Before dispatching a CaaS task, retrieve:
- relevant jurisdiction brief
- office playbook if office known
- recent episodes for same workflow template
- top rejection reasons for that office/template pair
- top redirect targets
- risk flags and confidence levels

The retrieved brief should shape:
- worker instructions
- fallback behavior
- urgency pricing
- escalation thresholds
- whether to split work into a clarifying Counter Question first

## 8. Example dispatch briefing

For a Packet Submission task, the dispatch-time briefing might say:
- this office has redirected 4 of the last 7 submissions to Window B
- outdated form version is the top rejection reason
- receipts are usually issued only on accepted packets
- photos at counter are inconsistently tolerated
- bilingual workers have had higher documentation fidelity here

That is the kind of intelligence that makes the next run materially better.

## 9. Observability model

Acontext should also support cross-project observability, not just storage.

Recommended first CaaS metrics:
- first-attempt routing accuracy
- redirect rate by office/template
- repeated rejection rate before vs after playbook updates
- evidence completeness rate
- percent of tasks with machine-usable next-step recommendation
- memory reuse rate at dispatch time
- worker familiarity lift compared with proximity-only matching

These metrics answer whether the memory loop is working.

## 10. IRC session management implications

IRC is useful as the live conversational bus, but not as the long-term memory system.
The bridge design should therefore:
- keep IRC for real-time coordination
- emit stable event names from meaningful moments
- mirror those events into compact Acontext records
- allow session summaries to reference those events during intervention or review

Examples of useful event names:
- `dispatch_created`
- `office_redirect_observed`
- `submission_reviewed`
- `playbook_delta_written`
- `review_escalated`

This creates a cleaner coordination stack:
- **IRC:** live operations
- **EM DB:** execution truth
- **Acontext:** reusable memory + observability

## 11. Minimal pre-Docker implementation path

Even if live Acontext infra is blocked, EM can prepare immediately:

1. define artifact schemas in-repo
2. create a local projector interface
3. emit JSON/Markdown files in an Acontext-shaped directory structure
4. standardize event names from review/coordination flows
5. define dispatch briefing contracts now

Then the sink can later swap from local files to Acontext API calls with minimal redesign.

## 12. Recommended first build order

1. Define a reviewed `episode_summary` schema
2. Define an `office_playbook` JSON contract
3. Add stable coordination event names in swarm/IRC flows
4. Build a local projector that writes artifacts after review
5. Build a retrieval helper that composes a dispatch briefing from those artifacts
6. Only then wire the same contracts into Acontext server APIs

## 13. Sharpest insight

The point is not to give agents more memory in general.
The point is to make **verified city reality reusable**.

If Execution Market can do that reliably, City as a Service stops being a labor marketplace feature and becomes municipal operating infrastructure.

## 14. Coordination event contract for cross-project reuse

To connect CaaS memory with the swarm control plane and broader cross-project decision systems, the memory bridge should standardize one reusable coordination event contract instead of inventing a city-only dialect.

### 14.1 Shared event envelope
Every replayable coordination event should be representable with the same compact envelope whether it originates from:
- a city task dispatch
- an EM swarm routing decision
- an IRC intervention or escalation
- a future cross-project decision-support pipeline

Suggested shared fields:
- `event_name`
- `coordination_session_id`
- `task_id`
- `vertical`
- `workflow_template`
- `jurisdiction_name`
- `office_name`
- `actor_type` (`agent`, `worker`, `operator`, `system`)
- `actor_id`
- `decision_phase` (`dispatch`, `execution`, `review`, `memory_write`, `redispatch`)
- `decision_summary`
- `risk_flags[]`
- `memory_write_recommended`
- `event_time`

### 14.2 Why this matters
This lets the same retrieval and observability surfaces answer questions across scopes, for example:
- what happened in IRC before a redirect was accepted as real?
- which operator interventions changed the next dispatch brief?
- which decision phases correlate with repeated rejection avoidance?
- where does the city workflow look different from generic swarm routing, and where is it actually the same?

### 14.3 Minimal implementation stance
Before Acontext is live, the local projector should write this envelope beside reviewed artifacts so daytime builders can:
- replay the exact event chain
- mirror the same payload into IRC summaries
- feed one stable schema into observability dashboards
- later swap the sink from local files to Acontext without rethinking the event model

## 15. Dispatch intelligence ladder

Not every retrieved artifact should influence the next task equally. The bridge should therefore rank retrieval outputs by decision weight.

### 15.1 Recommended priority order
1. `office_playbook_after` for known office + template pairs
2. `reviewed_episode` recency-weighted summaries for the same workflow template
3. rejection/redirect aggregates for the same jurisdiction
4. worker familiarity summaries for candidate assignees
5. coordination-event summaries showing recent escalations or drift

### 15.2 Dispatch-time rule
If higher-confidence artifacts exist, the briefing should degrade gracefully rather than mixing strong and weak memory into one undifferentiated blob.
That means the briefing should explicitly separate:
- **trusted operational guidance**
- **recent but weak signals**
- **open questions to resolve on-site**

This is important because city work is full of partial truths. A good memory bridge does not merely retrieve more context; it preserves decision hygiene under uncertainty.
