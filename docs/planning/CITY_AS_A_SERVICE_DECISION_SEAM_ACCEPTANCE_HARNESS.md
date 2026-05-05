# City as a Service — Decision Seam Acceptance Harness

> Last updated: 2026-05-02
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_TARGET_AND_DECISION_FLYWHEEL.md`
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_COMPACT_DECISION_OBJECT_AND_COORDINATION_LEDGER_SLICE.md`
> - `CITY_AS_A_SERVICE_REUSE_AND_REDISPATCH_ALIGNMENT_SLICE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> Status: 7am dream-session handoff

## 1. Why this doc exists

The planning stack is now sharp enough that daytime could still fail in a new way:
- build the normalized decision helper
- wire consumers correctly in isolation
- add reuse events and observability rows
- yet still never prove the whole chain as one acceptance harness

That would create several correct local seams without one enforceable product proof.

This doc closes that gap.

> the next daytime build window should be treated as one acceptance harness for a single shared decision seam, not as a bundle of adjacent feature tickets.

## 2. The single product proof

The seam should be considered real only if one replay-backed city case proves:

1. reviewed truth is conservative and inspectable
2. one compact decision object carries that truth forward
3. every runtime consumer preserves the same trust posture
4. reuse changes the next dispatch behavior for the right reason
5. observability and ledger artifacts prove the behavior change without semantic drift

If any one of those breaks, City as a Service is still documenting learning rather than operationalizing it.

## 3. Acceptance-harness objects

One selected replay-backed case should emit, from the same judgment seam:
- `review_packet.json`
- `city_compact_decision_object.json`
- `city_coordination_ledger.jsonl`
- `morning_pickup_brief.json`
- `city_dispatch_memory_unit.json`
- one runtime observability row
- one reuse observability row
- one initial dispatch output
- one redispatch or worker-instruction output
- one `city_shared_decision_parity_scoreboard.json`

The harness should fail if any of these require ad hoc reinterpretation.
It should also fail if reviewers cannot grade the reuse outcome from one compact scoreboard without reopening the whole bundle.
It should also fail if the block cannot end in one explicit combined verdict about whether to expand, tighten, or stop for drift.
It should also fail if that verdict cannot be carried forward as one compact telemetry row for pickup, rebuild, observability, and export-readiness review.
It should also fail if that telemetry row cannot pass a compact review proving it preserved the same closure truth and claim limits as the scoreboards.
It should also fail if the emitted pickup brief cannot pass `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_PICKUP_BRIEF_CONTRACT.md` as a strict mirror of that same closure truth.

## 4. Canonical harness scenario

The first acceptable proof scenario should stay narrow:

1. a `counter_question` or `packet_submission` case is reviewed
2. the replay bundle emits a valid `review_packet.json`
3. the packet yields one normalized decision projection
4. the compact decision object is emitted from that projection
5. the dispatch brief composer uses that projection directly
6. the pickup brief writer uses that same projection directly
7. the memory export writer uses that same projection directly
8. the rebuild helper reconstructs the next move from compact object plus ledger tail
9. a later dispatch or redispatch reuses the same projection
10. the reuse changes routing, worker instructions, evidence guidance, or escalation for an explicit reason
11. the ledger and observability rows preserve the same trust class throughout

If the proof case stops before step 9, the harness is incomplete.

## 5. Shared invariants that must never drift

The harness should assert parity for these fields across every emitted consumer artifact and ledger mirror row:
- `compact_decision_id`
- `coordination_session_id`
- `review_packet_id`
- `summary_judgment`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- `continuity_ready`
- `export_ready`
- `session_rebuild_ready`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`

The system may summarize these, but it may not silently strengthen, weaken, or omit them.

## 6. Harness pass criteria by seam

### 6.1 Replay seam passes when
- `review_packet.json` makes the learning judgment inspectable without transcript archaeology
- promotion stance is explicit
- anti-overclaim state is explicit
- the next smallest proof is explicit

### 6.2 Runtime carriage seam passes when
- brief, pickup, export, rebuild, observability, and ledger consumers all read one normalized decision projection
- no consumer re-derives tone, placement, copyability, or readiness independently
- one explicit downgrade path is recorded rather than silently mutating semantics

### 6.3 Reuse seam passes when
- a later dispatch or redispatch consumes the same decision projection
- behavior changes are classified as one of:
  - `shown_only`
  - `routing_changed`
  - `instruction_changed`
  - `evidence_guidance_changed`
  - `redispatch_changed`
  - `escalation_changed`
- trust posture is preserved during the behavior change

### 6.4 Observability seam passes when
- one row can answer whether memory was merely shown or materially used
- one row can identify the governing trust posture
- one row can link back to `compact_decision_id` and `review_packet_id`
- one paired reuse-behavior scoreboard can grade whether the behavior change was supported, trust-preserving, and operationally justified

### 6.5 Rebuild seam passes when
- the next active move can be reconstructed from compact object plus ledger tail
- rebuild does not require transcript dependency
- if rebuild cannot preserve trust posture, it fails loudly

## 7. Drift tests that should be first-class

The harness should deliberately try to induce these failures:

### 7.1 Promotion drift
A consumer renders `directive` guidance when the decision seam says `cautious`.

### 7.2 Placement drift
Inspect-only guidance appears in top-line or copyable worker-instruction zones.

### 7.3 Copyability drift
Worker-facing output becomes copyable when `copyable_worker_instruction=false`.

### 7.4 Anti-overclaim drift
`not_safe_to_claim[]` disappears from pickup, rebuild, or reuse outputs without exclusion logic.

### 7.5 Readiness drift
A downstream surface implies continuity/export/rebuild readiness beyond what the decision seam allowed.

### 7.6 Provenance drift
An emitted runtime, reuse, or observability artifact cannot point back to the governing packet and compact decision.

If any of these fail silently, the seam is not ready.

## 8. Recommended daytime implementation sequence inside this harness

### Step 1
Implement one normalized decision projection helper from `review_packet` and replay-aligned context.

### Step 2
Route these consumers through it:
- Dispatch Brief composer
- Morning Pickup Brief writer
- Dispatch memory export writer
- Session rebuild helper
- Observability row writer
- Coordination ledger writer

### Step 3
Route these reuse consumers through the same helper:
- initial dispatch-context reuse
- redispatch fallback reuse
- worker-instruction block builder
- reuse observability row writer

### Step 4
Add fixture-backed parity assertions across all emitted artifacts.

### Step 5
Add deliberate drift fixtures that must fail loudly.

### Step 6
Emit `CITY_AS_A_SERVICE_REUSE_BEHAVIOR_PROOF_SCOREBOARD.md`-aligned scoreboard artifacts so the final harness can judge whether reuse delivered a real, trust-preserving execution improvement.

### Step 7
Apply `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md` so the block ends in one combined verdict instead of two loosely interpreted scoreboard readings.

### Step 8
Emit the proof-block telemetry gate row so combined verdict, portability state, and anti-overclaim carry-forward remain queryable after the replay review window closes.

### Step 9
Review that telemetry row with `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md` before treating the block as handoff-ready.

### Step 10
Review the emitted pickup brief with `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_PICKUP_BRIEF_CONTRACT.md` before letting it anchor continuity.

### Step 11
Use `CITY_AS_A_SERVICE_DECISION_DRIFT_TRIAGE_PLAYBOOK.md` as the mandatory first response path whenever parity, reuse, rebuild, export, observability, telemetry-packaging, or pickup-brief closure drift fixtures fail.

## 9. Suggested test table for the first harness run

| Test case | Expected behavior change | Required trust posture | Required loud failure if broken |
|---|---|---|---|
| Redirect memory reused in new dispatch | `routing_changed` | `cautious` or `directive` as judged | promotion drift |
| Evidence restriction reused in worker guidance | `instruction_changed` or `evidence_guidance_changed` | non-copyable if packet forbids it | copyability drift |
| Appointment-required case reused in redispatch | `redispatch_changed` | verify-first unless strongly promoted | placement drift |
| Weak learning shown only | `shown_only` | `inspect_only` or `suppressed` | anti-overclaim drift |
| Resume from compact object + ledger tail | rebuild recovers next move | exact prior trust posture | readiness drift |

## 10. What daytime should avoid while this harness is incomplete

Do not broaden scope into:
- more templates
- richer dashboards
- retrieval cleverness
- multi-city expansion
- generic cross-vertical cleanup
- transport swaps or heavy Acontext integration

Those all become safer after this harness proves one real decision flywheel.

## 11. Sharp recommendation

**Treat the next PR sequence as one proof artifact: a single decision seam that survives replay, runtime carriage, reuse, rebuild, and measurement without trust drift.**

That is the narrowest build target that would make the City-as-a-Service stack operationally real.
A proof harness is only complete when its end state is operationally legible too: expand, tighten, or fix drift.
And that end state should be mirrored in one compact telemetry gate row, then reviewed so the row itself does not dilute the verdict or anti-overclaim posture.

When the harness fails, the next move should not be guesswork.
Use `CITY_AS_A_SERVICE_DECISION_DRIFT_TRIAGE_PLAYBOOK.md` to classify whether the bug came from projection, consumer wiring, downgrade handling, or mirror/observability drift before broadening scope.
