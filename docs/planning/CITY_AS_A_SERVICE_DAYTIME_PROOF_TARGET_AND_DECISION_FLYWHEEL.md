# City as a Service — Daytime Proof Target and Decision Flywheel

> Last updated: 2026-05-02
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_COMPACT_DECISION_OBJECT_AND_COORDINATION_LEDGER_SLICE.md`
> - `CITY_AS_A_SERVICE_REUSE_AND_REDISPATCH_ALIGNMENT_SLICE.md`
> - `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md`
> Status: pre-dawn synthesis handoff

## 1. Why this doc exists

The current City-as-a-Service planning stack is no longer missing strategy.
It now has enough narrow implementation slices that the daytime risk has changed again:
- building several good seams without proving they compound into one decision loop
- treating replay proof, runtime continuity, and reuse alignment as separate wins
- shipping artifact correctness without proving the next dispatch actually becomes smarter from the same judged truth

This doc compresses the night’s work into one daytime proof target.

> the same reviewed city decision should survive replay, runtime carriage, and reuse-time dispatch change without semantic drift.

If daytime can prove that once, the first City-as-a-Service learning flywheel is real.
If it cannot, the stack is still a clean archive rather than an operational advantage.

## 2. The one daytime question

Daytime should organize the next build window around one question only:

> can one reviewed rejection or redirect produce a compact decision object that changes the next dispatch behavior, while preserving the exact same trust posture across brief, pickup, export, rebuild, reuse, and observability?

That is the smallest proof that joins the current planning seams into one product claim.

## 3. The decision flywheel

The current stack now implies one strict causal loop:

1. worker evidence is reviewed into canonical truth
2. replay proof shows the truth is valid and behaviorally useful
3. compact decision object carries that truth through runtime consumers
4. coordination ledger proves downstream consumers did not reinterpret it
5. next dispatch or redispatch reuses the same truth
6. observability proves whether behavior actually changed
7. later reviews decide whether cautious learning should strengthen, stay held, or be suppressed

This is the first true CaaS decision flywheel.
It should be treated as the product seam, not as documentation polish.

## 4. What is already strong enough

The current planning corpus is already strong on these layers:
- replay artifact order and conservative judgment
- packet-level promotion and guidance semantics
- compact decision object as shared runtime truth
- append-only coordination ledger for continuity and drift detection
- reuse-time trust-preserving dispatch and redispatch rules

Daytime should assume these are conceptually decided.
The next work is not to expand the planning tree.
The next work is to prove these layers operate as one chain.

## 5. The exact proof target

One replay-backed city case should emit all of the following from one shared judgment seam:
- `review_packet.json`
- `city_compact_decision_object.json`
- `city_coordination_ledger.jsonl`
- `morning_pickup_brief.json`
- `city_dispatch_memory_unit.json`
- one observability row
- one reused dispatch or redispatch output

And the same case should prove all of these acceptance points together:
1. replay judgment is conservative and inspectable
2. compact decision fields are explicit enough for all runtime consumers
3. ledger events mirror those fields unchanged
4. pickup/export/rebuild outputs inherit the same trust posture
5. reuse changes actual dispatch or instruction behavior
6. observability records *how* behavior changed, not just that memory was shown
7. no surface silently upgrades cautious learning into directive doctrine

## 6. The most important invariant

**The product is not “memory exists.” The product is “the next city action changes for the right reason.”**

That means the key invariant for daytime is:

> every downstream surface must preserve the same promotion class, guidance tone, guidance placement, copyability boundary, and anti-overclaim state.

If any surface breaks that invariant, the flywheel is fake even if the files all exist.

## 7. Recommended daytime build order

### Step 1 — lock one normalized decision projection helper
Implement one shared helper that maps packet judgment into the exact runtime fields all consumers read.

Required outcome:
- brief, pickup, export, rebuild, observability, and reuse consumers stop deriving semantics independently

### Step 2 — wire all runtime consumers through the shared helper
Consumers in scope:
- Dispatch Brief composer
- Morning Pickup Brief writer
- Dispatch memory export writer
- Session rebuild helper
- Observability row writer
- Coordination ledger writer

Required outcome:
- one replay-backed case can prove cross-consumer semantic parity

### Step 3 — wire reuse consumers through the same helper
Consumers in scope:
- initial dispatch-context reuse
- redispatch fallback reuse
- worker-instruction block builder
- reuse observability row writer

Required outcome:
- the next dispatch visibly changes, but never exceeds the judged trust posture

### Step 4 — add deliberate drift fixtures
Create fixtures that intentionally try to break:
- promotion class
- tone
- placement
- copyability
- readiness flags
- anti-overclaim preservation

Required outcome:
- these drifts fail loudly instead of becoming “just UI differences”

## 8. What daytime should measure first

The first useful observability rows should answer:
- was prior city memory only shown, or materially used?
- did it change routing, worker instructions, evidence guidance, redispatch, or escalation?
- what trust posture governed that reuse?
- did any consumer require a downgrade?
- did rebuild recover the next move from compact artifacts plus ledger tail alone?

If those questions are queryable, the loop is becoming operational.
If not, the team is still instrumenting artifacts rather than decision quality.

## 9. What not to do next

Do not spend the next daytime window on:
- broader multi-city expansion
- heavy Acontext plumbing before this proof exists
- rich dashboards that sit on top of unstable semantics
- new templates that do not strengthen the same learning seam
- retrieval cleverness before trust-preserving reuse is proven

The next bottleneck is not idea breadth.
It is proof compression.

## 10. Sharp recommendation

**Treat the next daytime PR sequence as one proof harness, not several related features.**

Success is not:
- a pretty review panel
- a compact decision file in isolation
- a ledger in isolation
- a pickup brief in isolation

Success is:
- one reviewed city case
- one shared decision seam
- one actual dispatch behavior change
- one observability trail proving the change was trust-preserving and reproducible

That is the first build target that would make City as a Service feel like a real operational learning system instead of a promising planning stack.
