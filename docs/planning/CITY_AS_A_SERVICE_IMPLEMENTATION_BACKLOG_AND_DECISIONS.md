# City as a Service — Implementation Backlog and Decision Ledger

> Last updated: 2026-05-01
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_IMPLEMENTATION_SLICE_V1.md`
> - `CITY_AS_A_SERVICE_DAYTIME_BUILD_SPEC.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `CITY_AS_A_SERVICE_LOCAL_PROJECTOR_BOOTSTRAP.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> Status: build-readiness synthesis

## 1. Why this doc exists

The CaaS planning stack is now broad, but the implementation risk is no longer lack of ideas.
The real risk is losing daytime momentum to ambiguity:
- too many equally-plausible starting points
- hidden open questions spread across many docs
- no single backlog that converts planning into an ordered build
- no explicit record of what has already been decided versus what is still open

This document compresses the current planning set into one engineering-facing artifact.
Its job is to make the next build window obvious.

## 2. Current build thesis

The first live CaaS slice should prove one narrow product claim:

> a reviewed municipal task can generate reusable office memory that measurably improves the next dispatch.

Everything in this backlog is in service of that claim.
Anything that does not strengthen the loop below should wait:

1. task posted with city template context
2. worker submits municipal evidence
3. operator reviews into canonical structured result
4. projector emits episode + office-memory delta
5. later dispatch retrieves a brief
6. operator or agent changes instructions because of that brief

## 3. Decisions already locked

These are not open debates anymore unless new evidence appears.

### 3.1 Product wedge
- Start with **City as a Service** as an Execution Market AAS vertical.
- Focus on verified municipal-world execution, not generic local errands.
- Optimize for repeatable city/compliance workflows where evidence quality matters.

### 3.2 Pilot shape
- Start with **one metro area**.
- Recommended default remains **Miami-area municipal/compliance workflows**.
- Initial customer wedge remains SMB permit/compliance-adjacent operations.

### 3.3 Template scope for first implementation
- In scope first: `counter_question`, `packet_submission`
- Contract-compatible but not first-class in the first slice: `posting_proof`
- Defer broad support for `site_audit` and `queue_wait_handoff` until the review/memory loop is stable.

### 3.4 Memory-write policy
- No durable memory writes from raw worker uploads.
- Memory writes happen **after review**.
- `reviewed_result` + `review_artifact` are the promotion gate.

### 3.5 Infrastructure sequencing
- Do **not** block the product loop on Acontext or Docker.
- Build the first loop with local artifacts and deterministic replay.
- Treat the later Acontext swap as a transport change, not a semantic change.

### 3.6 Operator surface priority
- Start with **Review Console** and **Dispatch Brief Panel**.
- Office Memory View can be admin/debug-first.
- Do not start with a giant city-ops dashboard.

### 3.7 Observability principle
- Measure decision-quality improvement, not generic marketplace throughput.
- Routing quality, rejection learning, and memory reuse are the core health signals.

## 4. Build sequence recommendation

This is the clearest current implementation order.

### Phase 1 — contracts and fixture pack
Deliverables:
- lock `reviewed_result`, `review_artifact`, `reviewed_episode`, `office_playbook_delta`, `dispatch_brief`, and `review_packet`
- create 8-12 reviewed fixtures covering redirects, repeated rejections, evidence restrictions, clean acceptance, and inconclusive cases
- add schema validation for shared and template-specific fields

Why first:
Without fixture-backed contracts, UI and projector work will drift.

### Phase 2 — review normalizer
Deliverables:
- transform review-form/admin input into valid `reviewed_result` + `review_artifact`
- enforce conditional requirements
- reject incomplete closures

Why second:
The normalizer is the promotion gate between worker uploads and durable municipal memory.

### Phase 3 — deterministic local projector
Deliverables:
- emit `reviewed_episode`
- detect meaningful learning signals
- emit `office_playbook_delta` where appropriate
- merge office playbook artifacts
- compose deterministic dispatch briefs
- emit one compact `review_packet` after manifest + scorecard judgment so downstream tooling can consume the replay outcome without re-deriving it from the full bundle
- apply explicit promotion policy from `review_packet` so future brief composition can distinguish confident, cautious, held, and blocked learning

Why third:
This is the first point where the system can become smarter on the second run.

### Phase 4 — operator/admin debug surfaces
Deliverables:
- Review Console v0
- Dispatch Brief Panel v0
- Office Memory Debug View v0
- memory-write preview before confirm

Why fourth:
The underlying loop should exist before UI polish tries to hide product ambiguity.

### Phase 5 — observability
Deliverables:
- stable events for review/projector/retrieval moments
- first reports/dashboard queries for redirect concentration, rejection concentration, review completion, and memory reuse

Why fifth:
Once the loop exists, the team needs proof that it is working and where it is failing.

### Phase 6 — transport swap to Acontext
Deliverables:
- replace local-file sink with Acontext-backed sink using the same contracts
- preserve deterministic replay semantics for tests

Why last:
By then the team is swapping plumbing, not redesigning product meaning.

## 5. The minimum viable artifact chain

The first slice is not real unless every reviewed task can produce this chain:

### Always required
- one `reviewed_result`
- one `review_artifact`
- one `reviewed_episode`
- one `review_packet`

### Conditionally required
- one `office_playbook_delta` when meaningful learning exists
- updated office playbook when office context exists
- one `dispatch_brief` for later reuse

### Hard rule
If the operator cannot trace a later dispatch warning back to a reviewed episode, the memory loop is not trustworthy yet.

## 6. Highest-value open decisions

Only a small set of questions still deserves daytime attention now.

### 6.1 Code placement
Open question:
Where should the first city-ops seam live?

Recommended default:
```text
mcp_server/city_ops/
  contracts.py
  review_normalizer.py
  projector.py
  brief_composer.py
  observability.py
```

Decision standard:
Prefer the smallest placement that keeps contracts, replay, and observability together.
Avoid burying the first slice inside generic abstractions.

### 6.2 Review surface host
Open question:
Should the first review surface be dashboard-native, admin-only, or server-rendered?

Recommendation:
Choose the cheapest surface that still enforces the contracts.
For v0, admin/debug-first is acceptable if it produces valid reviewed artifacts and previewable memory writes.

### 6.3 Office key derivation
Open question:
How should office keys be derived to avoid collisions and memory fragmentation?

Recommendation:
Use a deterministic office key derived from normalized jurisdiction + office name + optional office type.
Do not overfit to addresses before field reality proves they are stable enough.

### 6.4 Context reuse semantics
Open question:
What exact operator action should count as `city_dispatch_context_reused`?

Recommendation:
Count it when prior memory is not just displayed but materially used, for example:
- operator copies fallback guidance into instructions
- operator changes office routing after seeing brief
- operator changes evidence guidance or risk handling because of prior memory

### 6.5 Trust thresholds
Open question:
What minimum trust should allow memory promotion?

Recommendation:
Start conservatively:
- `observed` and `documented` with complete evidence: normally eligible
- `heard` or `mixed`: eligible only with explicit confidence and operator approval
- weak, contradictory, or inconclusive hearsay should generate reviewed episodes but not strong doctrine changes

## 7. Backlog by object

### 7.1 `reviewed_result`
Must be production-grade first.

Backlog:
- finalize required shared fields
- finalize conditional validation by outcome type
- finalize template-specific `structured_result` variants
- add examples for accepted, rejected, redirected, blocked, inconclusive
- add test fixtures for low-confidence hearsay and evidence-missing cases

### 7.2 `review_artifact`
Backlog:
- finalize `review_status`, `closure_type`, and `result_trust_level` enums
- clarify relationship between `follow_on_needed` and `follow_on_recommendation`
- define when `memory_write_recommended=false` should still allow episode writing

### 7.3 `reviewed_episode`
Backlog:
- standardize compact narrative fields
- ensure every episode can state what changed in dispatch behavior
- separate observed facts from operator inference

### 7.4 `office_playbook_delta`
Backlog:
- lock delta types for redirect learning, rejection learning, evidence restriction, scope correction, and queue pattern
- define merge behavior for counts vs narrative notes
- define confidence update rules conservatively

### 7.5 `dispatch_brief`
Backlog:
- finalize compact operator-facing shape
- define exact fallback-instruction generation rules
- expose source episode ids for provenance
- keep output readable in under a minute

### 7.6 `review_packet`
Backlog:
- require explicit `summary_judgment`, `learning_strength`, `review_decision`, and `memory_promotion_decision`
- require direct refs to `bundle_manifest`, `event_summary`, `brief_improvement_scorecard`, `improved_dispatch_brief`, `office_playbook_delta`, and `reviewed_episode`
- keep rationale short, behavior-focused, and safe for future Acontext ingestion
- treat the packet as the compact decision object, not a duplicate of the full replay archive
- make packet output actionable by downstream retrieval through a stable promotion-policy interpretation
- require packet output to drive one explicit operator-facing guidance-tone choice so brief language does not drift across implementations
- require packet-derived fields to feed one shared runtime projection helper so replay, continuity, export, rebuild, observability, and reuse do not re-derive semantics independently
- require packet output to drive one explicit guidance-placement choice so tentative learning cannot silently occupy top-line summary slots
- require packet output to constrain where guidance may appear in the improved brief, not only how it is phrased
- align packet defaults with the shared review decision tables so repeated rejection/redirect learning upgrades from `cautious` to `directive` via explicit replay evidence instead of ad hoc brief logic
- require packet output to feed one compact `morning_pickup_brief.json` continuity object so the next engineering block inherits the same promotion/tone/placement truth without restating it manually
- require packet output to carry or deterministically derive one replay-readiness judgment for Review Console preview parity (`pass`, `partial`, `fail`)
- require packet-adjacent rendering outputs or deterministic derivation rules for:
  - default brief section family
  - copyable worker-instruction eligibility
  - pickup-brief observation class (`confirmed`, `cautious`, `held`, `suppressed`)
- require one parity scoreboard artifact so downstream review can grade semantic sameness across brief, pickup, export, rebuild, observability, reuse, and ledger mirrors without manually diffing every surface
- require one reuse behavior scoreboard artifact so downstream review can grade whether the next dispatch changed for the right reason, not just whether artifacts lined up
- require one drift triage playbook so the first parity/reuse failures can be classified as projection, consumer, downgrade, or mirror bugs instead of getting dismissed as surface polish
- require one proof-block scoreboard protocol so parity and reuse scoreboards always collapse into a single expand / tighten / fix-drift verdict instead of ad hoc review debate
- require one proof-block telemetry gate row so combined verdict, portability state, and anti-overclaim carry-forward become queryable across pickup, rebuild, observability, and export review instead of living only in prose
- require one telemetry-gate review protocol so the compact closure row itself is checked for verdict fidelity, conservative readiness, and anti-overclaim carry-forward before later sessions trust it
- treat missing rendering alignment as a real backlog gap, not a cosmetic follow-up, because replay proof is incomplete if the same promotion decision can still render differently across surfaces

## 8. Backlog by product surface

### 8.1 Review Console v0
Must support:
- evidence rail
- normalized outcome fields
- review decision fields
- follow-on recommendation
- memory-write preview

Must not require:
- long narrative authoring to close a task
- manual re-entry of obvious task context

### 8.2 Dispatch Brief Panel v0
Must support:
- office summary
- top rejection reasons
- top redirect targets
- evidence warnings
- fallback instruction recommendation
- freshness/provenance markers

Must not become:
- a long-form knowledge browser
- an excuse for operators to ignore the actual review artifacts

### 8.3 Office Memory View v0
Must support:
- current office playbook
- recent episodes
- rejection/redirect pattern summaries
- provenance from episode → delta → brief

## 9. Backlog by observability

### 9.1 Events to implement first
- `city_task_created`
- `city_submission_received`
- `city_review_started`
- `city_review_completed`
- `city_reviewed_episode_written`
- `city_office_playbook_delta_written`
- `city_dispatch_brief_composed`
- `city_dispatch_context_reused`
- `city_follow_on_task_created`

### 9.2 Queries/reports to make possible immediately
- review completion rate by template
- redirect rate by office/template
- rejection reason concentration
- repeat rejection same-reason rate
- brief presence and reuse rate
- routing accuracy improvement on later attempts
- pickup-brief readiness rate, meaning how often replay blocks can honestly mark operator surfaces ready versus still partial

## 10. Acceptance scenario that should decide readiness

The first slice should be considered real only if this scenario passes cleanly:

1. a `counter_question` run at a named office is reviewed
2. the reviewed output writes a valid `reviewed_result`
3. the projector emits an episode and office-memory delta
4. the replay emits a valid `review_packet` with an explicit memory-promotion stance
5. a later `packet_submission` for that office opens with a generated brief
6. the brief warns about a known redirect, evidence restriction, or rejection pattern
7. the operator changes dispatch instructions because of that brief
8. the operator can inspect exactly which episode caused the warning and which review packet justified promotion
9. the surfaced guidance strength matches the promotion policy outcome (`confident`, `cautious`, held, or blocked) instead of flattening all learned memory into the same operator tone
10. the operator-facing wording style also matches the policy outcome, for example directive language for confident promotion, verify-first language for cautious promotion, inspect-only surfacing for held learning, and no default brief injection for blocked learning
11. the operator-facing section placement also matches the policy outcome, so cautious or held learning cannot silently appear in the same top-line summary zones reserved for confident doctrine

If that scenario fails, the system is documenting work, not learning from it.

## 11. What should explicitly wait

The following are valuable later, but should not dilute the first build window:
- broad multi-city expansion
- generalized workflow engine complexity
- executive reporting surfaces
- semantic retrieval or embeddings-first experiments
- worker marketplace redesign for city verticals
- deep automation from raw uploads without reviewed promotion

## 12. Morning handoff checklist for daytime continuity

Before daytime expands scope, it should answer this checklist from actual replay artifacts rather than intuition:
- which fixtures produced complete replay bundles
- which acceptance gates passed versus failed
- whether `review_packet` promotion stance changed dispatch tone in a behaviorally meaningful way
- whether any improvement remains cosmetic rather than operational
- whether guidance tone matched the promotion-policy class instead of collapsing all surfaced learning into the same warning register
- whether guidance placement matched the promotion-policy class instead of letting tentative rules inherit directive placement by default
- what the next smallest proof is if the seam is still partial

Recommended coordination artifacts:
- `morning_pickup_brief.json` or equivalent batch summary derived from actual replay runs
- `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md` as the canonical reading and judgment order for replay-proof PRs
- `CITY_AS_A_SERVICE_DAYTIME_REPLAY_PROOF_RUNBOOK.md` as the canonical execution order for daytime proof blocks so the team emits, reviews, and classifies one replay-backed seam the same way every time
- `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md` as the canonical final judgment rule once both scoreboards exist
- `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md` as the canonical closure rule for turning proof-block verdicts into compact, queryable continuity/observability/export state
- `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md` as the canonical fidelity check for confirming that compact closure state still matches the scoreboards before handoff

This checklist exists to keep continuation honest.
The city-ops seam should be advanced by the smallest missing proof, not by whichever adjacent surface looks most exciting.

## 13. Rendering alignment checklist for the next build block

Before daytime treats the replay seam as implementation-ready, it should be able to answer `yes` to all of these from artifacts rather than intuition:
- does the selected promotion stance determine guidance tone deterministically?
- does it also determine section placement deterministically?
- does it determine whether guidance may enter the copyable worker-instruction block?
- can the same decision be summarized consistently in `morning_pickup_brief.json` without restating bundle logic by hand?
- can repeated reviewed evidence strengthen guidance from cautious to directive only through explicit replay-backed promotion changes?

If any answer is `no`, the next build block should tighten rendering alignment before broadening UI scope.

## 14. Review-discipline addition

The planning stack now has one more locked seam: replay-proof review discipline.

Daytime should treat `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md` as the default protocol for deciding whether a replay block is:
- ready for broader UI wiring
- still only partial proof
- overclaiming based on cosmetic or weak learning

The practical reading order is now:
1. `bundle_manifest.json`
2. `event_summary.json`
3. `review_packet.json`
4. `city_compact_decision_object.json`
5. `morning_pickup_brief.json`
6. `brief_improvement_scorecard.json`
7. `improved_dispatch_brief.json`
8. deeper artifacts only as needed

And once reuse is in scope, the next proof should also be inspectable from:
1. `city_dispatch_context_reused`
2. `city_redispatch_context_reused`
3. `city_worker_instruction_block_built`
4. `city_reuse_observability_row`
so reviewers can verify that the same judged truth survives the next actual dispatch decision instead of only the replay archive.

If those first seven objects do not already make the before/after learning story obvious, the next build block should tighten replay proof instead of broadening surfaces.

## 15. Sharp recommendation

If daytime wants the clearest possible next move, it should treat the CaaS backlog as:

**contracts first, replay second, review gate third, projector fourth, promotion-policy-aware retrieval fifth, observability sixth, infra swap last.**

And inside that sequence, the next narrow proof should be:
**one shared runtime truth from review packet -> compact decision object -> brief tone -> brief placement -> pickup-brief continuity -> append-only coordination ledger -> reuse-safe next dispatch guidance.**

That preserves the real moat:
**reviewed municipal reality becoming better future execution.**

## 17. New locked implementation slice

The planning stack now has one more explicit daytime recommendation:
- `CITY_AS_A_SERVICE_DECISION_PROJECTION_IMPLEMENTATION_SLICE.md`

That doc should be treated as the narrowest code-ready translation of the current planning seam.
Its purpose is to prevent the next engineering block from splitting into several “aligned” local implementations that still re-derive semantics independently.

Practical recommendation:
1. build the shared decision projection helper first
2. wire core runtime consumers through it
3. wire reuse consumers through it
4. end the slice with parity + reuse-behavior scoreboard artifacts
5. run the resulting proof block through `CITY_AS_A_SERVICE_DAYTIME_REPLAY_PROOF_RUNBOOK.md` instead of ad hoc execution
6. end the resulting proof block with `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md` instead of informal pass/partial debate
7. emit the resulting proof-block telemetry package via `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md` so verdict and portability state survive into later sessions and sinks
8. review that compact closure package with `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md` so later sessions do not inherit diluted verdicts or claim limits
9. only then broaden adjacent surfaces

## 16. Next daytime implementation slice

The most leverage now is not more planning breadth.
It is one thin end-to-end implementation seam that proves memory, IRC/session continuity, Acontext export readiness, and observability are all reading the same truth.

### 15.1 Recommended build ticket breakdown
1. derive one `city_compact_decision_object.json` from `review_packet` plus aligned replay-proof context
2. create append-only city control-plane JSONL ledger with stable event envelope and mirrored decision fields
3. emit decision-aligned rendering fields on reuse events:
   - `promotion_class`
   - `guidance_tone`
   - `guidance_placement`
   - `copyable_worker_instruction`
   - `replay_readiness_judgment`
4. derive `dispatch_brief`, `morning_pickup_brief.json`, and export/observability rows from the same compact decision object
5. add one restart-rebuild helper that reconstructs active session state from ledger + compact decision object + brief
6. write one scorecard row per reviewed replay bundle with integration judgments
7. only then add the Acontext sink using the same compact exported memory unit

### 15.2 Hard acceptance gate for that slice
Do not call this seam ready unless one replay-backed case can prove all of the following together:
- operator-facing brief wording matches promotion stance
- operator-facing section placement matches promotion stance
- pickup brief preserves the same judgment without manual restatement
- append-only ledger mirrors the same decision fields across brief/pickup/export/rebuild events
- session rebuild works from compact artifacts without transcript dependency
- observability can query the same case by `coordination_session_id`, `review_packet_id`, and `compact_decision_id`
- exported Acontext memory unit does not need extra interpretation to drive retrieval

### 15.3 Explicit deprioritization for the next block
Until that seam is real, avoid spending the next block on:
- broader dashboard polish
- extra city templates
- richer semantic search ideas
- generic cross-vertical abstraction cleanup
- reuse surfaces that bypass the compact decision object and invent their own trust logic

Those can wait.
The highest-value proof is still the compact decision-support seam holding under real replay conditions.
