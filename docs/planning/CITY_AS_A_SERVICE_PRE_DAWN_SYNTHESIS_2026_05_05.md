# City as a Service — Pre-Dawn Synthesis (2026-05-05)

> Last updated: 2026-05-05
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
> - `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_04.md`
> Status: final night-to-day handoff

## 1. Why this doc exists

The active dream priority is still Execution Market AAS / City as a Service only.
The stale cron body pointed at AutoJob, Frontier Academy, and KK v2 again, but `DREAM-PRIORITIES.md` overrode all of that.
So the right pre-dawn move was not widening scope.
It was tightening the daytime handoff around the highest-leverage seam already in flight.

Tonight's planning stack gained one important property:

> the first daytime implementation is now split, ordered, and closeable as one reviewable proof ladder.

That matters because the remaining daylight risk is no longer missing artifacts.
It is landing the right artifacts in the wrong shape:
- one oversized PR that hides semantic drift
- several small PRs that are locally clean but not obviously one proof program
- a closure package that passes through scoreboards honestly but softens the truth during handoff

## 2. Strongest synthesis from this session

The cleanest new insight is:

> **daytime now needs packaging discipline as much as semantic discipline.**

Earlier docs already made the shared-decision seam clear.
What tonight clarified is the exact daylight progression needed to make that seam reviewable without overclaim:
1. projection truth
2. runtime convergence
3. reuse convergence
4. closure-proof packaging

That turns the first shared-decision implementation from "one big careful refactor" into a ladder with explicit advancement rules.

## 3. What changed in the planning spine

Two new handoff-strengthening docs now anchor the current daytime move:
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`

Together they close the last daylight ambiguity between:
- how to split the work
- what each split is allowed to claim
- what checkpoint must pass before the next rung
- when to stop tightening instead of broadening

The closure-proof seam is now also explicitly governed by:
- `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`

So the planning stack now has a full chain from implementation packaging to final handoff fidelity.

## 4. The one daytime mission

If daytime only gets one meaningful slice done, it should be this:

1. land PR A so one normalized decision projection helper becomes the only owner of trust semantics
2. land PR B only after runtime continuity surfaces prove conservative parity from that owner
3. land PR C only after reuse behavior proves the next dispatch changed for the right reason from that same owner
4. land PR D only after scoreboards, telemetry, and pickup packaging can preserve the exact same closure truth

This is narrower than "build the CaaS flywheel," but much more honest.
It gives daytime a disciplined way to report progress as:
- foundation landed
- runtime parity landed
- reuse parity landed
- closure-proof landed

Instead of prematurely calling the whole flywheel complete.

## 5. The new daylight anti-drift rule

The key anti-drift lesson to carry into day is:

> **no PR should force reviewers to answer more than one semantic question at once.**

The four allowed daytime questions are now:
1. is the shared decision truth shape correct?
2. do runtime consumers read it directly?
3. do reuse consumers read it directly?
4. do scoreboards and closure artifacts prove the truth survived?

If any PR blurs two of those together, review risk rises sharply.
If a PR claims a later answer before an earlier checkpoint is proven, the ladder should stop.

## 6. The exact closure bar that matters now

The closure checklist sharpened the most important operational truth:

A proof block is not done when scoreboards exist.
It is done when the exact claim limits survive all the way through:
1. scoreboards
2. telemetry gate row
3. morning pickup brief

The dangerous fields remain the same ones from last night, but they now have a stronger execution context because the ladder defines when they become authoritative:
- `combined_verdict`
- `behavior_change_class`
- `trust_preservation_result`
- `dangerous_axes_failed[]`
- `supported_behavior_change_reason[]`
- `do_not_claim_yet[]`
- `next_smallest_proof[]`

If those drift anywhere between PR D output and pickup continuity, the block should end as `fix_drift_before_expand`, not "good enough."

## 7. What daytime should do first

The sharpest starting point remains one replay-backed redirect or rejection case.
But the working rule is now stricter:
- pick one stable case
- keep it stable across PR A through PR D
- use that same case to prove each rung before widening surface area

That gives reviewers a fixed semantic anchor instead of changing both implementation and evidence basis at the same time.

## 8. What not to do next

Still avoid:
- AutoJob work
- Frontier Academy work
- KK v2 work
- broader template expansion
- Acontext plumbing before local closure proof is honest
- dashboard polish that hides unresolved parity or closure drift

The current bottleneck is not ideation.
It is disciplined first-proof landing.

## 9. Strategic recommendation for daytime

Treat the next engineering window as:

> **one first-PR closure ladder for the shared-decision seam.**

That means:
- split by verification boundary, not directory
- merge only the claim earned by the current rung
- keep one replay-backed case stable across the ladder
- let PR D end only when telemetry and pickup mirrors preserve scoreboard truth exactly

If daytime follows that rule, the first CaaS proof block should become much easier to ship cleanly and much harder to overstate.

## 10. Bottom line

The night's final synthesis is simple:

> the next daytime win is not more planning breadth.
> it is landing the first shared-decision seam as a four-rung proof ladder whose closure truth survives handoff unchanged.

That is the cleanest path from a strong CaaS planning stack to an actually usable daytime implementation program.
