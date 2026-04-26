# City as a Service — Implementation Slice v1

> Last updated: 2026-04-26
> Status: build-sequencing spec
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_PILOT_BLUEPRINT.md`
> - `CITY_AS_A_SERVICE_OPERATOR_PLAYBOOK.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `CITY_AS_A_SERVICE_LOCAL_PROJECTOR_BOOTSTRAP.md`

## 1. Why this doc exists

The planning stack is now deep enough.
What is still missing is a single engineering-facing slice that says:
- what to build first
- which objects are real
- which UI surfaces own which state
- what counts as done

This doc narrows the next implementation move to one product loop:

**template -> reviewed result -> memory write -> better next dispatch**

That is the smallest slice that can prove City as a Service is compounding intelligence instead of just routing labor.

## 2. Product thesis for the first build

The first implementation should not try to ship “City as a Service” broadly.
It should prove one thing:

> reviewed municipal outcomes can be converted into reusable office memory that improves the next dispatch.

If that loop works, the rest of the vertical gets easier.
If that loop fails, more templates and more UI will only scale noise.

## 3. Scope of the first implementation slice

### In scope
- `counter_question` and `packet_submission` only
- reviewed result capture
- reviewed episode artifact generation
- office playbook delta generation
- local dispatch brief composition
- minimal operator-facing surfaces for review and retrieval

### Explicitly out of scope
- national or multi-metro rollout
- Acontext server dependency
- fully automated memory writes from raw submissions
- generalized workflow engine
- broad city-ops catalog expansion
- Posting Proof implementation beyond contract compatibility

## 4. The five stable objects

If the first slice keeps anything stable, it should keep these stable.

### 4.1 `reviewed_result`
The normalized closure object for a single city task.

Must contain:
- `task_id`
- `vertical`
- `workflow_template`
- `jurisdiction_name`
- `office_name`
- `outcome_status`
- `source_type`
- `confidence_score`
- `structured_result`
- `rejection_reasons[]`
- `redirect_target`
- `next_step_recommendation`
- `risk_flags[]`
- `reviewed_at`
- `reviewed_by`

### 4.2 `review_artifact`
The operator’s promotion decision.

Must contain:
- `task_id`
- `review_status`
- `closure_type`
- `result_trust_level`
- `memory_write_recommended`
- `memory_write_preview`
- `follow_on_recommendation`
- `notes`

### 4.3 `reviewed_episode`
The replayable summary of one meaningful municipal interaction.

Must contain:
- `episode_id`
- `task_id`
- `office_key`
- `workflow_template`
- `outcome_status`
- `what_happened`
- `why_it_matters`
- `learned_routing_fact`
- `learned_rejection_fact`
- `evidence_warnings[]`
- `recommended_next_dispatch_change`
- `captured_at`

### 4.4 `office_playbook_delta`
The office-memory mutation derived from one reviewed episode.

Must contain:
- `office_key`
- `workflow_template`
- `delta_type`
- `rejection_reason_counts`
- `redirect_target_counts`
- `photo_policy_note`
- `queue_time_observation`
- `routing_note`
- `confidence_delta`
- `derived_from_episode_id`

### 4.5 `dispatch_brief`
The compact retrieval artifact used before the next task is created or rerouted.

Must contain:
- `office_key`
- `workflow_template`
- `jurisdiction_summary`
- `top_rejection_reasons[]`
- `top_redirect_targets[]`
- `evidence_warnings[]`
- `fallback_instruction`
- `freshness_summary`
- `last_reviewed_episode_ids[]`

## 5. Required operator surfaces

The first slice only needs three surfaces.

### 5.1 Review Console
Purpose:
turn raw worker evidence into a valid `reviewed_result`.

Must support:
- side-by-side raw evidence and normalized result form
- explicit selection of `outcome_status`
- explicit selection of `source_type`
- structured template-specific result fields
- rejection/redirect capture
- memory write preview before confirm
- follow-on recommendation preview before confirm

Hard rule:
no office memory is written directly from raw worker submission.
The Review Console is the promotion gate.

### 5.2 Dispatch Brief Panel
Purpose:
inject memory into the next dispatch decision.

Must show:
- office/jurisdiction summary
- top rejection reasons
- top redirect targets
- evidence warnings
- fallback instruction recommendation
- freshness and number of reviewed episodes behind the brief

Hard rule:
this panel must be compact enough to guide an operator in under a minute.

### 5.3 Office Memory View
Purpose:
make the memory loop inspectable and correctable.

Must show:
- current office playbook summary
- recent reviewed episodes
- rejection/redirect concentration
- confidence/freshness markers
- latest delta provenance

Hard rule:
this is an operational trust surface, not a long-form knowledge browser.

## 6. Build sequence

### Step 1 — finalize the shared reviewed-result contract
Implement one typed contract for:
- `counter_question`
- `packet_submission`
- compatible shared fields for future `posting_proof`

Acceptance gate:
- fixture submissions can be transformed into valid `reviewed_result` payloads without ambiguity

### Step 2 — build Review Console state and validation
Implement the minimum review surface and form rules.

Acceptance gate:
- operator cannot close a city task without producing a valid reviewed result and promotion decision

### Step 3 — emit local projector artifacts
Write:
- reviewed result
- reviewed episode
- office playbook delta
- updated office playbook

Acceptance gate:
- artifacts are deterministic across reruns of the same fixture set
- raw submissions never bypass review

### Step 4 — compose dispatch briefs from local artifacts
Generate a compact `dispatch_brief` from office/jurisdiction memory.

Acceptance gate:
- repeated reviewed runs at the same office/template produce visibly richer pre-dispatch guidance

### Step 5 — render Dispatch Brief Panel
Expose retrieval at task creation, reroute, and resubmission moments.

Acceptance gate:
- operator sees concrete routing and evidence guidance before dispatch

### Step 6 — expose Office Memory View
Make it possible to inspect why the brief says what it says.

Acceptance gate:
- operator can trace a briefing claim back to recent reviewed episodes and deltas

### Step 7 — only then replace local sink with Acontext sink
Do not make live Acontext infra the blocker.

Acceptance gate:
- sink swap changes transport, not product behavior or object semantics

## 7. Data-flow contract

### 7.1 Review-time flow
1. worker submission arrives
2. operator reviews raw evidence
3. operator produces `reviewed_result`
4. system generates `review_artifact`
5. projector emits `reviewed_episode`
6. projector emits `office_playbook_delta`
7. office playbook is merged
8. future dispatches consume `dispatch_brief`

### 7.2 Dispatch-time flow
1. operator selects or reroutes a city template
2. system resolves office/jurisdiction context
3. system reads local office playbook + recent episodes
4. system composes `dispatch_brief`
5. operator adjusts instructions and fallback behavior before dispatch

## 8. Minimal metrics for this slice

Do not judge the first build by volume.
Judge it by replay quality.

### Product-loop metrics
- percent of city tasks closed with valid `reviewed_result`
- percent of meaningful episodes producing memory artifacts
- memory reuse rate on later office/template dispatches
- percent of briefs backed by at least one reviewed episode
- operator edits to dispatch instructions after seeing the brief

### Outcome-learning metrics
- redirect concentration by office/template
- repeated rejection reason concentration
- routing accuracy on second attempt vs first attempt
- percent of tasks with machine-usable `next_step_recommendation`

## 9. Recommended acceptance scenario

The first slice should be considered real only if this scenario works:

1. a `counter_question` task is reviewed
2. the review creates a `reviewed_result`
3. the local projector writes a `reviewed_episode` and office playbook delta
4. a later `packet_submission` at the same office/template family opens with a dispatch brief
5. that brief includes a rejection warning, redirect hint, or evidence warning learned from the earlier reviewed work
6. the operator can inspect which reviewed episode caused that recommendation

If this scenario works, the system is learning.
If not, it is just logging.

## 10. Strong recommendation

The next engineering move should not be more concept expansion.
It should be this narrow implementation slice with local artifacts first.

That keeps the work aligned with the actual moat:
**reviewed municipal reality turned into better future dispatch decisions.**
