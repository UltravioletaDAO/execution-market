# City as a Service — Decision Projection Implementation Slice

> Last updated: 2026-05-03
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_TARGET_AND_DECISION_FLYWHEEL.md`
> - `CITY_AS_A_SERVICE_DECISION_SEAM_ACCEPTANCE_HARNESS.md`
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_SHARED_DECISION_PARITY_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_REUSE_BEHAVIOR_PROOF_SCOREBOARD.md`
> Status: next-daytime implementation slice

## 1. Why this doc exists

The planning stack has already converged on the same recommendation from several angles:
- one reviewed city case should drive one shared decision seam
- every runtime and reuse consumer should preserve the same trust posture
- proof should end in one parity/behavior scoreboard instead of a pile of artifacts

What is still too abstract is the exact coding slice that turns that recommendation into buildable work.
Daytime now needs a file-first implementation plan that is narrow enough to ship and strict enough to prevent semantic drift.

This doc closes that gap.

> the next implementation slice should be one shared decision projection helper plus its first mandatory consumers, fixtures, and scoreboards.

## 2. The single engineering objective

Implement one normalized decision projection helper that takes replay-backed judgment inputs and produces the exact shared fields all downstream consumers must read.

If that helper exists but consumers still re-derive semantics locally, the slice failed.
If consumers align but no fixtures or scoreboards prove parity, the slice is still incomplete.

## 3. The concrete output of this slice

One replay-backed city case should be able to produce all of the following from the same normalized projection:
- `review_packet.json`
- `city_compact_decision_object.json`
- `city_dispatch_brief.json`
- `morning_pickup_brief.json`
- `city_dispatch_memory_unit.json`
- one session rebuild output
- one runtime observability row
- one reuse observability row
- one dispatch reuse / redispatch / worker-instruction output
- `city_shared_decision_parity_scoreboard.json`
- `city_reuse_behavior_scoreboard.json`

That is the smallest implementation slice that proves the decision flywheel is real rather than merely documented.

## 4. Recommended code placement

```text
mcp_server/city_ops/
  contracts.py
  decision_projection.py
  brief_composer.py
  pickup_brief.py
  memory_export.py
  rebuild.py
  observability.py
  reuse.py
  scoreboards.py
  fixtures/
    city_ops_review_cases/
```

If actual file names differ, the placement rule still holds:
- keep the projection helper central
- keep consumers thin
- keep scoreboard writers near the same seam
- keep fixtures close enough to assert drift loudly

## 5. The projection helper contract

### 5.1 Required inputs
The first projection helper should accept, directly or via one wrapper object:
- `review_packet`
- compact replay-aligned provenance refs
- any minimal contextual fields needed for rendering/reuse classification

It should not require transcript parsing or ad hoc consumer-specific inference.

### 5.2 Required outputs
The helper should emit a normalized projection containing at minimum:
- `compact_decision_id`
- `coordination_session_id`
- `review_packet_id`
- `summary_judgment`
- `learning_strength`
- `memory_promotion_decision`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- `continuity_ready`
- `export_ready`
- `session_rebuild_ready`
- `operator_surface_ready`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`
- `source_episode_ids[]`
- compact provenance refs

### 5.3 Hard rule
No downstream consumer may independently compute:
- promotion class
- guidance tone
- guidance placement
- copyability
- readiness flags
- anti-overclaim posture

If any consumer needs a downgrade, that downgrade must be explicit and ledger-visible.

## 6. Mandatory first consumers

The first slice should wire these consumers directly to the shared projection:
1. Dispatch Brief composer
2. Morning Pickup Brief writer
3. Dispatch memory export writer
4. Session rebuild helper
5. Runtime observability row writer
6. Reuse observability row writer
7. Dispatch reuse / redispatch / worker-instruction output builder
8. Coordination ledger mirror writer

This is intentionally broader than the earliest runtime list because daytime now needs one proof of end-to-end parity, not just continuity-time alignment.

## 7. Minimal implementation order

### Step 1 — lock projection schema
Deliver:
- typed projection object / dataclass / schema
- deterministic mappings from `review_packet` fields to normalized runtime semantics
- explicit downgrade note shape

Acceptance:
- projection can be created from one replay-backed case without consumer-specific code paths

### Step 2 — emit compact decision object from projection
Deliver:
- `city_compact_decision_object.json` built as the persistent/shared runtime truth
- stable identity fields and provenance refs

Acceptance:
- every later consumer can read from compact decision object without reopening full replay artifacts

### Step 3 — route core runtime consumers through projection
Deliver:
- brief writer
- pickup writer
- memory export writer
- rebuild helper
- runtime observability row writer

Acceptance:
- one fixture-backed case proves these consumers preserve the same trust semantics

### Step 4 — route reuse consumers through projection
Deliver:
- initial dispatch reuse output
- redispatch fallback output
- worker-instruction rendering gate
- reuse observability row writer

Acceptance:
- one fixture-backed case proves behavior change happens in one explicit class without trust inflation

### Step 5 — add scoreboard writers
Deliver:
- parity scoreboard writer
- reuse behavior scoreboard writer
- coordination-ledger mirror event for scoreboard summary

Acceptance:
- reviewers can grade semantic sameness and behavior-change legitimacy without diffing all downstream artifacts manually

### Step 6 — add deliberate drift fixtures
Deliver fixtures that intentionally induce:
- promotion drift
- tone drift
- placement drift
- copyability drift
- readiness drift
- anti-overclaim drift
- provenance loss
- rebuild transcript dependency

Acceptance:
- each drift fails loudly, not as a cosmetic warning

## 8. Suggested fixture progression

The first implementation pass does not need many fixtures.
It needs the right ones.

### 8.1 Redirect case
Expected result:
- `routing_changed`
- cautious or directive based on replay-backed evidence
- parity scoreboard passes
- reuse behavior scoreboard says smarter for the right reason

### 8.2 Evidence restriction case
Expected result:
- `instruction_changed` or `evidence_guidance_changed`
- worker-copyable block constrained correctly
- copyability drift fixture fails loudly if broken

### 8.3 Appointment-required redispatch case
Expected result:
- `redispatch_changed`
- verify-first posture preserved
- placement drift fails loudly if summary becomes directive

### 8.4 Weak-learning case
Expected result:
- `shown_only`
- inspect-only or suppressed behavior
- no overclaim allowed

## 9. Scoreboard obligations in this slice

### 9.1 Parity scoreboard must answer
- did all consumers preserve the same decision semantics?
- did any consumer require an explicit downgrade?
- did rebuild preserve the same next move?
- did observability keep the same trust posture?

### 9.2 Reuse behavior scoreboard must answer
- what behavior-change class occurred?
- was that change supported by judged truth?
- was trust posture preserved?
- was overclaim avoided?
- did the next action become smarter for the right reason?

### 9.3 Hard acceptance rule
Do not call the slice done unless one replay-backed case yields:
- parity scoreboard with dangerous axes passing
- reuse behavior scoreboard showing more than `shown_only`
- no hidden trust inflation

## 10. What this slice should explicitly not do

Do not spend the first implementation window on:
- more templates
- richer dashboard polish
- broad Acontext transport work
- multi-city generalization
- retrieval cleverness beyond export readiness
- abstractions that separate consumers from the projection seam

The goal is not elegance through breadth.
It is one real proof through tight coupling to judged truth.

## 11. Review order for the resulting PR

Reviewers should be able to inspect the slice in this order:
1. projection schema/helper
2. compact decision object emission
3. core consumer wiring
4. reuse consumer wiring
5. parity scoreboard output
6. reuse behavior scoreboard output
7. deliberate drift fixtures

If correctness depends on reading consumers before understanding the projection seam, the slice is still too loose.

## 12. Sharp recommendation

**Build the next daytime slice as one decision-projection implementation PR, not a handful of polite related tickets.**

That is the shortest path from the current planning corpus to a real City-as-a-Service learning loop that can prove the next dispatch got smarter without trust drift.
