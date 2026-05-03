# City as a Service — Decision Drift Triage Playbook

> Last updated: 2026-05-03
> Parent docs:
> - `CITY_AS_A_SERVICE_DECISION_SEAM_ACCEPTANCE_HARNESS.md`
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_SHARED_RENDERING_TRUTH_CONTRACT.md`
> - `CITY_AS_A_SERVICE_SHARED_DECISION_PARITY_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_REUSE_BEHAVIOR_PROOF_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_DECISION_PROJECTION_IMPLEMENTATION_SLICE.md`
> Status: next-daytime debugging companion

## 1. Why this doc exists

The planning stack now has a good answer for what should happen:
- one reviewed city decision becomes one normalized projection
- all runtime and reuse consumers preserve the same trust posture
- parity and reuse scoreboards prove semantic sameness and behavior-change legitimacy

What is still missing is the daylight operator/developer response when those guarantees fail.
Without a triage playbook, the first implementation slice can still land in an awkward state:
- drift fixtures fail, but nobody knows which seam to inspect first
- parity scoreboard says semantics drifted, but the team debates whether it is “just rendering”
- reuse scoreboard says behavior changed unsafely, but the root cause is buried between projection, consumer wiring, and ledger mirroring

This doc closes that gap.

> the first real decision seam needs not only acceptance proofs, but a fast, shared method for classifying and fixing drift when proofs fail.

## 2. Core principle

**Decision drift is a product bug, not a polish bug.**

If any consumer silently strengthens, weakens, drops, or relocates judged truth, the learning flywheel is lying about what it knows.
The triage process should therefore answer two questions quickly:
1. what exact invariant drifted?
2. did the drift originate in projection, consumer interpretation, downgrade handling, or ledger/observability mirroring?

## 3. The four drift origins

Every first-pass failure should be classified into one of these buckets:

### 3.1 Projection drift
The normalized decision projection itself produced the wrong shared semantics.

Examples:
- `memory_promotion_decision=promote_cautiously` mapped to `promotion_class=directive`
- `not_safe_to_claim[]` got flattened during projection
- readiness flags were inferred optimistically instead of copied conservatively

### 3.2 Consumer drift
Projection is correct, but a runtime or reuse consumer re-derived or mutated semantics locally.

Examples:
- brief composer turned `verify_first` into top-line imperative copy
- pickup writer omitted anti-overclaim warnings
- reuse builder treated non-copyable guidance as copyable worker text

### 3.3 Downgrade drift
A consumer could not honor the full semantics, but failed to emit an explicit downgrade note and mirror event.

Examples:
- export omitted placement semantics without a downgrade note
- rebuild compressed cautious guidance into resume text that reads directive
- observability row dropped readiness flags silently

### 3.4 Mirror drift
User-facing outputs are correct, but ledger or observability artifacts do not preserve the same governing truth.

Examples:
- ledger row has a different `guidance_tone` than the brief that was emitted
- reuse scoreboard and observability row disagree on behavior-change class
- parity scoreboard passes some consumers but provenance links break in exported artifacts

## 4. Triage order

When a fixture, parity scoreboard, or reuse scoreboard fails, inspect in this order only:

1. `review_packet.json`
2. normalized decision projection output
3. `city_compact_decision_object.json`
4. affected consumer output(s)
5. ledger mirror row(s)
6. observability row(s)
7. parity / reuse scoreboards

Why this order:
- it isolates whether the bug was born before or after projection
- it prevents premature UI debates when the projection is already wrong
- it keeps scoreboards as verdict surfaces, not as the first debugging surface

## 5. Invariant families to classify first

Every failure should be tagged with one primary invariant family before deeper debugging starts.

### 5.1 Promotion drift
The consumer rendered a stronger or weaker promotion class than the projection allowed.

### 5.2 Tone drift
The wording implies a different confidence mode than the governing tone.

### 5.3 Placement drift
Guidance moved into a stronger or weaker section family than allowed.

### 5.4 Copyability drift
Worker-facing text became copyable (or non-copyable) against the governing rule.

### 5.5 Anti-overclaim drift
`not_safe_to_claim[]`, caution notes, or next-proof boundaries disappeared or weakened.

### 5.6 Readiness drift
Continuity/export/rebuild/operator-surface readiness claims changed silently.

### 5.7 Provenance drift
A surface or mirror artifact can no longer point cleanly to the governing packet / compact decision / source episode.

### 5.8 Behavior-class drift
Reuse classification says one thing happened while dispatch, redispatch, or observability implies another.

## 6. Severity model

The first implementation slice should not treat all drift equally.

### P0 — stop-ship drift
Any of:
- cautious or inspect-only learning rendered as directive
- non-copyable guidance leaked into copyable worker instructions
- anti-overclaim protections lost on active operator surfaces
- rebuild says ready when the projection says not ready
- reuse scoreboard marks `smarter_for_right_reason=true` without support

### P1 — same-day fix drift
Any of:
- pickup/export/rebuild wording preserves class but loses a required warning
- ledger/observability mirror fields drift from the rendered consumer
- provenance refs are incomplete but recoverable

### P2 — cleanup drift
Any of:
- formatting mismatch with semantics preserved
- redundant downgrade notes
- scoreboards harder to inspect than necessary, but still semantically correct

## 7. Fast diagnosis table

| Symptom | Likely origin | First file/seam to inspect |
|---|---|---|
| parity scoreboard says promotion mismatch across consumers | consumer drift or projection drift | projection helper, then affected consumer |
| worker instruction became copyable unexpectedly | consumer drift | reuse / worker-instruction builder |
| pickup brief sounds stronger than dispatch brief | consumer drift | pickup writer and shared rendering helper |
| observability says continuity ready when rebuild fails | mirror drift or downgrade drift | rebuild helper, observability writer, ledger row |
| reuse scoreboard says unsafe overclaim | consumer drift or behavior-class drift | reuse output builder, reuse observability row |
| exported memory unit lacks tone/placement semantics | downgrade drift or mirror drift | memory export writer |
| provenance lost between brief and ledger | mirror drift | ledger writer / provenance refs mapping |

## 8. Required debugging artifacts per failure

A drift bug is not fully diagnosed until the issue report can show:
- the governing `review_packet_id`
- the governing `compact_decision_id`
- the normalized projection field(s) expected
- the consumer or mirror field(s) observed
- the invariant family violated
- whether the problem is projection, consumer, downgrade, or mirror drift
- whether the scoreboards failed correctly or missed the issue

This should keep daytime bugs concrete instead of argumentative.

## 9. Suggested issue template

```text
Decision drift report
- fixture/case:
- review_packet_id:
- compact_decision_id:
- failing invariant family:
- severity: P0 / P1 / P2
- expected shared field(s):
- observed field(s):
- drift origin hypothesis: projection / consumer / downgrade / mirror
- affected outputs:
- scoreboard verdicts:
- loud-fail gap? yes/no
- smallest fix seam:
```

## 10. Relationship to scoreboards

### 10.1 Parity scoreboard role
The parity scoreboard should answer:
- did all consumers preserve the same judged truth?
- where did semantic sameness break?

### 10.2 Reuse behavior scoreboard role
The reuse scoreboard should answer:
- did the next dispatch change for the right reason?
- did that change preserve trust posture?

### 10.3 Playbook role
This playbook answers:
- once a scoreboard fails, what should the team inspect first and how should the bug be classified?

That separation matters.
Scoreboards are verdicts.
This playbook is response discipline.

## 11. Recommended daytime implementation hook

The first code slice should make triage cheap by emitting one compact debug bundle whenever a drift fixture fails:
- normalized projection snapshot
- affected consumer output snapshot
- relevant ledger rows
- relevant observability rows
- parity scoreboard artifact
- reuse behavior scoreboard artifact when applicable

That bundle does not need to be product-facing.
It only needs to make the first failure explainable in minutes instead of hours.

## 12. What this prevents

This playbook is meant to prevent three predictable daylight mistakes:
1. calling semantic drift “just wording”
2. fixing consumer copy while leaving projection bugs alive
3. chasing scoreboard symptoms without checking the shared decision seam first

## 13. Sharp recommendation

**Treat the first drift failure as a design test, not just a bug.**

If the team can classify and localize drift quickly, the shared decision seam is probably real.
If drift turns into a long argument about interpretation, the seam is still too loose and should not expand yet.
