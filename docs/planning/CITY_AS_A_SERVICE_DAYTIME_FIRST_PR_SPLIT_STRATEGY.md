# City as a Service — Daytime First PR Split Strategy

> Last updated: 2026-05-05 01:20 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DECISION_PROJECTION_IMPLEMENTATION_SLICE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_REVIEW_CARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> Status: daytime implementation packaging guide

## 1. Why this doc exists

The planning stack is already clear about **what** the first daytime proof must accomplish.
The remaining implementation risk is more tactical:
- trying to land the whole shared-decision seam in one oversized PR
- mixing schema, consumer wiring, proof fixtures, and closure packaging in a review that becomes too hard to reason about
- approving partial semantic alignment because the diff is broad enough to hide drift

This doc closes that packaging gap.

> the first daytime proof should be built as one tightly sequenced PR set, but reviewed as one closure-proof program.

That means:
- multiple small PRs are allowed
- semantic ownership must still converge on one shared decision seam
- no PR should claim the flywheel alone before the closure-proof chain is actually complete

## 2. The single packaging principle

Split by **verification boundary**, not by file count.

A good first PR sequence should let reviewers answer one focused question at a time:
1. is the shared decision truth shape correct?
2. are runtime consumers reading it directly?
3. are reuse consumers reading it directly?
4. do scoreboards and closure artifacts prove that the truth survived?

If a PR forces reviewers to answer all four at once, it is probably too large.
If a PR hides one answer behind another, it is probably split the wrong way.

## 3. Recommended first PR sequence

## PR A — shared projection foundation

### Goal
Create the one normalized decision projection helper and the compact decision object shape.

### Should include
- projection schema / typed helper
- deterministic mapping from `review_packet` to normalized decision fields
- explicit downgrade-note shape
- `city_compact_decision_object.json` emission path
- minimal provenance and identity fields

### Should NOT include yet
- broad consumer wiring
- reuse logic
- scoreboards
- pickup-brief closure packaging

### Review question
> does one helper now own trust semantics, and can the compact decision object carry them without consumer-specific inference?

### Acceptance gate
- one replay-backed case can emit the projection and compact decision object deterministically
- no consumer-facing trust semantics are still being invented in ad hoc helper branches

## PR B — core runtime consumer convergence

### Goal
Force first-order runtime consumers to read the shared projection directly.

### Should include
- Dispatch Brief composer wiring
- Morning Pickup Brief writer wiring
- memory export writer wiring
- rebuild helper wiring
- runtime observability row wiring
- coordination ledger mirror wiring
- explicit downgrade visibility where a consumer cannot fully preserve semantics

### Should NOT include yet
- reuse/redispatch behavior changes
- final scoreboards
- closure-proof verdict protocol

### Review question
> do all runtime continuity surfaces preserve the same judged truth without recomputing trust posture locally?

### Acceptance gate
- one fixture-backed case proves parity across brief, pickup, export, rebuild, observability, and ledger mirror
- any downgrade is explicit, inspectable, and not silently stronger than the projection

## PR C — reuse behavior convergence

### Goal
Force dispatch reuse and redispatch behavior to consume the same projection seam.

### Should include
- initial dispatch-context reuse
- redispatch fallback reuse
- worker-instruction rendering gate
- reuse observability row writer
- first behavior-change classification output

### Should NOT include yet
- combined closure verdict packaging
- pickup-brief closure signoff

### Review question
> does one reviewed city decision now change the next dispatch for the right reason without exceeding the judged trust posture?

### Acceptance gate
- one replay-backed case shows more than `shown_only`
- trust preservation remains explicit during routing, instruction, evidence-guidance, or redispatch change
- copyability boundaries are enforced by the projection rather than local consumer opinion

## PR D — scoreboards, drift fixtures, and closure packaging

### Goal
Turn the aligned seam into one honest proof block with loud failures and handoff-safe packaging.

### Should include
- parity scoreboard writer
- reuse behavior scoreboard writer
- combined verdict application
- proof-block telemetry gate row
- closure-proof pickup brief validation
- deliberate drift fixtures for dangerous axes
- any compact daylight note / debug bundle needed to localize failures

### Review question
> does the proof block end in one honest verdict, and does that verdict survive telemetry and pickup packaging unchanged?

### Acceptance gate
- dangerous drift fixtures fail loudly
- telemetry row preserves scoreboard truth exactly
- pickup brief preserves telemetry truth exactly
- `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md` can pass honestly

## 4. Why this split is the safest one

This split follows the actual semantic dependency chain:
1. projection truth exists
2. runtime consumers stop drifting
3. reuse consumers stop drifting
4. proof and closure packaging become reviewable

That order matters.
If scoreboards or closure packaging land before all consumers share one truth seam, the artifacts may look honest while hiding structural drift.
If reuse lands before runtime parity, the next dispatch may change for the right reason in one place while continuity surfaces still tell a softer or stronger story elsewhere.

## 5. What should remain constant across the whole PR set

Even if the work lands across multiple PRs, these rules should not change:
- one normalized decision projection helper owns trust semantics
- no consumer independently computes promotion class, tone, placement, copyability, readiness posture, or anti-overclaim state
- downgrade handling is explicit, never silent
- the first replay-backed proof case stays stable enough to compare across PRs
- the final claim is only made after closure packaging passes

## 6. What NOT to do

Do not split the work like this:

### Bad split A — by arbitrary file family
- one PR for schemas
- one PR for “UI stuff”
- one PR for “logging”
- one PR for “cleanup”

Why this fails:
- it maps to directories, not proof boundaries
- it encourages local correctness without end-to-end semantic proof

### Bad split B — scoreboards before consumer convergence
Why this fails:
- reviewers get formal verdict artifacts before the system has one actual source of semantic truth
- false confidence becomes likely

### Bad split C — pickup brief treated as a soft continuity surface
Why this fails:
- the pickup brief is part of closure proof, not just a convenience summary
- softening there breaks handoff integrity even when scoreboards are correct

## 7. Suggested reviewer discipline across the PR set

### After PR A
Reviewer should be able to say:
> trust semantics now have one owner.

### After PR B
Reviewer should be able to say:
> continuity surfaces now mirror the same owner.

### After PR C
Reviewer should be able to say:
> next-dispatch behavior now mirrors the same owner.

### After PR D
Reviewer should be able to say:
> the proof verdict and closure package now mirror the same owner.

If any of those statements feels too generous, that PR is not done.

## 8. Daytime recommendation

**Treat PR A through PR D as one closure-proof ladder, not four unrelated wins.**

The first PR set is successful only when the last rung is true:
- one reviewed city decision changed the next dispatch for the right reason
- every first-order consumer preserved the same judged truth
- the final verdict survived compact telemetry and pickup packaging without trust inflation

Until then, daytime should report progress as:
- foundation landed
- runtime parity landed
- reuse parity landed
- closure-proof landed

Not as “flywheel complete.”

## 9. Bottom line

The right first daytime split is not about smaller diffs for their own sake.
It is about making semantic ownership, consumer convergence, behavior change, and closure fidelity reviewable in the right order.

That is the safest path from a strong planning stack to the first honest City-as-a-Service proof block.
