# City as a Service — Observability and Success Metrics

> Last updated: 2026-04-26
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `MASTER_PLAN_STABILITY_OBSERVABILITY.md`
> Status: implementation-oriented planning draft

## 1. Why this doc exists

The CaaS planning stack now defines:
- the product wedge
- the pilot shape
- the reviewed result contract
- the reviewed episode and playbook delta seam
- the Acontext/local-projector bridge
- the first operator surfaces

What is still easy to hand-wave is whether the loop is actually working.
This document defines the first observability layer for CaaS so daytime implementation can answer one hard question:

> Are reviewed city tasks producing measurably better future dispatch decisions?

## 2. Core thesis

CaaS observability should not optimize for generic marketplace throughput first.
It should optimize for **decision-quality improvement over repeated municipal work**.

The system is healthy when:
- the right office is chosen earlier
- redirects happen less often
- rejection causes become predictable
- dispatch briefs become more useful
- reviewed memory changes operator behavior in measurable ways

## 3. Product loop to measure

The loop to instrument is:
1. city task created
2. worker executes
3. operator reviews into `reviewed_result`
4. projector emits `reviewed_episode` + `office_playbook_delta`
5. later task retrieves `dispatch_brief`
6. operator dispatches differently because of prior memory
7. outcome improves or at least uncertainty shrinks

If any link in that loop is invisible, the product will drift into vibes instead of compounding execution quality.

## 4. Metric families

## 4.1 Review quality metrics

These answer whether raw worker output is being converted into trusted city artifacts.

### Required first metrics
- `review_completion_rate`
  - percent of submitted city tasks that reach reviewed closure
- `review_latency_minutes`
  - time from worker submission to reviewed result
- `memory_write_recommendation_rate`
  - percent of reviewed tasks marked safe/useful for memory promotion
- `insufficient_evidence_rate`
  - percent of city submissions that fail review because evidence or structure is unusable
- `review_escalation_rate`
  - percent of reviewed tasks requiring operator escalation

### Why they matter
If review is too slow, too noisy, or too often inconclusive, the memory loop never compounds.

## 4.2 Routing quality metrics

These answer whether the office/template routing is getting smarter.

### Required first metrics
- `first_attempt_routing_accuracy`
  - percent of tasks that reach the correct office/window/process without redirect
- `redirect_rate_by_office_template`
  - percent of reviewed tasks with `outcome_status=redirected`
- `repeat_redirect_rate`
  - percent of repeated runs that hit the same redirect after a playbook update already existed
- `counter_question_preflight_lift`
  - difference in redirect/rejection rate when a Counter Question happened before Packet Submission
- `office_scope_correction_count`
  - number of times memory changed which office is believed to own the workflow

### Why they matter
Routing quality is the clearest signal that prior city episodes are improving the next run.

## 4.3 Rejection learning metrics

These answer whether the system is learning from failure instead of repeating it.

### Required first metrics
- `rejection_rate_by_office_template`
  - percent of reviewed tasks with `outcome_status=rejected`
- `top_rejection_reason_concentration`
  - share of rejections explained by the top 1-3 reasons
- `repeat_rejection_same_reason_rate`
  - percent of repeated runs rejected again for a reason already present in the dispatch brief
- `rejection_to_playbook_delta_latency`
  - time from reviewed rejection to visible playbook delta
- `resubmission_success_after_learning_rate`
  - percent of reruns/resubmits that succeed after a prior reviewed rejection

### Why they matter
A rejection that becomes a better next dispatch is product learning.
A rejection that repeats unchanged is wasted field effort.

## 4.4 Memory reuse metrics

These answer whether the memory bridge is being used, not just written.

### Required first metrics
- `dispatch_brief_presence_rate`
  - percent of city task dispatches where a brief existed
- `dispatch_brief_open_rate`
  - percent of dispatches where operator viewed/expanded the brief
- `dispatch_brief_reuse_rate`
  - percent of dispatched tasks that referenced prior office/template memory
- `memory_artifact_freshness_days`
  - age of latest reviewed episode/playbook artifact used at dispatch
- `memory_backed_dispatch_rate`
  - percent of dispatches whose instructions were modified by retrieved context

### Why they matter
If memory exists but nobody uses it during dispatch, the bridge is decorative.

## 4.5 Evidence and structured-result quality metrics

These answer whether the system is producing machine-usable city data.

### Required first metrics
- `structured_result_completeness_rate`
  - percent of reviewed results with all required fields present
- `attachment_expectation_satisfaction_rate`
  - percent of tasks with expected proof artifacts present
- `source_type_distribution`
  - observed vs heard vs documented vs mixed
- `confidence_below_threshold_rate`
  - percent of heard/mixed outcomes below confidence target
- `template_schema_violation_rate`
  - percent of results failing template-specific validation

### Why they matter
CaaS cannot become compounding infrastructure if the reviewed artifacts are too incomplete or ambiguous to replay.

## 4.6 Worker familiarity and match-quality metrics

These answer whether the system is learning which workers succeed where.

### Required first metrics
- `worker_familiarity_coverage`
  - percent of city tasks where assigned worker has prior office/template history
- `experienced_worker_success_lift`
  - outcome delta between familiarity-aware matching and proximity-only matching
- `redirect_handling_quality_score`
  - quality measure for how well workers capture redirect detail
- `documentation_fidelity_score`
  - operator-rated quality of evidence/result accuracy
- `repeat_worker_office_success_rate`
  - success rate for repeated worker-office pairings

### Why they matter
The marketplace edge is not just having nearby people; it is knowing who reliably handles municipal ambiguity.

## 5. Canonical event names

The observability layer should use stable event names across EM product logic, projector flows, and IRC/session coordination.

Recommended first event set:
- `city_task_created`
- `city_dispatch_brief_composed`
- `city_dispatch_brief_viewed`
- `city_worker_assigned`
- `city_submission_received`
- `city_review_started`
- `city_review_completed`
- `city_review_escalated`
- `city_reviewed_episode_written`
- `city_office_playbook_delta_written`
- `city_dispatch_context_reused`
- `city_follow_on_task_created`
- `city_redirect_observed`
- `city_rejection_observed`
- `city_resubmission_created`

These names should stay boring and durable.
The point is longitudinal visibility, not clever taxonomy.

## 6. Minimal event payloads

Every event does not need everything.
But the first observability slice should standardize a compact shared payload:

```json
{
  "event_name": "city_review_completed",
  "task_id": "[task_id]",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "[office]",
  "outcome_status": "rejected",
  "review_status": "approved_with_learning",
  "redirect_target": "Window B",
  "rejection_reasons": ["outdated_form_version"],
  "memory_write_recommended": true,
  "event_time": "2026-04-26T07:00:00Z"
}
```

### Required shared fields
- `event_name`
- `task_id`
- `workflow_template`
- `jurisdiction_name`
- `event_time`

### Strongly recommended shared fields
- `office_name`
- `outcome_status`
- `review_status`
- `redirect_target`
- `rejection_reasons[]`
- `memory_write_recommended`

## 7. First dashboards to support

The first dashboards should help operators and builders answer concrete questions quickly.

### 7.1 Pilot operations dashboard
Should answer:
- how many city tasks were reviewed today?
- which offices/templates are producing the most redirects or rejections?
- which tasks are stalled waiting on review?
- are reviewed results writing memory artifacts reliably?

### 7.2 Memory effectiveness dashboard
Should answer:
- how often are dispatch briefs present and used?
- are redirects decreasing after playbook updates?
- are repeated rejection reasons shrinking for repeated offices/templates?
- are operators actually changing instructions after retrieval?

### 7.3 Worker familiarity dashboard
Should answer:
- where do we have repeat municipal operators?
- does familiarity outperform proximity-only assignment?
- which office/template pairs are still weakly covered?

## 8. Acceptance gates for the first observability slice

The first slice should not be called done until:
- every reviewed city task emits a stable `city_review_completed` event
- every memory-safe reviewed task emits a visible `city_reviewed_episode_written` event
- every dispatch with prior memory can emit `city_dispatch_brief_composed`
- at least one dashboard/report can show redirect and rejection concentration by office/template
- the team can measure whether a reroute or resubmission reused prior context

## 9. Recommended local-first implementation path

This does not need full infra first.

### Step 1
Emit line-delimited JSON events locally from review/projector flows.

### Step 2
Generate simple daily aggregates by office/template.

### Step 3
Produce a compact report showing:
- reviewed count
- redirect count
- rejection count
- memory write count
- dispatch brief count
- repeat rejection count

### Step 4
Only after the event model feels stable, swap the sink to Acontext/observability services.

## 10. Sharp recommendation

**Do not measure CaaS primarily by task volume yet. Measure it by whether prior reviewed city work changes the next dispatch in the right direction.**

That is the real product loop.
If that loop is visible and improving, scale can come later with confidence.
If that loop is invisible, scale will just multiply confusion.

## 11. Coordination control plane metrics

Because CaaS is being designed alongside the swarm coordination control plane, observability should include a thin metric layer that connects dispatch quality to coordination quality.

### 11.1 Additional required metrics
- `coordination_session_coverage_rate`
  - percent of reviewed city tasks with a durable `coordination_session_id`
- `event_mirror_completeness_rate`
  - percent of required city events mirrored from review/IRC/control-plane sources into the local ledger or projector outputs
- `intervention_to_outcome_lift`
  - outcome delta for tasks that received operator or system intervention before review closure
- `brief_to_assignment_latency_seconds`
  - time from `city_dispatch_brief_composed` to worker assignment
- `restart_reconstruction_success_rate`
  - percent of interrupted/restarted city workflows that can be reconstructed from artifacts without transcript spelunking

### 11.2 Why they matter
A smart dispatch brief is not enough if the surrounding coordination state is fragile.
These metrics reveal whether city memory is surviving real operational conditions:
- restarts
- IRC interruptions
- escalations
- follow-on redispatch loops

## 12. Success scorecard for the first live loop

To keep daytime implementation honest, the first slice should report one composite judgment alongside raw metrics.

### 12.1 Suggested scorecard dimensions
A first-pass `city_learning_loop_scorecard` can mark each reviewed replay bundle on five axes:
- `review_trustworthy`
- `memory_written_when_safe`
- `dispatch_brief_improved`
- `coordination_trace_complete`
- `next_step_operationally_clear`

### 12.2 Judgment policy
The scorecard should remain conservative:
- improvement without proof of operational usefulness is not a pass
- memory writes from ambiguous review should count against the loop
- missing coordination trace should block strong claims of replayability

This gives builders and operators one simple question to inspect:
> did this reviewed task actually strengthen the next dispatch in a way we can replay and explain?

### 12.3 New integration cuts to report explicitly
Because the current planning push is about joining memory, Acontext, IRC/session continuity, and cross-project decision support, the first scorecard/reporting slice should also emit explicit pass/fail or enum judgments for:
- `promotion_rendering_aligned`
  - whether promotion class, guidance tone, and section placement stayed consistent across packet -> brief -> pickup brief
- `session_rebuild_ready`
  - whether compact artifacts are sufficient to reconstruct live city context without transcript dependency
- `acontext_sink_ready`
  - whether the artifact set is compact and provenance-safe enough to export without semantic reinterpretation
- `cross_project_event_reusable`
  - whether the event envelope is generic enough to be reused by adjacent AAS/control-plane surfaces

These cuts make the integration seam inspectable instead of assuming that replay correctness automatically implies operational portability.

### 12.4 Recommended per-row dimensions for later queries
Each replay-backed scorecard row should carry enough metadata to answer success questions across office, workflow, and session boundaries:
- `coordination_session_id`
- `review_packet_id`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `reuse_mode`
- `office_key`
- `workflow_template`
- `jurisdiction_name`
- `source_episode_count`

Without those dimensions, teams will be able to say that learning improved in aggregate but not which decision-support seam actually worked.
