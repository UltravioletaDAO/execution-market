# City as a Service — Compact Decision Object and Coordination Ledger Slice

> Last updated: 2026-05-02
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_CONTINUITY_AND_EXPORT_SEAM.md`
> - `CITY_AS_A_SERVICE_MORNING_PICKUP_BRIEF_CONTRACT.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> Status: next implementation handoff slice

## 1. Why this doc exists

The current planning stack now says the right strategic thing in several places:
- one reviewed replay-backed decision should drive brief rendering, pickup continuity, retrieval export, rebuild, and observability
- `review_packet` is the compact judgment seam
- `morning_pickup_brief.json` is the continuity seam
- replay review should prove continuity/export readiness, not just file existence

What is still too easy to misbuild is the **runtime carriage** of that truth.
A team can agree on one compact decision object in principle and still drift in practice because each consumer writes its own runtime representation:
- dispatch brief composition emits one interpretation
- pickup continuity emits another
- export objects flatten the packet differently
- observability rows lose key rendering fields
- restart/rebuild code has to infer state from transcripts or scattered artifacts

This doc defines the narrowest next slice that prevents that drift:

> one compact decision object, plus one append-only coordination ledger, should carry the same replay-backed truth across render, pickup, export, rebuild, and measurement.

## 2. Core principle

**Replay-backed learning should move through the runtime as one append-only compact decision trail, not as five loosely synchronized summaries.**

The product claim is no longer only:
- can we produce the right artifacts?

It is now also:
- can the active system session recover, continue, export, and measure the same judged truth without semantic reinterpretation?

That means the runtime needs two things:
1. a canonical `city_compact_decision_object.json`
2. a canonical append-only `city_coordination_ledger.jsonl`

## 3. The two runtime objects

### 3.1 Compact decision object
This is the smallest reusable decision-support object derived from `review_packet` plus aligned replay-proof context.
Its job is to answer:
- what was proven?
- how strong is the learning?
- how should the guidance render?
- what continuity/export/rebuild claims are safe now?

It is not the full packet.
It is the exact shared shape downstream consumers should read.

### 3.2 Coordination ledger
This is the append-only runtime trail of coordination-relevant events around the same case.
Its job is to answer:
- what happened in what order?
- which compact decision object version was active when a brief, pickup handoff, export, or rebuild occurred?
- did later surfaces mirror the same truth or drift?

It is not a transcript.
It is not a generic event dump.
It is the minimum durable runtime spine for proving continuity.

## 4. Why these belong in the same slice

A compact decision object without an append-only ledger will still leave daytime blind to timing and drift.
A ledger without a compact decision object will preserve sequence but not semantics.

The next implementation slice should pair them because together they answer the real continuity question:

> did the same replay-backed judgment survive through actual coordination steps, or did each step silently reinterpret it?

## 5. Canonical compact decision object

Recommended first shape:

```json
{
  "compact_decision_version": "v1",
  "compact_decision_id": "cdo_2026_05_02_packet_submission_001",
  "coordination_session_id": "city_packet_submission_2026_05_02_001",
  "review_packet_id": "rp_2026_05_02_001",
  "workflow_template": "packet_submission",
  "jurisdiction_name": "Miami-Dade County",
  "office_name": "Permit Intake Window B",
  "summary_judgment": "pass",
  "learning_strength": "moderate",
  "memory_promotion_decision": "promote_cautiously",
  "promotion_class": "cautious",
  "guidance_tone": "verify_first",
  "guidance_placement": "fallback_and_caution",
  "copyable_worker_instruction": false,
  "replay_readiness_judgment": "pass",
  "continuity_ready": true,
  "export_ready": true,
  "session_rebuild_ready": true,
  "operator_surface_ready": false,
  "top_guidance": [
    "Verify whether Window B is still handling packet intake before full queue commitment."
  ],
  "top_open_questions": [
    "Need one more reviewed redirect episode before directive promotion."
  ],
  "safe_to_claim": [
    "redirect guidance is reusable with verify-first framing"
  ],
  "not_safe_to_claim": [
    "default doctrine for packet rejection prevention is not yet stable"
  ],
  "next_smallest_proof": [
    "replay one repeated redirect fixture with aligned scorecard improvement"
  ],
  "source_episode_ids": [
    "ep_city_ops_2026_05_02_001"
  ],
  "provenance_refs": {
    "bundle_manifest": "city_ops_replay_runs/.../bundle_manifest.json",
    "event_summary": "city_ops_replay_runs/.../event_summary.json",
    "review_packet": "city_ops_replay_runs/.../review_packet.json",
    "pickup_brief": "city_ops_replay_runs/.../morning_pickup_brief.json"
  },
  "freshness_date": "2026-05-02"
}
```

## 6. Compact decision derivation rules

### 6.1 Packet first
The compact decision object should derive from `review_packet` and aligned replay-proof artifacts.
It should not re-judge the case.
It compresses judgment; it does not replace judgment.

### 6.2 Rendering fields are first-class
The object must carry explicit runtime rendering decisions, not just semantic conclusions.
At minimum:
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`

If downstream surfaces still have to derive these ad hoc, the seam is not finished.

### 6.3 Continuity/export/rebuild readiness are explicit
The object must carry explicit readiness judgments for:
- `continuity_ready`
- `export_ready`
- `session_rebuild_ready`

These should not be inferred later from vague success states.

### 6.4 Anti-overclaim state is preserved
The object must preserve:
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`

Without these, restart and export flows will tend to flatten caution away.

## 7. Canonical coordination ledger

Recommended first line shape:

```json
{
  "ledger_version": "v1",
  "event_id": "cled_2026_05_02_0007",
  "coordination_session_id": "city_packet_submission_2026_05_02_001",
  "event_name": "city_dispatch_brief_composed",
  "event_time": "2026-05-02T11:02:18Z",
  "compact_decision_id": "cdo_2026_05_02_packet_submission_001",
  "review_packet_id": "rp_2026_05_02_001",
  "workflow_template": "packet_submission",
  "office_key": "miami_dade__permit_intake_window_b",
  "summary_judgment": "pass",
  "promotion_class": "cautious",
  "guidance_tone": "verify_first",
  "guidance_placement": "fallback_and_caution",
  "copyable_worker_instruction": false,
  "replay_readiness_judgment": "pass",
  "continuity_ready": true,
  "export_ready": true,
  "session_rebuild_ready": true,
  "event_payload": {
    "brief_id": "brief_2026_05_02_001",
    "reuse_mode": "office_memory_plus_replay_packet",
    "source_episode_count": 1
  }
}
```

## 8. Ledger event families

The first ledger slice should not try to mirror everything.
It should mirror only the events needed to prove continuity and drift resistance.

Recommended first event families:
- `city_review_completed`
- `city_review_packet_emitted`
- `city_compact_decision_emitted`
- `city_dispatch_brief_composed`
- `city_pickup_brief_emitted`
- `city_memory_export_emitted`
- `city_session_rebuild_attempted`
- `city_session_rebuild_succeeded`
- `city_observability_row_emitted`
- `city_follow_on_dispatch_created`

These events are enough to prove whether the same judgment survived the downstream path.

## 9. Runtime alignment checks

The first implementation should validate these alignment questions directly from the ledger:
- did the same `compact_decision_id` govern brief, pickup, export, rebuild, and observability writes?
- did `promotion_class` stay constant across mirrored events?
- did `guidance_tone` stay constant across mirrored events?
- did `guidance_placement` stay constant across mirrored events?
- did `copyable_worker_instruction` remain constrained consistently?
- were readiness flags preserved or downgraded explicitly instead of silently changing?

If these cannot be answered from the ledger, the runtime seam is still too implicit.

## 10. Relationship to morning pickup brief

`morning_pickup_brief.json` should become a rendered continuity view of the compact decision object plus current gate state.

That means the pickup brief should not invent new semantics.
It may expand readability, but it should inherit:
- promotion class
- tone
- placement
- safe/not-safe claims
- next smallest proof
- readiness judgments

A good test is simple:
If a pickup brief can contradict the compact decision object without a validation failure, the seam is too loose.

## 11. Relationship to export and Acontext readiness

`city_dispatch_memory_unit.json` should become the retrieval/export view of the same compact decision object.

That export object may add retrieval metadata, but it should not reinterpret the decision.
In practice, export readiness means:
- future retrieval can consume the object without reading the full replay bundle
- the object carries enough provenance to be trustworthy
- cautious versus directive learning is explicit in the object itself

## 12. Relationship to observability

The compact decision object and ledger should feed a deterministic observability row.

That row should preserve:
- `coordination_session_id`
- `review_packet_id`
- `compact_decision_id`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- readiness flags
- `source_episode_count`
- reuse mode / brief composition context

This makes the measurement layer a consumer of the same runtime truth instead of a separate judgment system.

## 13. Relationship to session rebuild

The first restart/rebuild target should read:
- latest compact decision object for a coordination session
- latest pickup brief
- latest relevant ledger lines

Then reconstruct:
- current safe guidance
- current open question
- current next smallest proof
- whether the session is continuity/export/rebuild ready
- whether operator-facing rendering is cautious, directive, held, or suppressed

If rebuild still needs transcript archaeology, the seam is not real yet.

## 14. First implementation checklist

The next build block should not broaden scope until it can produce, for one replay-backed case:
1. `review_packet.json`
2. `city_compact_decision_object.json`
3. `morning_pickup_brief.json` derived from the same decision object
4. `city_dispatch_memory_unit.json` derived from the same decision object
5. `continuity_observability_row.json` derived from the same decision object
6. `city_coordination_ledger.jsonl` lines that mirror the same decision fields across brief/pickup/export/rebuild/observability
7. one rebuild helper that reconstructs state from compact artifacts without transcript dependency

## 15. Hard acceptance gate

Do not call this slice ready unless one replay-backed case proves all of the following together:
- the same compact decision object drives brief rendering, pickup continuity, export, rebuild, and observability
- the append-only coordination ledger preserves the same decision fields across mirrored events
- cautious/directive/held/suppressed semantics do not drift across surfaces
- a restart can recover the next move from compact artifacts plus ledger lines
- observability can query the case without custom interpretation
- export is compact enough for future Acontext ingestion without semantic flattening

## 16. What should wait

Until this slice is proven, avoid spending the next block on:
- broader UI polish
- more template expansion
- generic semantic retrieval work
- deeper Acontext transport work
- abstract cross-vertical cleanup

Those are downstream of the same missing runtime proof.

## 17. Sharp recommendation

**The next daytime implementation should prove one replay-backed city decision can survive as a single compact runtime truth across brief composition, pickup continuity, append-only coordination logging, export, restart, and observability.**

That is the narrowest build slice that turns the current planning corpus into a restart-safe, retrieval-safe, coordination-safe decision-support loop.