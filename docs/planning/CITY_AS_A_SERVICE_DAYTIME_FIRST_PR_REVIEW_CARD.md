# City as a Service — Daytime First PR Review Card

> Last updated: 2026-05-05 23:15 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DECISION_PROJECTION_IMPLEMENTATION_SLICE.md`
> - `CITY_AS_A_SERVICE_DECISION_SEAM_ACCEPTANCE_HARNESS.md`
> - `CITY_AS_A_SERVICE_SHARED_DECISION_PARITY_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_DECISION_DRIFT_TRIAGE_PLAYBOOK.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PR_A_PROJECTION_TRUTH_HANDOFF.md`
> Status: ladder-wide review companion; use PR A handoff for the first rung

## 1. Why this doc exists

The planning stack is now sharp enough that the next daytime risk is not choosing the wrong concept.
It is landing the right implementation slice but reviewing it loosely.

The first decision-projection program now lands as PR A through PR D, not one oversized PR.
Across that ladder it will touch:
- one new shared helper
- several downstream consumers
- fixtures
- scoreboard writers
- failure-path downgrade logic

That is exactly the kind of change where teams accidentally approve "mostly aligned" work that still hides trust drift.
This doc is therefore the **ladder-wide** review bar for the whole first proof program.
For the first rung specifically, use `CITY_AS_A_SERVICE_DAYTIME_PR_A_PROJECTION_TRUTH_HANDOFF.md`.

> the first daytime proof ladder should be reviewed as one decision-flywheel program, not as a generic multi-file refactor.

## 2. The single review question

Before approving the whole first daytime PR ladder, reviewers should be able to answer:

> did PR A through PR D force every in-scope consumer to read one shared decision projection, and does one frozen replay-backed case prove that the next dispatch got smarter without trust drift?

For PR A alone, the narrower question is:

> did one helper become the owner of projection truth, and can it emit a deterministic compact decision object for the frozen proof anchor without claiming runtime, reuse, or closure proof?

If the relevant rung question is not clearly answered, that rung is not done.

## 3. Required ladder contents

The first acceptable daytime proof ladder should include all of the following by the time PR D closes:

1. one normalized decision projection helper
2. one compact decision object emitted from that helper
3. core runtime consumers wired to the helper
4. reuse consumers wired to the helper
5. parity scoreboard writer
6. reuse behavior scoreboard writer
7. at least one passing replay-backed proof case
8. deliberate drift fixtures for dangerous trust failures
9. explicit downgrade-note shape for consumers that cannot preserve full semantics directly
10. proof-anchor freeze note preserved across all rungs

Missing any of these by PR D means the ladder is still a seam fragment, not the proof harness.
For PR A alone, only items 1, 2, 9, and 10 should be in scope.

## 4. Mandatory review order

Review the full ladder in this order only:

1. projection schema/helper
2. compact decision object emission
3. core runtime consumer wiring
4. reuse consumer wiring
5. parity scoreboard output
6. reuse behavior scoreboard output
7. downgrade handling
8. deliberate drift fixtures
9. combined scoreboard verdict application
10. proof-block telemetry gate emission
11. telemetry-gate review protocol application
12. closure-proof pickup brief contract application
13. debug/triage bundle shape if a drift fixture fails

If reviewers jump straight into UI/wording diffs, they will miss the real seam.
They should also reject “looks basically done” language if the proof block cannot end in one explicit expand / tighten / fix-drift verdict.
They should also reject any PR that reaches a verdict but does not emit the matching compact telemetry gate row for later pickup and observability use.
They should also reject any PR that emits the row but never verifies that the row preserved the same verdict, claim limits, and conservative readiness posture.

## 5. What reviewers should verify in the projection helper

The helper should clearly own these fields:
- `compact_decision_id`
- `coordination_session_id`
- `review_packet_id`
- `summary_judgment`
- `memory_promotion_decision`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- readiness flags
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`
- provenance refs

Reviewers should reject the PR if any consumer still independently computes:
- promotion class
- tone
- placement
- copyability
- readiness posture
- anti-overclaim state

## 6. What reviewers should verify in consumer wiring

### Core runtime consumers
These should read the shared projection directly:
- Dispatch Brief composer
- Morning Pickup Brief writer
- memory export writer
- rebuild helper
- runtime observability writer
- coordination ledger mirror writer

### Reuse consumers
These should also read the same projection directly:
- dispatch-context reuse
- redispatch fallback reuse
- worker-instruction builder
- reuse observability writer

Review standard:
- consumer logic may format
- consumer logic may explicitly downgrade
- consumer logic may not reinterpret trust semantics

## 7. The minimum acceptable proof case

One replay-backed redirect or rejection case should prove all of this together:
- parity scoreboard says `semantic_parity=pass`
- reuse behavior scoreboard is beyond `shown_only`
- trust preservation passes
- rebuild parity passes
- observability parity passes
- the next dispatch changed for a reason that is explicitly supported by the reviewed city judgment

If the proof case only shows memory display, that is not enough.

## 8. Dangerous failure modes reviewers should look for

Reject the relevant rung immediately if any of these are present:
- cautious or inspect-only learning rendered as directive
- non-copyable guidance leaked into copyable worker text
- anti-overclaim warnings missing from pickup, rebuild, or export paths
- rebuild claiming readiness stronger than the projection allows
- observability rows implying stronger trust than the emitted consumer artifacts
- scoreboard pass states produced from missing fields or silent downgrades

These are not polish issues.
They are product-trust failures.

## 9. Minimum drift-fixture bar

The first PR should include deliberate fixtures for at least:
- promotion drift
- tone drift
- placement drift
- copyability drift
- anti-overclaim drift
- readiness drift
- pickup-brief closure drift
- provenance loss

Reviewers should verify that each one fails loudly and localizes cleanly enough to use the drift triage playbook.

## 10. What a reviewer should be able to say after approval

A strong approval should be able to say, in plain English:

> one reviewed city decision now flows through one shared projection seam, every first-order consumer reads it directly, one replay-backed case proves smarter next-dispatch behavior, the dangerous trust drifts fail loudly, the proof block ends in one honest combined verdict about what should happen next, that verdict is carried forward in one compact telemetry gate row, the telemetry row itself was reviewed for verdict fidelity before handoff, and the pickup brief mirrors the same closure truth instead of retelling it more optimistically.

If a reviewer cannot honestly say that, the PR should stay open.

## 11. What not to waive in the name of speed

Do not waive:
- scoreboard completeness on dangerous axes
- drift fixtures for trust failures
- explicit downgrade visibility
- rebuild parity proof
- observability parity proof

Those are the proof.
Without them, the PR only looks aligned.

## 12. Sharp recommendation

**Use this card as the approval gate for the first daytime decision-projection ladder.**
Use `CITY_AS_A_SERVICE_DAYTIME_PR_A_PROJECTION_TRUTH_HANDOFF.md` as the approval gate for PR A specifically.

The planning stack is already good.
Now the main risk is approving a partially unified seam and calling it the flywheel.