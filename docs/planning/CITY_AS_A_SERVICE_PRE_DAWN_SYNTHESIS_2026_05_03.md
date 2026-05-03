# City as a Service — Pre-Dawn Synthesis (2026-05-03)

> Last updated: 2026-05-03
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_TARGET_AND_DECISION_FLYWHEEL.md`
> - `CITY_AS_A_SERVICE_DECISION_SEAM_ACCEPTANCE_HARNESS.md`
> - `CITY_AS_A_SERVICE_SHARED_DECISION_PARITY_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_REUSE_AND_REDISPATCH_ALIGNMENT_SLICE.md`
> Status: final night-to-day handoff

## 1. Why this doc exists

The night work is no longer missing planning detail.
It now has a tighter problem:
- several good artifacts already describe the right seams
- daytime could still implement them in fragments
- the real daylight risk is losing the single proof target while touching multiple files

This doc compresses the current state into one daytime action map.

> daytime should build one shared decision seam that survives replay, runtime carriage, reuse, rebuild, and observability while changing the next dispatch for the right reason.

## 2. The strongest synthesis from tonight

The key shift from tonight is that **proof completeness is now scoreboard-based, not artifact-count-based**.

Earlier seams already established:
- replay bundle correctness
- compact decision continuity
- reuse and redispatch alignment
- acceptance harness structure

Tonight's addition makes the build bar sharper:
- one parity scoreboard must prove that all downstream consumers preserved the same judged truth
- one behavior-change result must prove the next dispatch became smarter for an operational reason

That means daytime should stop asking "did we emit the files?" and start asking:

> did every consumer preserve the same trust posture, and did reuse produce a justified behavior change?

## 3. The single daytime build target

If daytime only finishes one meaningful slice, it should be this:

1. implement one normalized decision projection helper
2. wire all core runtime consumers through it
3. wire all reuse consumers through it
4. emit one parity scoreboard plus one reuse/behavior proof
5. fail loudly on deliberate drift fixtures

Everything else is downstream of that.

## 4. The invariant stack that must stay identical

The following semantics should never be independently re-derived once the shared helper exists:
- `memory_promotion_decision`
- `guidance_mode`
- `target_section_family`
- `copyable_worker_instruction_eligibility`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`
- continuity/export/rebuild readiness posture

If any consumer free-styles these fields, the flywheel is not proven.

## 5. The minimal convincing proof case

The smallest convincing daytime pass is one replay-backed redirect or rejection case that emits:
- `review_packet.json`
- `city_compact_decision_object.json`
- `city_coordination_ledger.jsonl`
- `morning_pickup_brief.json`
- `city_dispatch_memory_unit.json`
- runtime/reuse observability rows
- one reused dispatch or redispatch output
- `city_shared_decision_parity_scoreboard.json`

And that same case must show:
- semantic parity across all consumers
- a real behavior change beyond `shown_only`
- trust-preserving reuse
- rebuild parity from compact object + ledger tail
- no anti-overclaim drift

## 6. Highest-value daytime implementation order

### First
Build the normalized decision projection helper.

### Second
Route these consumers through it before widening any surfaces:
- Dispatch Brief composer
- Morning Pickup Brief writer
- Memory export writer
- Session rebuild helper
- Coordination ledger writer
- Runtime observability writer

### Third
Route reuse consumers through the same seam:
- initial dispatch-context reuse
- redispatch fallback reuse
- worker-instruction block builder
- reuse observability writer

### Fourth
Emit two end-state receipts:
- parity scoreboard
- reuse/behavior-change proof result

### Fifth
Add deliberate drift fixtures for:
- promotion drift
- tone drift
- placement drift
- copyability drift
- anti-overclaim drift
- rebuild drift

## 7. What daytime should explicitly not do first

Do not spend the next window on:
- broader template expansion
- richer dashboards
- heavy retrieval cleverness
- generalized Acontext plumbing
- any surface polish that sits above unstable decision semantics

The bottleneck is still proof compression, not product breadth.

## 8. Daytime questions worth answering in code review

The next PR review should be able to answer these quickly:
1. Which file owns the normalized decision projection?
2. Which consumers still derive trust semantics on their own?
3. Does one replay-backed case prove behavior change beyond display-only memory?
4. Does the parity scoreboard end `pass` on all dangerous axes?
5. Can rebuild recover the same next move from compact artifacts plus ledger tail alone?
6. Which drift fixtures currently fail, and where do they localize the bug?

If reviewers cannot answer those six questions without code archaeology, the seam is still too loose.

## 9. Strategic recommendation for daytime

**Treat the next build as one decision-flywheel proof harness, not a collection of related City Ops improvements.**

That framing should keep implementation honest:
- one shared truth seam
- one justified behavior change
- one parity scoreboard
- one rebuild-safe continuity chain
- one explicit set of loud-fail drifts

If that passes once, City as a Service starts looking like a real operational learning system.
If it does not, the right move is still seam tightening, not scope growth.

## 10. Bottom line

The night's work now compresses to one daytime mission:

> prove that one reviewed city decision can move the next dispatch in the right direction without semantic drift anywhere along the chain.

That is the narrowest proof that turns the current planning stack into a shippable product loop.
