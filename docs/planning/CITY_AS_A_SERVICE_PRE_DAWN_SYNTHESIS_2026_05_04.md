# City as a Service — Pre-Dawn Synthesis (2026-05-04)

> Last updated: 2026-05-04
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_TARGET_AND_DECISION_FLYWHEEL.md`
> - `CITY_AS_A_SERVICE_DECISION_SEAM_ACCEPTANCE_HARNESS.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_REVIEW_CARD.md`
> Status: final night-to-day handoff

## 1. Why this doc exists

The planning stack is now tight enough that the main daylight risk is no longer missing design detail.
It is losing the **closure discipline** of the first proof block.

Daytime now has:
- the execution order
- the acceptance harness
- the parity scoreboard
- the reuse-behavior scoreboard
- the combined verdict protocol
- the telemetry-gate fidelity check

What still matters most is making sure those pieces land as **one compact operating loop** instead of one more pile of careful docs.

> the next daytime window should produce one proof block whose verdict can survive handoff without reopening the full bundle.

## 2. Strongest synthesis from tonight

The biggest shift from tonight is this:

> **proof integrity is now a closure-packaging problem, not just a semantic-parity problem.**

Last night already established that daytime must prove one shared decision seam across replay, runtime carriage, rebuild, reuse, and observability.
Tonight sharpened the last remaining daylight failure mode:
- even with correct scoreboards
- even with an honest combined verdict
- the handoff can still drift if the compact closure artifact softens the truth

That means the first real City-as-a-Service flywheel is not complete when the scoreboards pass.
It is complete when the scoreboards, pickup brief, and telemetry closure row all preserve the **same exact claim limits**.

## 3. The one daytime mission

If daytime only accomplishes one meaningful thing, it should be this:

1. implement one normalized decision projection helper
2. wire all first-order consumers through it
3. run one replay-backed proof case through the full harness
4. end the block with one combined verdict
5. emit one compact telemetry closure row
6. verify that the closure row says exactly what the scoreboards said

That is the narrowest honest proof that the learning seam is durable across shifts, not just correct during one review session.

## 4. The critical closure truth that must never drift

The following fields now matter twice:
- once in the scoreboards
- once again in the compact closure package

They should survive unchanged across both:
- `combined_verdict`
- `behavior_change_class`
- `trust_preservation_result`
- `dangerous_axes_failed[]`
- `supported_behavior_change_reason[]`
- `do_not_claim_yet[]`
- `next_smallest_proof[]`

If any of those are softened, omitted, or rephrased into stronger certainty during pickup or observability packaging, the seam is still unsafe.

## 5. The smallest convincing daytime proof

The minimum convincing pass is still one replay-backed redirect or rejection case, but now it should prove **three layers at once**:

### Layer A — semantic sameness
- parity scoreboard passes the dangerous axes
- no consumer re-derives trust posture on its own

### Layer B — justified behavior change
- reuse result is stronger than `shown_only`
- the next dispatch changes for a reviewed operational reason

### Layer C — closure fidelity
- pickup brief carries the same verdict and claim limits
- telemetry row carries the same verdict and claim limits
- later sessions can trust the closure package without reopening the archive

Until Layer C is proven, the seam is still review-correct but handoff-weak.

## 6. Recommended daytime implementation order

### First
Build the normalized decision projection helper and make it the only owner of trust semantics.

### Second
Route these runtime consumers through it:
- Dispatch Brief composer
- Morning Pickup Brief writer
- memory export writer
- rebuild helper
- observability row writer
- coordination ledger writer

### Third
Route these reuse consumers through it:
- initial dispatch-context reuse
- redispatch fallback reuse
- worker-instruction builder
- reuse observability writer

### Fourth
Emit the proof artifacts in one pass:
- parity scoreboard
- reuse behavior scoreboard
- combined verdict
- telemetry closure row

### Fifth
Fail loudly on at least these drift families:
- promotion drift
- tone drift
- placement drift
- copyability drift
- anti-overclaim drift
- readiness drift
- telemetry packaging drift

## 7. Daytime review standard should now be brutally simple

A reviewer should be able to say:

> one reviewed city decision passed through one shared projection seam, changed the next dispatch for the right reason, ended in one honest combined verdict, and that verdict survived compact handoff packaging without trust inflation.

If they cannot say that plainly, the seam is not done.

## 8. What not to do before this passes once

Do not spend the next window on:
- broader template coverage
- richer dashboard surfaces
- generalized Acontext integration
- wider observability polish
- multi-city expansion
- any cleanup that does not strengthen proof-block closure fidelity

The bottleneck is still proof compression.
Now it is specifically **closure-truth compression**.

## 9. Strategic recommendation for daytime

**Treat the next implementation slice as a closure-proof harness, not just a decision-proof harness.**

That framing keeps the bar honest:
- one shared truth seam
- one justified behavior change
- one explicit combined verdict
- one compact closure package
- one fidelity review proving the package did not lie

If that works once, City as a Service stops being a promising planning stack and starts acting like a real cross-session operational learning loop.

## 10. Bottom line

The night’s work now compresses to one daytime mission:

> prove that one reviewed city decision can change the next dispatch for the right reason, and that the exact truth of that proof survives compact handoff packaging without semantic drift.

That is the narrowest proof that the first CaaS learning flywheel is operationally real.
