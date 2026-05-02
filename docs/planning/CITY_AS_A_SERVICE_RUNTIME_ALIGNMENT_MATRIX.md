# City as a Service — Runtime Alignment Matrix

> Last updated: 2026-05-02
> Parent docs:
> - `CITY_AS_A_SERVICE_COMPACT_DECISION_OBJECT_AND_COORDINATION_LEDGER_SLICE.md`
> - `CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`
> - `CITY_AS_A_SERVICE_MORNING_PICKUP_BRIEF_CONTRACT.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_OPERATOR_GUIDANCE_TONE_AND_PLACEMENT_POLICY.md`
> Status: implementation handoff companion

## 1. Why this doc exists

The planning stack now says the right thing repeatedly:
- one replay-backed judgment should survive across runtime consumers
- compact decision state should drive brief, pickup, export, rebuild, and observability
- tone/placement and anti-overclaim rules must not drift between surfaces
- append-only coordination events should make that drift inspectable

What is still missing is a single matrix that lets daytime implementation answer, file by file:
- which runtime consumer reads which fields
- which fields are required versus derived
- which alignment checks should fail loudly
- which event should be emitted when each consumer materializes state

Without that matrix, the compact decision object can still become another good idea that each surface interprets slightly differently.

This doc closes that gap.

## 2. Core principle

**Every runtime consumer should either mirror the compact decision object faithfully or declare its downgrade explicitly.**

No surface should silently:
- strengthen cautious guidance into directive language
- move inspect-only learning into copyable worker instructions
- drop anti-overclaim warnings
- forget readiness judgments that were part of the replay proof

## 3. Canonical runtime consumers

The first slice should treat these as the only required consumers:
1. Dispatch Brief composer
2. Morning Pickup Brief writer
3. Dispatch memory export writer
4. Session rebuild helper
5. Observability row writer
6. Coordination ledger writer

If a new surface cannot map itself cleanly onto this matrix, it is probably premature for the first implementation window.

## 4. Source-of-truth rule

### 4.1 Primary runtime source
`city_compact_decision_object.json` is the primary shared runtime truth.

### 4.2 Ordered supporting sources
Consumers may read supporting artifacts only in this order:
1. `city_compact_decision_object.json`
2. `review_packet.json`
3. `morning_pickup_brief.json`
4. `event_summary.json`
5. `bundle_manifest.json`

They should not need full replay artifacts or transcripts for the normal path.

### 4.3 Downgrade rule
If a consumer cannot honor a field exactly, it must:
- emit a downgrade note
- preserve the original field value in provenance
- write a coordination ledger event that exposes the downgrade

That prevents semantic drift from hiding inside convenience logic.

## 5. Alignment matrix

| Consumer | Required inputs | Must preserve exactly | Allowed derived fields | Must emit event |
|---|---|---|---|---|
| Dispatch Brief composer | compact decision object | `promotion_class`, `guidance_tone`, `guidance_placement`, `copyable_worker_instruction`, `safe_to_claim`, `not_safe_to_claim` | section text formatting, brief section grouping, fallback wording | `city_dispatch_brief_composed` |
| Morning Pickup Brief writer | compact decision object + gate state | `summary_judgment`, readiness flags, `next_smallest_proof`, `not_safe_to_claim` | acceptance gate grouping, continuity phrasing | `city_pickup_brief_emitted` |
| Dispatch memory export writer | compact decision object | `promotion_class`, `guidance_tone`, `guidance_placement`, provenance refs, readiness flags | retrieval metadata, freshness labels | `city_memory_export_emitted` |
| Session rebuild helper | compact decision object + ledger tail | readiness flags, `top_guidance`, `top_open_questions`, `next_smallest_proof` | rebuild summary text, operator resume hint | `city_session_rebuild_attempted` + terminal rebuild event |
| Observability row writer | compact decision object + reuse context | `coordination_session_id`, `review_packet_id`, `compact_decision_id`, `promotion_class`, `guidance_tone`, `guidance_placement`, readiness flags | aggregate tags, score buckets, reuse mode labels | `city_observability_row_emitted` |
| Coordination ledger writer | compact decision object + consumer event context | all mirrored decision fields chosen for ledger schema | event-local payload details only | event being mirrored |

## 6. Required shared fields across all consumers

The following fields should be considered first-class runtime invariants:
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
- `provenance_refs`

If any of these disappear between surfaces without an explicit downgrade, the runtime seam is not aligned.

## 7. Consumer-specific behavior rules

### 7.1 Dispatch Brief composer
The brief composer may rephrase for operator clarity, but must not change trust class.

Rules:
- `directive` guidance may appear in top-line worker-operational sections
- `cautious` guidance may appear only in verify-first/watchout sections
- `inspect_only` guidance must stay out of default copyable worker instructions
- `suppressed` guidance must not surface in the default brief body
- `not_safe_to_claim[]` should influence exclusion, not just styling

### 7.2 Morning Pickup Brief writer
The pickup brief is allowed to summarize, but not reinterpret.

Rules:
- if `session_rebuild_ready=false`, the brief may not imply clean continuity handoff
- if `operator_surface_ready=false`, the brief must keep UI-readiness claims narrow
- `do_not_claim_yet` should inherit from `not_safe_to_claim[]` unless a stricter continuity warning is needed

### 7.3 Dispatch memory export writer
This consumer is the bridge to future Acontext or retrieval sinks.

Rules:
- export objects must preserve the same promotion/tone/placement semantics as runtime surfaces
- export may add retrieval keys such as `office_key`, `workflow_template`, or freshness windows
- export must keep provenance refs compact but sufficient for audit backtracking

### 7.4 Session rebuild helper
The rebuild helper should reconstruct actionability, not the full archive.

Rules:
- rebuild should prefer the latest compact decision object linked by session id
- rebuild should use ledger tail only to determine the most recent mirrored consumer state
- rebuild output must include current next move, top open question, and latest safe guidance mode
- if rebuild needs transcript archaeology, it should fail loudly as `session_rebuild_ready=false`

### 7.5 Observability row writer
Observability is a consumer, not a judge.

Rules:
- it must not infer stronger readiness or stronger promotion than the compact decision object carried
- it should preserve enough dimensions to query drift and reuse quality later
- it should record the consumer context that produced the row, not just the case identity

### 7.6 Coordination ledger writer
The ledger is the runtime drift detector.

Rules:
- every mirrored event row should preserve the shared field subset consistently
- event-local payloads may vary, but decision semantics may not
- explicit downgrades should be recorded as payload or note fields rather than silent omission

## 8. Alignment checks that should fail loudly

The first implementation should validate at least these checks:

### 8.1 Promotion drift check
Fail if one consumer renders:
- `promotion_class=directive`
when the compact decision object says:
- `promotion_class=cautious`

### 8.2 Placement drift check
Fail if inspect-only or suppressed learning appears in a copyable worker-instruction section.

### 8.3 Anti-overclaim drop check
Fail if `not_safe_to_claim[]` disappears from pickup or rebuild continuity outputs without replacement warnings.

### 8.4 Readiness drift check
Fail if a downstream consumer implies:
- `continuity_ready=true`
- `export_ready=true`
- `session_rebuild_ready=true`
when the compact decision object marked any of them false.

### 8.5 Provenance loss check
Fail if export or observability outputs cannot link back to:
- `compact_decision_id`
- `review_packet_id`
- at least one replay-proof provenance ref

### 8.6 Copyability drift check
Fail if `copyable_worker_instruction=false` but worker-facing rendered output is still flagged copyable.

## 9. Event mirroring expectations

The runtime alignment slice should mirror these events at minimum:
- `city_compact_decision_emitted`
- `city_dispatch_brief_composed`
- `city_pickup_brief_emitted`
- `city_memory_export_emitted`
- `city_session_rebuild_attempted`
- `city_session_rebuild_succeeded` or `city_session_rebuild_failed`
- `city_observability_row_emitted`

Each mirrored row should include:
- identity fields
- promotion/tone/placement fields
- readiness flags
- one event-local payload block

## 10. Recommended implementation order

### Step 1
Lock the compact decision object schema with explicit shared invariants.

### Step 2
Implement one helper that projects compact decision fields into a normalized runtime view for all consumers.

### Step 3
Have the brief, pickup, export, rebuild, and observability writers consume that helper instead of re-deriving semantics independently.

### Step 4
Write ledger rows from the same normalized runtime view.

### Step 5
Add fixture-backed alignment assertions that intentionally try to create drift across:
- tone
- placement
- copyability
- readiness
- anti-overclaim warnings

## 11. Acceptance gate for this companion slice

Do not call the compact-decision runtime seam aligned until one replay-backed case proves all of the following:
- the same compact decision fields flow into all six runtime consumers
- mirrored ledger events preserve those fields unchanged
- one induced downgrade is recorded explicitly instead of silently mutating semantics
- rebuild can recover the next move and trust posture from compact artifacts plus ledger tail
- observability/export outputs remain compact but provenance-safe

## 12. Relationship to reuse and redispatch

This runtime matrix governs replay-time and continuity-time consumers first.
The next adjacent slice should apply the same invariant fields to reuse-time consumers too:
- initial dispatch-context reuse
- redispatch fallback reuse
- worker-instruction copyability filtering
- reuse observability rows

Those consumers should not invent a second decision seam.
They should read the same normalized runtime view and fail loudly on trust-class drift.

See also:
- `CITY_AS_A_SERVICE_REUSE_AND_REDISPATCH_ALIGNMENT_SLICE.md`

## 13. Sharp recommendation

**Build the runtime seam as a matrix, not as a set of polite conventions.**

The matrix is what turns the current planning work into something daytime can implement without reintroducing semantic drift at every surface boundary.
