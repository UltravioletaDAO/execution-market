# City as a Service — Daytime First PR Execution Ladder

> Last updated: 2026-05-05 02:08 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_REVIEW_CARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_PICKUP_BRIEF_CONTRACT.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
> Status: daytime execution-order bridge

## 1. Why this doc exists

The planning stack now says three useful but slightly separate things:
- how to split the first shared-decision implementation into reviewable PRs
- how to review each PR for semantic ownership and drift
- how to close a proof block so telemetry and pickup continuity stay honest

What is still easy to lose in daylight is the **execution order that connects those three layers**.
A team can still:
- choose the right PR split
- review each PR locally
- yet package the whole ladder loosely, without a crisp rule for when to run proof closure versus when to keep tightening the same seam

This doc closes that gap.

> treat PR A through PR D as one execution ladder with one closure discipline, not as four independent implementation wins.

## 2. The single ladder question

For the first daytime shared-decision seam:

> at each rung, do we know exactly what may advance, what must stay frozen, and what closure artifact must exist before the next rung is honest?

If the answer is no, the team is still vulnerable to broad diffs, weak verdicts, or pickup drift.

## 3. Canonical ladder

The first daytime seam should advance in this order only:
1. **PR A — projection truth**
2. **PR B — runtime convergence**
3. **PR C — reuse convergence**
4. **PR D — scoreboards + drift fixtures + closure packaging**

See `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md` for the detailed contents of each PR.
This doc defines the execution rule between them.

## 4. Rung-by-rung execution rules

### 4.1 PR A — projection truth

#### Goal
Create the one normalized decision projection owner and compact decision object shape.

#### Allowed claim after merge
- shared trust semantics now have one owner

#### Forbidden claim after merge
- runtime parity exists
- reuse parity exists
- flywheel proof exists
- closure-proof is ready

#### Required checkpoint before PR B
Reviewers can inspect one replay-backed case and confirm:
- deterministic projection emission
- no downstream consumer is silently inventing stronger trust semantics in helper branches that will later be hard to unwind

If that checkpoint is weak, do not advance to PR B.
Tighten the projection seam first.

### 4.2 PR B — runtime convergence

#### Goal
Force continuity/runtime consumers to read the shared projection directly.

#### Allowed claim after merge
- continuity surfaces now mirror the same semantic owner conservatively

#### Forbidden claim after merge
- next dispatch behavior is already proven smarter
- closure packaging is complete
- telemetry handoff is ready without reuse convergence

#### Required checkpoint before PR C
One fixture-backed case should prove parity across:
- dispatch brief
- morning pickup brief
- export writer
- rebuild helper
- observability row
- coordination ledger mirror

Any downgrade must be explicit.
Any consumer-specific strengthening is a stop sign.

### 4.3 PR C — reuse convergence

#### Goal
Force dispatch reuse and redispatch behavior to consume the same projection seam.

#### Allowed claim after merge
- next-dispatch behavior now mirrors the same semantic owner without local trust invention

#### Forbidden claim after merge
- closure-proof is complete
- pickup continuity is handoff-safe
- telemetry packaging is trustworthy by default

#### Required checkpoint before PR D
One replay-backed case should prove:
- reuse behavior exceeds `shown_only` when appropriate
- copyability limits are enforced by projection state
- trust preservation remains explicit in routing/instruction/evidence-guidance changes

If the case is only inspectable as “looks better,” do not advance.
The seam still needs tightening.

### 4.4 PR D — scoreboards + drift fixtures + closure packaging

#### Goal
Turn the converged seam into one honest proof block with loud failures and durable handoff packaging.

#### Allowed claim after merge
- one closure-proof block is honest, queryable, and handoff-safe

#### Required closure chain
PR D is not done unless all of these happen in order:
1. parity scoreboard emitted
2. reuse behavior scoreboard emitted
3. combined verdict applied
4. telemetry gate row emitted
5. telemetry gate row reviewed for fidelity
6. pickup brief emitted from the same closure truth
7. pickup brief checked against the same closure truth
8. closure-proof checklist passes honestly

If any step above is missing, the correct result is not “done later.”
It is `tighten_same_seam` or `fix_drift_before_expand`.

## 5. Which artifact becomes authoritative at each rung

### After PR A
Authoritative artifact:
- shared projection helper / compact decision object

### After PR B
Authoritative artifacts:
- runtime parity outputs
- explicit downgrade notes where needed

### After PR C
Authoritative artifacts:
- reuse behavior outputs
- trust-preservation classification on next-dispatch behavior

### After PR D
Authoritative closure package:
1. combined scoreboard verdict
2. telemetry gate row
3. pickup brief
4. closure-proof checklist result

The ladder should not skip authority.
Each later rung inherits and preserves the earlier one.

## 6. Honest stop conditions

Daytime should stop the ladder and tighten the same seam if any of these happen:
- projection helper still leaves tone/placement/copyability/readiness to consumer opinion
- runtime parity requires prose explanation to look aligned
- reuse behavior changes but trust preservation is ambiguous
- scoreboards pass but telemetry row drops dangerous axes or claim limits
- telemetry row is honest but pickup brief becomes more optimistic
- pickup brief is compact but no longer actionable for the next session

These are not minor polish issues.
They mean the ladder is not ready to advance.

## 7. Final closure verdict discipline

The whole first PR ladder should end in one of three outcomes only:
- `ship_same_seam`
- `tighten_same_seam`
- `fix_drift_before_expand`

That verdict should be chosen from the scoreboards, carried into telemetry, mirrored in pickup, and confirmed by the closure checklist.
No rung should substitute vibes for that chain.

## 8. Recommended daytime operating rhythm

For the first daytime shared-decision push:
1. build one rung
2. review only the question for that rung
3. prove the required checkpoint for that rung
4. advance only if the checkpoint is honest
5. when PR D lands, run the full closure chain before claiming the seam is handoff-safe

That rhythm prevents two common failures:
- broad implementation drift hidden inside one “nearly there” review
- correct scoreboards paired with weak continuity packaging

## 9. Relationship to the rest of the planning stack

Use this doc as the bridge between:
- split strategy (`CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`)
- review bar (`CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_REVIEW_CARD.md`)
- proof closure (`CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md`)
- telemetry fidelity review (`CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md`)
- pickup continuity contract (`CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_PICKUP_BRIEF_CONTRACT.md`)
- final daylight closure gate (`CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`)

If daytime uses only one of those docs in isolation, the seam will probably still drift.
Use them as one ladder.

## 10. Sharp recommendation

**The safest first daytime move now is not more planning breadth.**
It is to treat the first shared-decision implementation as one four-rung execution ladder where each rung has:
- one allowed claim
- one forbidden claim set
- one required checkpoint
- one stronger authoritative artifact
- one honest stop condition

That makes the first City-as-a-Service closure-proof seam much harder to overclaim and much easier to land cleanly.