# City as a Service — Review Loop State Machine

> Last updated: 2026-04-27
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_IMPLEMENTATION_SLICE.md`
> - `CITY_AS_A_SERVICE_TYPED_VALIDATORS_AND_FIXTURE_SCHEMA.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The remaining risk in the CaaS planning stack is not lack of strategy.
It is transition ambiguity.

Daytime now has:
- the object contracts
- the replay fixtures
- the observability model
- the first implementation slice

What is still easy to misbuild is **when a reviewed city task is allowed to promote memory, emit learning, and influence the next dispatch**.

This doc defines the smallest explicit state machine for that review loop.

## 2. Core principle

**Raw submission is not memory. Reviewed closure is the promotion gate.**

The state machine should make three things impossible to confuse:
- when a city task is still only evidence collection
- when an operator has produced normalized truth
- when that truth is strong enough to change office memory and dispatch behavior

## 3. The minimum states

The first implementation only needs six states.

### 3.1 `awaiting_submission`
Meaning:
- task exists
- no worker submission has arrived yet

### 3.2 `submission_received`
Meaning:
- raw worker evidence exists
- nothing has been normalized or trusted yet

Hard rule:
- no office memory writes
- no dispatch-brief learning claims

### 3.3 `under_review`
Meaning:
- operator is actively reviewing raw evidence into a `reviewed_result`

Hard rule:
- draft normalization may exist
- no durable playbook delta yet

### 3.4 `reviewed_no_learning`
Meaning:
- reviewed closure exists
- task may be complete, but outcome is too weak, too ambiguous, or too narrow to promote into office memory

Examples:
- evidence insufficient
- one-off anomaly with low confidence
- closure approved but memory-write recommendation is false

### 3.5 `reviewed_with_learning`
Meaning:
- reviewed closure exists
- normalized output is strong enough to emit a `reviewed_episode`
- optional `office_playbook_delta` may be promoted
- future dispatch may now change because of this task

### 3.6 `review_escalated`
Meaning:
- operator could not safely finalize the reviewed result without additional human judgment or follow-up

Hard rule:
- escalation can block closure or reroute into follow-on review
- escalated tasks should be visible in observability as unresolved learning pressure

## 4. Allowed transitions

```text
awaiting_submission -> submission_received
submission_received -> under_review
under_review -> reviewed_no_learning
under_review -> reviewed_with_learning
under_review -> review_escalated
review_escalated -> under_review
review_escalated -> reviewed_no_learning
review_escalated -> reviewed_with_learning
```

Transitions that should be forbidden in the first slice:
- `submission_received -> reviewed_with_learning` without review
- `submission_received -> reviewed_no_learning` without review
- `awaiting_submission -> reviewed_*`
- `reviewed_no_learning -> reviewed_with_learning` without explicit new review action

## 5. Transition outputs

### 5.1 `submission_received -> under_review`
Should create:
- review work item
- draft normalized form state if desired

Should emit:
- `city_review_started`

### 5.2 `under_review -> reviewed_no_learning`
Should create:
- final `reviewed_result`
- final `review_artifact`
- optional follow-on recommendation

Should not create:
- `office_playbook_delta`
- memory-backed dispatch changes

Should emit:
- `city_review_completed`

### 5.3 `under_review -> reviewed_with_learning`
Should create:
- final `reviewed_result`
- final `review_artifact`
- `reviewed_episode`
- optional `office_playbook_delta`
- updated `dispatch_brief`

Should emit in stable order:
1. `city_review_completed`
2. `city_reviewed_episode_written`
3. `city_office_playbook_delta_written` (when delta exists)
4. `city_dispatch_brief_composed`

### 5.4 `under_review -> review_escalated`
Should create:
- escalation reason
- unresolved review marker
- optional recommended follow-up action

Should emit:
- `city_review_escalated`

## 6. Decision rules for learning promotion

A reviewed city task should only enter `reviewed_with_learning` when all of these are true:
- `reviewed_result` validates
- `review_artifact` validates
- review status is explicitly approved
- `memory_write_recommended = true`
- at least one learning claim is attributable and bounded
- provenance to the reviewed task is preserved

A reviewed city task should land in `reviewed_no_learning` when any of these are true:
- outcome closed but confidence is too weak
- evidence exists but is too incomplete for durable guidance
- observed fact is too local or incidental to justify office memory
- operator wants task closure without doctrine promotion

## 7. Interaction with replay fixtures

The fixture harness should assert state transitions directly, not just final artifacts.

At minimum each replay case should prove:
- its starting state
- its final review state
- whether learning promotion was allowed
- which events were emitted because of that decision

This matters because many likely bugs will be transition bugs, not schema bugs.
Example:
- a valid `reviewed_result` that should still not promote memory because evidence confidence is too weak

## 8. Interaction with operator surfaces

### Review Console
Must expose:
- current review state
- promotion eligibility
- reasons learning is blocked
- preview of memory impact before confirmation

### Dispatch Brief Panel
Must only consume artifacts from `reviewed_with_learning` paths.
It should never treat `reviewed_no_learning` tasks as authoritative office memory.

### Office Memory View
Must distinguish:
- reviewed episodes stored for replay/history
- actual promoted office playbook guidance
- escalated or blocked cases still awaiting safe interpretation

## 9. First failure modes this state machine prevents

### 9.1 Raw-submission doctrine
Worker speculation becomes office truth without review.

### 9.2 Ambiguous closure promotion
A task closes successfully, but weak evidence still gets promoted as if reliable.

### 9.3 Hidden escalation debt
Operators keep punting hard cases, but the system looks healthy because closures are counted without state clarity.

### 9.4 Dispatch contamination
Future briefs start quoting episodes that were reviewed but explicitly not approved for learning.

## 10. Strong recommendation

Before broader city UI work, daytime should implement this tiny state machine alongside the contract validators.

That gives the first CaaS slice a clean rule:
**only reviewed-with-learning outcomes are allowed to change future city behavior.**
