# City as a Service — Review Decision Tables

> Last updated: 2026-04-26
> Parent docs:
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `CITY_AS_A_SERVICE_OPERATOR_PLAYBOOK.md`
> - `CITY_AS_A_SERVICE_REVIEW_AND_ROUTING_UI_BLUEPRINT.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> Status: implementation-oriented planning draft

## 1. Why this doc exists

The planning stack already says the first product seam is:
- review worker evidence
- normalize a reviewed city result
- emit memory artifacts
- improve the next dispatch

What remains too implicit is the exact review logic that converts city outcomes into:
- reviewed result fields
- review artifact values
- follow-on actions
- memory-write decisions

Without that decision layer, daytime engineering still has to guess how the Review Console should behave.

This doc defines the narrowest decision tables needed to make review behavior implementation-ready and testable.

## 2. Core principle

**Review should be rule-driven enough to be consistent, but small enough to ship before broader workflow automation.**

The first version should answer four questions deterministically:
1. how is the outcome classified?
2. what follow-on action should be suggested?
3. should office memory be updated?
4. what fields are mandatory before closure?

## 3. Shared review outputs

Every reviewed city task should resolve these fields before closure:
- `outcome_status`
- `source_type`
- `next_step_recommendation`
- `review_status`
- `closure_type`
- `result_trust_level`
- `follow_on_needed`
- `memory_write_recommended`

## 4. Outcome-to-closure decision table

| Reviewed situation | `outcome_status` | `closure_type` | Default `review_status` | Default `follow_on_needed` |
|---|---|---|---|---|
| Submission accepted with proof | `accepted` | `success_proof` | `approved` | `false` |
| Counter answer obtained and usable | `completed` | `success_proof` | `approved` | `false` |
| Rejection with clear reason | `rejected` | `rejection_diagnosis` | `approved_with_learning` | `true` |
| Redirect with clear destination | `redirected` | `redirect_clarified` | `approved_with_learning` | `true` |
| Office blocked progress but condition is clear | `blocked` | `blocked_condition` | `needs_followup` | `true` |
| Evidence too weak to trust outcome | `inconclusive` | `inconclusive` | `insufficient_evidence` | `true` |
| Conflicting signals require operator escalation | `inconclusive` | `inconclusive` | `escalated` | `true` |

## 5. Follow-on recommendation table

| Reviewed situation | Default `next_step_recommendation` |
|---|---|
| Clean success, no immediate downstream task | `none` |
| Counter answer reveals missing requirement | `ask_followup_question` |
| Packet rejected for fixable document issue | `resubmit_packet` |
| Packet or question routed to another office/window | `reroute_office` |
| Posting or audit failed due to visible compliance issue | `fix_posting` |
| Office closed, appointment required, or revisit timed later | `schedule_revisit` |
| Accepted result unlocks downstream compliance prep | `prepare_for_inspection` |
| Conflicting evidence or policy ambiguity | `human_review_required` |

## 6. Memory-write decision table

| Condition | `memory_write_recommended` | Why |
|---|---|---|
| Accepted/completed result with no reusable office learning | `false` | Closure is useful but does not change routing or policy knowledge |
| New rejection reason captured clearly | `true` | Rejection patterns should improve the next dispatch |
| Repeat rejection reason confirmed again | `true` | Repeat signal should strengthen office guidance confidence |
| Redirect target captured clearly | `true` | Routing knowledge is one of the highest-value memory outputs |
| Photo/evidence restriction observed | `true` | Future proof expectations should adjust before dispatch |
| Office closure / appointment rule observed clearly | `true` | Access friction is reusable operational knowledge |
| Weak or contradictory evidence | `false` | Raw ambiguity should not become doctrine |
| Escalated legal/policy ambiguity without clear field truth | `false` | Needs human interpretation before memory promotion |

## 7. Mandatory fields before closure by outcome

### 7.1 Accepted / completed
Must have:
- `outcome_status`
- `source_type`
- `next_step_recommendation`
- proof attachment or explicit proof explanation
- `review_status`
- `closure_type`
- `result_trust_level`

### 7.2 Rejected
Must have:
- all accepted/completed fields as applicable
- `rejection_reasons[]`
- template-specific rejection detail in `structured_result`
- follow-on recommendation

### 7.3 Redirected
Must have:
- `redirect_target`
- redirect source captured in `structured_result` or notes
- follow-on recommendation, usually `reroute_office`

### 7.4 Blocked
Must have:
- blocked condition captured in `structured_result`
- whether retry/revisit is sensible
- follow-on recommendation

### 7.5 Inconclusive
Must have:
- explicit explanation of why the result is weak
- `result_trust_level`
- `review_status` of `insufficient_evidence` or `escalated`
- no memory write recommendation unless later re-reviewed

## 8. Trust-level rules

| Signal quality | Default `result_trust_level` |
|---|---|
| Primary documentary proof or strong visual proof | `high` |
| Mixed proof with some operator interpretation | `medium` |
| Mostly hearsay, conflicting claims, or missing proof | `low` |

Recommended rule:
- low-trust outcomes may close operationally, but should not write office memory by default
- high-trust rejections and redirects should usually write memory

## 9. Review Console behavior implied by these tables

The first Review Console should be able to:
1. infer a draft row from the reviewed situation
2. highlight missing mandatory fields before closure
3. preview the follow-on action that the selected row implies
4. preview whether memory will be written and why

This means the UI does not need heavy AI to be useful.
It needs compact rule-driven review support.

## 10. Fixture coverage requirements

The fixture replay pack should explicitly cover at least one case for each of these rows:
- accepted/completed with no memory write
- rejected with memory write
- repeated rejection with stronger memory signal
- redirected with reroute recommendation
- blocked with revisit recommendation
- inconclusive with memory write suppressed

If the replay harness cannot exercise these rows, the first review logic is still underspecified.

## 11. First engineering acceptance gate

The first city-ops review implementation should not be considered done until:
- each decision-table row can be represented in fixtures
- the Review Console can derive or enforce the required fields for that row
- the projector receives stable review outputs for all rows
- memory writes are suppressed for low-trust or inconclusive cases
- follow-on recommendations are deterministic enough to test by snapshot

## 12. Promotion, tone, and placement decision tables

The core outcome tables above decide whether a task can close and whether memory should be written.
What they still need is an explicit bridge into operator-facing behavior.

The first implementation should therefore treat review output as a three-stage decision chain:
1. classify the reviewed result
2. decide the replay/packet promotion stance
3. decide operator guidance tone and placement from that stance

### 12.1 Review output to packet/promotion defaults

| Reviewed pattern | Default `summary_judgment` | Default `learning_strength` | Default `review_decision` | Default `memory_promotion_decision` |
|---|---|---|---|---|
| Clean accepted/completed result with no reusable office learning | `pass` | `weak` | `close_without_learning` | `do_not_promote` |
| First clear rejection reason with high-trust evidence | `pass` | `moderate` | `promote_rejection_learning` | `promote_cautiously` |
| Repeated rejection reason confirmed again with strong provenance | `pass` | `strong` | `promote_rejection_learning` | `promote_with_confidence` |
| First clear redirect target with strong field proof | `pass` | `moderate` | `promote_redirect_learning` | `promote_cautiously` |
| Repeated redirect target confirmed across reviewed runs | `pass` | `strong` | `promote_redirect_learning` | `promote_with_confidence` |
| Evidence restriction observed once and usable but bounded | `pass` | `moderate` | `promote_evidence_guidance` | `promote_cautiously` |
| Plausible office pattern but only one weak or mixed episode | `partial` | `weak` | `hold_pending_more_evidence` | `hold_for_more_evidence` |
| Contradictory, low-trust, or unresolved municipal ambiguity | `fail` | `weak` | `archive_without_promotion` | `do_not_promote` |

### 12.2 Promotion stance to operator guidance mode

| `memory_promotion_decision` | Guidance mode | Operator meaning |
|---|---|---|
| `promote_with_confidence` | `directive` | Safe to shape top-line dispatch doctrine |
| `promote_cautiously` | `cautious` | Safe to shape verify-first or likely-pattern guidance |
| `hold_for_more_evidence` | `inspect_only` | Visible for inspection/debug, not default dispatch doctrine |
| `do_not_promote` | `suppressed` | Do not surface in default brief guidance |

### 12.3 Guidance mode to default brief placement

| Guidance mode | Allowed default placement | Disallowed default placement |
|---|---|---|
| `directive` | `recommended_first_action`, `must_avoid_rejection_traps`, `required_evidence_plan`, `default_fallback_instruction` | hidden only in debug drawers |
| `cautious` | `watchouts`, `verify_first_patterns`, `likely_redirect_behavior`, `evidence_caveats` | top-line doctrine sections reserved for confident guidance |
| `inspect_only` | Office Memory View, expandable provenance/debug drawer, replay bundle inspection | copyable worker instruction block, top-line dispatch summary |
| `suppressed` | internal audit history only when needed | all dispatch brief sections and lightweight operator summaries |

### 12.4 Mandatory Review Console preview fields implied by these tables

Before review confirmation, the first Review Console should preview:
- `memory_promotion_decision`
- guidance mode (`directive`, `cautious`, `inspect_only`, `suppressed`)
- target brief section
- one-line rendered guidance preview
- why that tone/placement was selected
- whether the rendered guidance is allowed into the default copyable worker-instruction block
- whether the same learning should also appear in the next `morning_pickup_brief.json` as a promotion/tone/placement observation

This keeps the review gate honest about how future dispatch will sound, not only whether memory will be written.

### 12.5 Promotion-policy rendering matrix

To reduce daylight ambiguity, the first implementation should treat review output as a compact rendering matrix, not only a set of independent enums.

| `memory_promotion_decision` | Guidance mode | Default brief placement | Copyable worker instruction block | Pickup-brief expectation |
|---|---|---|---|---|
| `promote_with_confidence` | `directive` | top-line operational sections (`recommended_first_action`, `must_avoid_rejection_traps`, `required_evidence_plan`, `default_fallback_instruction`) | `allowed` | record as confirmed behavior-changing guidance if the brief actually changes likely dispatch behavior |
| `promote_cautiously` | `cautious` | secondary caution sections (`watchouts`, `verify_first_patterns`, `likely_redirect_behavior`, `evidence_caveats`) | `allowed_with_bounded_wording` | record as cautious guidance and explicitly note what is still unproven |
| `hold_for_more_evidence` | `inspect_only` | debug/provenance surfaces only | `disallowed` | record as held learning and name the next evidence needed before promotion |
| `do_not_promote` | `suppressed` | no default brief placement | `disallowed` | record only as anti-overclaim or suppression if relevant |

This matrix should be reused by:
- Review Console preview logic
- brief composer rendering rules
- replay assertions
- `morning_pickup_brief.json` generation or review

### 12.6 Fixture coverage additions

The replay fixture pack should include at least one case for each of these presentation outcomes:
- repeated rejection -> `directive`
- first clear redirect -> `cautious`
- plausible but weak office pattern -> `inspect_only`
- contradictory or unresolved field signal -> `suppressed`

If replay cannot assert these distinctions, the operator-facing part of the memory loop is still underspecified.

## 13. Sharp recommendation

**The strongest next seam is explicit review decision logic that reaches all the way into promotion, guidance tone, and placement.**

Once these tables exist, daytime engineering can build the Review Console, projector rules, replay assertions, and dispatch-brief rendering against one shared operational truth.
