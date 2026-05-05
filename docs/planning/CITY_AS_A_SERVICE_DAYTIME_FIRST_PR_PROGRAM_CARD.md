# City as a Service — Daytime First PR Program Card

> Last updated: 2026-05-05 04:00 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_REVIEW_CARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
> Status: daytime implementation program compression card

## 1. Why this doc exists

The planning stack already has the right ingredients for the first shared-decision build:
- a safe PR split
- a rung-by-rung execution ladder
- a strict review card
- a closure-proof checklist

What is still easy to lose in a real daytime window is the **program shape across those artifacts**.
A team can still:
- read each doc separately
- agree with each one locally
- then start the day without one compact program that says what to build first, what to prove before broadening, and what final artifact chain makes the block handoff-safe

This doc closes that gap.

> treat the first shared-decision implementation as one four-rung daytime program with one opening move, one active proof case, and one final closure chain.

## 2. The single program question

For the first daytime City-as-a-Service implementation push:

> if the team had only one engineering window, would the next move, the active proof case, the allowed claim, and the honest stop condition all be obvious from one page?

If not, the planning stack is still correct but operationally too fragmented.

## 3. The one active proof case

Keep one replay-backed case as the active program anchor across PR A through PR D.
Do not rotate cases between rungs unless the original case is invalid.

Recommended default:
- one redirect or rejection case
- one case that can move from `shown_only` toward a real routing or instruction change
- one case that stresses trust preservation, not only artifact emission

Why this matters:
- reviewers can compare the same judged truth across all rungs
- drift becomes easier to localize
- closure artifacts stay interpretable without re-learning a new example every PR

## 4. The four-rung daytime program

### Rung 1 — projection truth
Primary artifact owner:
- shared decision projection helper

Primary question:
- does one projection seam now own trust semantics?

Allowed claim:
- semantic ownership is unified

Must remain forbidden:
- runtime parity proven
- reuse parity proven
- closure-proof complete

Authoritative outputs:
- projection helper
- compact decision object

Stop if:
- tone, placement, copyability, readiness, or anti-overclaim state still depend on consumer opinion

### Rung 2 — runtime convergence
Primary artifact owners:
- brief
- pickup
- export
- rebuild
- observability
- ledger mirror

Primary question:
- do continuity surfaces now mirror the same owner conservatively?

Allowed claim:
- runtime continuity surfaces preserve one judged truth

Must remain forbidden:
- smarter next-dispatch behavior proven
- closure-safe handoff proven

Authoritative outputs:
- fixture-backed runtime parity artifacts
- explicit downgrade notes where needed

Stop if:
- parity requires prose excuses
- any continuity surface is semantically stronger than the projection

### Rung 3 — reuse convergence
Primary artifact owners:
- dispatch reuse
- redispatch reuse
- worker-instruction block
- reuse observability row

Primary question:
- did the next dispatch change for the right reviewed reason without trust drift?

Allowed claim:
- reuse behavior now mirrors the shared semantic owner

Must remain forbidden:
- closure-proof complete
- pickup/telemetry handoff trustworthy by default

Authoritative outputs:
- reuse behavior artifacts
- trust-preservation classification

Stop if:
- behavior change is only aesthetic
- copyability boundaries leak
- trust preservation is arguable instead of explicit

### Rung 4 — closure packaging
Primary artifact owners:
- parity scoreboard
- reuse behavior scoreboard
- combined verdict
- telemetry gate row
- pickup brief
- closure checklist result

Primary question:
- did the exact verdict survive compact closure packaging unchanged?

Allowed claim:
- one closure-proof block is handoff-safe

Authoritative outputs:
- combined verdict
- reviewed telemetry row
- reviewed pickup brief
- closure checklist result

Stop if:
- pickup becomes more optimistic than telemetry
- telemetry becomes more optimistic than scoreboards
- dangerous axes or claim limits disappear in compact packaging

## 5. The canonical opening move for daytime

If the team starts cold, do this first:
1. choose the one active replay-backed proof case
2. declare PR A as the only allowed build scope
3. list the exact projection-owned trust fields before touching consumers
4. refuse all adjacent surface work until the projection checkpoint is honest

This avoids the common daylight failure mode of “starting implementation everywhere” before semantic ownership is actually unified.

## 6. The canonical closing move for daytime

A daytime block should end in this order only:
1. combined verdict selected from the scoreboard protocol
2. telemetry gate row emitted from that verdict
3. telemetry row reviewed for fidelity
4. pickup brief emitted from the same closure truth
5. pickup brief reviewed for fidelity
6. closure-proof checklist marked pass / partial / fail
7. next smallest honest move recorded

If the block ends before step 7, the next session inherits ambiguity instead of continuity.

## 7. The exact final artifact chain

The first shared-decision program should not claim closure-proof until reviewers can inspect this chain coherently:
1. `bundle_manifest.json`
2. `event_summary.json`
3. `review_packet.json`
4. `city_compact_decision_object.json`
5. `city_shared_decision_parity_scoreboard.json`
6. `city_reuse_behavior_scoreboard.json`
7. proof-block telemetry gate row
8. `morning_pickup_brief.json`
9. closure-proof checklist result

That chain is now the smallest honest proof that:
- the same judged truth existed
- the same judged truth changed the next dispatch for the right reason
- the same judged truth survived handoff packaging

## 8. What daytime should explicitly defer until this program passes once

Defer:
- new template expansion
- richer dashboard surfaces
- generalized Acontext transport work
- cross-vertical abstraction cleanup
- broader observability polish beyond the proof seam

Reason:
those moves broaden the surface area before the first closure-proof program is proven stable.

## 9. How to report progress honestly

Use only these progress labels across the first program:
- `projection_truth_landed`
- `runtime_parity_landed`
- `reuse_parity_landed`
- `closure_proof_landed`
- `tighten_same_seam`
- `fix_drift_before_expand`

Avoid:
- “flywheel done” before rung 4 passes
- “basically complete” when claim limits are still moving
- “UI polish remaining” when trust packaging is still drifting

## 10. Sharp recommendation

**Use this card as the daytime opener before writing code and as the daylight closer before claiming handoff-safe proof.**

The first City-as-a-Service shared-decision implementation is most likely to land cleanly when the team treats it as:
- one active case
- one four-rung program
- one closure chain
- one honest next move

That is the shortest path from careful planning to the first durable operational proof block.
