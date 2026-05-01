# City as a Service — Replay Proof Review Protocol

> Last updated: 2026-05-01
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_REPLAY_BUNDLE_SPEC.md`
> - `CITY_AS_A_SERVICE_REPLAY_REVIEW_PACKET_CONTRACT.md`
> - `CITY_AS_A_SERVICE_MORNING_PICKUP_BRIEF_CONTRACT.md`
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `CITY_AS_A_SERVICE_BRIEF_IMPROVEMENT_SCORECARD_SPEC.md`
> Status: pre-dawn handoff synthesis

## 1. Why this doc exists

The planning stack already defines:
- what artifacts a replay bundle must emit
- how the manifest and scorecard should behave
- how `review_packet` governs promotion and guidance tone
- how `morning_pickup_brief.json` should preserve continuity

What is still too easy to mis-execute in daylight is **review discipline**.
A team can have the right files and still waste time asking:
- which file should be read first in a PR?
- what counts as proof versus only progress?
- when is a bundle ready for UI wiring?
- when should the next engineering block tighten replay instead of expanding scope?

This doc closes that gap.

Its goal is simple:

> make every replay-proof review follow one compact, conservative, repeatable reading and judgment order.

## 2. Core principle

**Review the proof seam in the same order the product claims causality.**

Do not review city replay work by skimming random artifacts.
Do not start from the prettiest UI surface.
Do not infer readiness from code shape alone.

The review order should mirror the product claim:
1. the proof contract says what happened
2. the event story says in what order it happened
3. the packet says what it means operationally
4. the pickup brief says what the next builder should do next
5. the scorecard says whether the next dispatch got better
6. the improved brief shows what the operator would actually see
7. deeper artifacts justify the change

If that order does not hold, the seam is still too vague.

## 3. Canonical reading order

Every replay-proof review should follow this order:

1. `bundle_manifest.json`
2. `event_summary.json`
3. `review_packet.json`
4. `morning_pickup_brief.json` (or batch-equivalent continuity object)
5. `brief_improvement_scorecard.json`
6. `improved_dispatch_brief.json`
7. `baseline_dispatch_brief.json`
8. `office_playbook_delta.json`
9. `office_playbook_after.json`
10. `reviewed_episode.json`
11. `reviewed_result.json`
12. `review_artifact.json`

Why this order:
- manifest first = pass/partial/fail contract
- event summary second = ordered proof story
- packet third = compact reviewed judgment and promotion stance
- pickup brief fourth = continuity and anti-overclaim guardrail
- scorecard fifth = behavior-change proof
- brief pair sixth/seventh = operator-visible before/after
- deeper artifacts afterward = provenance and justification

## 4. What each review step must answer

### 4.1 Manifest review
The manifest review must answer:
- are all required artifacts present?
- did validation pass?
- is determinism asserted?
- did the proof clear its acceptance checks?
- is `summary_judgment` conservative?

Immediate fail signals:
- missing required artifact with no explicit placeholder reason
- `summary_judgment=pass` while `brief_improvement_visible=false`
- manifest lists files but does not express clear acceptance checks

### 4.2 Event summary review
The event summary review must answer:
- is the proof story ordered compactly?
- does the sequence match the intended city learning loop?
- can a reviewer see where promotion and brief composition happened?

Immediate fail signals:
- transcript-like noise instead of compact event sequence
- unstable or confusing event order
- no visible event seam connecting review completion to improved brief composition

### 4.3 Review packet review
The packet review must answer:
- what did the replay prove?
- how strong is the learning?
- what is the `memory_promotion_decision`?
- what is the main operational improvement?
- what is the main remaining concern?

Immediate fail signals:
- packet tone stronger than the manifest/scorecard supports
- packet judgment unclear enough that retrieval/UI would have to reinterpret it
- packet implies promotion while the scorecard shows only cosmetic change

### 4.4 Morning pickup brief review
The pickup brief review must answer:
- what gates truly passed, failed, or remain partial?
- what is the next smallest proof?
- what should the team **not** claim yet?
- are tone/placement observations aligned with packet promotion stance?

Immediate fail signals:
- no explicit anti-overclaim language
- vague next steps like “continue improving”
- continuity summary contradicts packet or manifest truth

### 4.5 Scorecard review
The scorecard review must answer:
- did the improved brief get operationally better instead of only longer?
- which dimensions improved?
- did compactness stay acceptable?
- is provenance clear for the important learned claims?

Immediate fail signals:
- `improved=true` without visible dimension-level support
- no increase in risk specificity for rejection/redirect fixtures
- compactness degrades badly while the run still claims success

### 4.6 Dispatch-brief review
The brief review must answer:
- what will the next operator or worker do differently now?
- does tone match promotion stance?
- does placement match promotion stance?
- is held or suppressed learning kept out of default doctrine?

Immediate fail signals:
- confident and cautious learning sound the same
- held learning appears in copyable worker instructions
- improved brief is longer but no clearer on routing, fallback, or proof plan

### 4.7 Deeper artifact review
The deeper artifact review must answer:
- which reviewed episode justified the change?
- what exactly changed in office memory?
- is the playbook delta meaningful rather than decorative?
- does reviewed truth remain separate from raw ambiguity?

Immediate fail signals:
- delta restates existing guidance without change
- episode provenance is too weak to justify surfaced doctrine
- reviewed result and review artifact do not support the packet-level claim

## 5. Summary judgment protocol

Use a three-level proof judgment:
- `pass`
- `partial`
- `fail`

### 5.1 `pass`
Use only when:
- required artifacts are present
- acceptance checks are true
- event order is clear
- packet judgment is promotion-safe and legible
- improved brief shows real operational improvement
- scorecard supports that improvement explicitly
- pickup brief remains conservative and actionable

### 5.2 `partial`
Use when:
- artifact chain is mostly valid
- the proof story is inspectable
- but one critical bar is not yet cleared

Typical `partial` cases:
- scorecard improvement exists but remains weak
- learning is inspectable but should still be held or cautious
- manifest and packet are sound but the improved brief does not yet change likely behavior enough

### 5.3 `fail`
Use when:
- contracts break
- event sequence is unclear
- packet overclaims
- improvement is cosmetic only
- provenance is not traceable
- continuity/handoff object is not trustworthy

## 6. Learning-strength review protocol

The first review should classify learning as:
- `weak`
- `moderate`
- `strong`

### `weak`
Use when the replay is valid but the learned memory is narrow, tentative, or mostly wording-level.

### `moderate`
Use when the replay changes likely worker/operator behavior for a bounded office pattern.

### `strong`
Use when repeated reviewed evidence creates reusable office doctrine that clearly improves future dispatch behavior.

Rule:
**Do not let a clean artifact set inflate weak learning into strong learning.**

## 7. UI-wiring readiness rule

A replay-proof seam is ready for broader operator-surface wiring only when all of these are true:
- manifest judgment is honest and reproducible
- packet promotion stance is explicit
- scorecard shows behaviorally meaningful improvement
- improved brief tone matches promotion class
- improved brief placement matches promotion class
- held and suppressed learning stay out of default worker doctrine
- pickup brief can state the next step without reopening the whole bundle

If any of those are false, the next engineering block should tighten replay proof before expanding UI or infra.

## 8. PR review checklist

Before approving a replay-proof PR, reviewers should be able to answer yes to all of these:
- can I understand the proof outcome from `bundle_manifest.json` first?
- does `event_summary.json` tell one compact ordered story?
- does `review_packet.json` make promotion stance obvious?
- does `morning_pickup_brief.json` state the next smallest proof and anti-overclaim warning clearly?
- does `brief_improvement_scorecard.json` prove operational improvement instead of verbosity?
- does the improved brief change likely routing, fallback, or evidence behavior?
- can I trace the surfaced guidance back to `reviewed_episode` and `office_playbook_delta`?
- would I trust this seam to drive the next dispatch without reading the full codepath?

If any answer is no, the PR may still contain useful progress, but the replay proof is not complete.

## 9. Anti-overclaim rules

Do not claim the city-ops learning seam is proven if:
- only validators exist
- only artifacts exist
- the brief changed but not behaviorally
- provenance is vague
- cautious learning renders like directive doctrine
- the pickup brief cannot name what is still unproven

Do claim progress narrowly when appropriate, for example:
- `contracts and replay bundle shape are valid, but behavior-change proof remains partial`
- `redirect learning is cautiously reusable; rejection prevention is not yet directive-safe`
- `packet and manifest align, but scorecard still shows wording-level improvement only`

## 10. Strong recommendation

**Treat replay-proof review as a product test, not a file-existence check.**

The right question is not “did the system emit the expected files?”
The right question is:

> can a reviewer prove, in minutes, that one reviewed municipal outcome made the next dispatch smarter in an honest, traceable, promotion-safe way?

If yes, the seam is compounding.
If not, keep tightening replay before expanding surface area.
