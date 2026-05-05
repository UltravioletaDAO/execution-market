# City as a Service — Coordination Carry-Forward Matrix

> Last updated: 2026-05-05 03:12 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> - `CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`
> - `CITY_AS_A_SERVICE_ACONTEXT_LOCAL_SERVER_AND_SESSION_DISCIPLINE.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md`
> Status: implementation handoff companion

## 1. Why this doc exists

The planning stack already has the right ingredients:
- compact replay-backed decision truth
- runtime alignment rules
- local-first Acontext/session discipline
- proof-block telemetry closure
- observability scorecards

What is still easy to lose is the **carry-forward join** between those layers.
Daytime can still end up with:
- a correct replay verdict
- a good dispatch brief
- a rebuild-safe ledger tail
- a plausible Acontext export object
- a telemetry row

...while each surface carries a slightly different subset of the same decision.
That creates a quieter failure mode than outright drift:
**field drop drift**.
The trust posture stays roughly right, but the system stops carrying enough shared fields for:
- restart-safe session rebuild
- Acontext sink-swap verification
- cross-project event reuse
- observability joins that explain *why* behavior changed

This doc closes that gap.

> one reviewed city decision should carry the same minimum join fields through runtime, continuity, export, telemetry, and later Acontext retrieval — or fail loudly.

## 2. The single question

For one replay-backed city case:

> which fields must survive every carry-forward surface so the same judgment remains queryable, rebuildable, exportable, and reusable without transcript archaeology?

If that field set is not explicit, the control plane will look aligned while slowly losing operational memory.

## 3. Carry-forward surfaces

The first implementation window should treat these as the required carry-forward surfaces:
1. `city_compact_decision_object.json`
2. `city_dispatch_brief.json`
3. `morning_pickup_brief.json`
4. local coordination ledger rows
5. observability / proof telemetry row
6. `city_dispatch_memory_unit.json` export object
7. Acontext retrieval result shape
8. session rebuild output

If a surface cannot preserve the required carry-forward fields, it must declare a downgrade explicitly.

## 4. Minimum carry-forward field classes

### 4.1 Identity joins
These make all later artifacts queryable against the same case:
- `coordination_session_id`
- `review_packet_id`
- `compact_decision_id`
- `workflow_template`
- `jurisdiction_name`
- `office_name`

### 4.2 Decision truth joins
These preserve the actual judged meaning:
- `summary_judgment`
- `learning_strength`
- `memory_promotion_decision`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`

### 4.3 Readiness joins
These preserve whether the seam is actually portable:
- `coordination_trace_complete`
- `continuity_ready`
- `session_rebuild_ready`
- `export_ready`
- `acontext_sink_ready`
- `cross_project_event_reusable`

### 4.4 Anti-overclaim joins
These preserve the limits of the current proof:
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `supported_behavior_change_reason[]`
- `next_smallest_proof[]`
- `dangerous_axes_failed[]`

### 4.5 Provenance joins
These keep the system auditable without replay bundle spelunking:
- `source_episode_ids[]`
- `event_summary_id` or equivalent summary ref
- compact `provenance_refs`

## 5. Carry-forward matrix

| Surface | Must preserve exactly | May summarize | Must never drop silently | Loud-fail event |
|---|---|---|---|---|
| Compact decision object | all identity, decision, readiness, anti-overclaim core fields | none | any invariant field | `city_compact_decision_emitted` failure |
| Dispatch brief | `promotion_class`, `guidance_tone`, `guidance_placement`, `copyable_worker_instruction`, `not_safe_to_claim[]`, key identity joins | operator phrasing, section grouping | readiness posture and claim limits | `city_dispatch_brief_composed` downgrade |
| Morning pickup brief | verdict, readiness joins, `not_safe_to_claim[]`, `next_smallest_proof[]`, key identity joins | continuity wording | dangerous axes, rebuild/export posture | `city_pickup_brief_emitted` downgrade |
| Coordination ledger row | identity joins, decision truth joins, reuse/behavior classification, readiness flags | event-local payload details | provenance and trust posture | mirrored event row mismatch |
| Proof telemetry row | identity joins, verdict, behavior class, readiness joins, anti-overclaim joins | compact justification prose | dangerous-axis failures, downgrade count | telemetry gate mismatch |
| Dispatch memory export | identity joins, decision truth joins, readiness joins, top guidance/open questions | retrieval metadata, freshness labels | promotion/tone/placement/copyability semantics | `city_memory_export_emitted` downgrade |
| Acontext retrieval result | identity joins, decision truth joins, top guidance/open questions, readiness and claim limits relevant to dispatch | retrieval formatting | promotion class and trust posture | retrieval parity failure |
| Session rebuild output | identity joins, next move, top guidance mode, readiness posture, `next_smallest_proof[]` | resume summary phrasing | `not_safe_to_claim[]` and current stop condition | `city_session_rebuild_failed` |

## 6. Surface-specific rules

### 6.1 Dispatch brief
The brief may compress but must still let a reviewer answer:
- which reviewed packet this guidance came from
- whether the guidance is directive, cautious, inspect-only, or suppressed
- whether the operator is allowed to hand the instruction to a worker directly
- what remains unsafe to claim

If those answers require reopening the replay bundle, the carry-forward seam is too thin.

### 6.2 Morning pickup brief
The pickup brief is the night/day handoff seam.
It must preserve enough shared fields that the next session can decide whether to:
- continue the same seam
- tighten proof
- fix drift
- export safely

It should never soften `tighten_same_seam` into a generic progress note.

### 6.3 Ledger rows
The ledger is not just an audit trail.
It is the shared join table for:
- session rebuild
- observability
- Acontext sink prep
- cross-project decision-support reuse

That means ledger rows should carry the same compact truth, not just event names.

### 6.4 Export and Acontext retrieval
The sink-swap path should treat `city_dispatch_memory_unit.json` as the canonical export seam.
Acontext retrieval should then prove it can return the same:
- trust posture
- guidance placement
- copyability boundary
- top guidance vs open question separation

If Acontext retrieval returns only a blended note blob, the carry-forward seam failed.

## 7. Join completeness checks

The first implementation should grade these checks explicitly.

### 7.1 Session join completeness
Pass only if the same `coordination_session_id` links:
- ledger rows
- pickup brief
- telemetry row
- export object
- rebuild output

### 7.2 Proof join completeness
Pass only if `review_packet_id` and `compact_decision_id` survive into:
- telemetry
- export
- rebuild output or linked provenance
- observability rows

### 7.3 Claim-limit completeness
Pass only if `not_safe_to_claim[]` and `next_smallest_proof[]` survive into:
- pickup brief
- telemetry row
- rebuild output

### 7.4 Portability completeness
Pass only if rebuild/export/Acontext/cross-project readiness judgments are queryable from one compact row or pair of rows without replay bundle reopening.

## 8. Recommended observability additions

To make carry-forward completeness measurable, add these explicit metrics beside the existing observability stack:
- `carry_forward_join_completeness_rate`
  - percent of replay-backed proof blocks where identity joins survive across all required surfaces
- `claim_limit_survival_rate`
  - percent of proof blocks where `not_safe_to_claim[]` and `next_smallest_proof[]` persist through pickup, telemetry, and rebuild outputs
- `export_retrieval_parity_rate`
  - percent of exported memory units whose retrieved Acontext result preserves the same promotion/tone/placement/copyability semantics
- `session_handoff_field_loss_rate`
  - percent of pickup/rebuild seams that drop at least one required readiness or dangerous-axis field

These metrics make field-drop drift visible instead of anecdotal.

## 9. Recommended next daytime use

This doc should be used as the join-check companion when daytime reaches PR D closure packaging.
The closure chain should now verify not only:
- parity scoreboard
- reuse verdict
- telemetry row fidelity
- pickup brief fidelity

but also:
- carry-forward join completeness across pickup, ledger, telemetry, export, and rebuild surfaces

That is the narrowest extra step that strengthens:
- memory ↔ Acontext planning
- IRC/session rebuild discipline
- cross-project decision-support reuse
- agent observability and success metrics

without expanding scope into new product surfaces.

## 10. Acceptance gate

Do not call the first shared-decision proof block handoff-safe until one replay-backed case proves:
- all required identity joins survive across every carry-forward surface
- claim limits survive pickup, telemetry, and rebuild outputs
- export object and retrieval result preserve the same trust posture
- session rebuild can explain the next move from compact joins alone
- any dropped field is explicit, counted, and reviewable as a downgrade

## 11. Sharp recommendation

**The next failure mode is not obvious semantic drift. It is quiet carry-forward field loss.**

Lock the minimum join fields now, or the system will slowly lose the ability to explain why a dispatch changed, why a session is rebuild-safe, or whether Acontext is preserving the same judged truth.