# City as a Service — Daytime Continuity and Export Seam

> Last updated: 2026-05-02
> Parent docs:
> - `CITY_AS_A_SERVICE_IMPLEMENTATION_BACKLOG_AND_DECISIONS.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md`
> - `CITY_AS_A_SERVICE_COORDINATION_EVENT_CONTRACT.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> Status: implementation handoff slice

## 1. Why this doc exists

The planning stack is already strong on:
- reviewed result and memory contracts
- replay bundles and review discipline
- `review_packet` promotion policy
- Acontext-ready export objects
- operator-facing tone and placement rules

What is still too easy to misbuild is the seam between three specific consumers of the same reviewed truth:
1. the next active operator/session block
2. the compact export object for future Acontext retrieval
3. observability and replay review surfaces

That seam needs to be explicit because daytime work can otherwise drift into a bad pattern:
- replay bundles say one thing
- `morning_pickup_brief.json` says another
- Acontext export units require extra interpretation
- observability sees generic lifecycle events but not the same decision truth

This doc defines the narrowest continuity-and-export seam that keeps those consumers aligned.

## 2. Core principle

**One reviewed decision should drive continuity, retrieval export, and observability without semantic drift.**

The reviewed truth should not be restated by hand in three different formats.
The system should derive them from the same compact decision object and rendering policy.

The seam should preserve, at minimum:
- `summary_judgment`
- `learning_strength`
- `memory_promotion_decision`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- `replay_readiness_judgment`
- provenance refs

## 3. The three continuity consumers

### 3.1 Pickup continuity object
This is the shortest restart-safe handoff for the next work block.
Its job is to answer:
- what was proven?
- what is safe to claim?
- what remains partial?
- what is the next smallest proof?

### 3.2 Retrieval export unit
This is the compact object future Acontext retrieval should consume.
Its job is to answer:
- what learned guidance is reusable now?
- how strongly?
- how should it sound and where should it appear?
- what source episodes justify it?

### 3.3 Observability row / event summary
This is the measurement and review surface.
Its job is to answer:
- which replay-backed decision path completed?
- what judgment did it end with?
- was the result continuity-ready and export-ready?

## 4. Shared continuity truth

The first implementation should treat `review_packet` as the source decision object, but not the only runtime artifact.
A small derived continuity truth should be emitted beside it and reused consistently.

Recommended minimum shared fields:
```json
{
  "review_packet_id": "rp_2026_05_02_001",
  "coordination_session_id": "city_packet_submission_2026_05_02_001",
  "summary_judgment": "pass",
  "learning_strength": "moderate",
  "memory_promotion_decision": "promote_cautiously",
  "guidance_tone": "cautious",
  "guidance_placement": "secondary_caution",
  "copyable_worker_instruction": false,
  "replay_readiness_judgment": "pass",
  "main_improvement": [
    "warns operators to verify Window B redirect before full queue commitment"
  ],
  "main_concern": [
    "redirect pattern still needs one more aligned reviewed episode before directive promotion"
  ]
}
```

This object should not replace the packet.
It should compress the packet into the exact state that continuity, export, and observability need to share.

## 5. First required derived artifacts

### 5.1 `morning_pickup_brief.json`
This should be the continuity artifact for the next engineering block or operator session.
It should be derived from replay truth, not written from scratch.

Minimum fields:
- `summary_judgment`
- `learning_strength`
- `replay_readiness_judgment`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`
- `guidance_tone_alignment`
- `guidance_placement_alignment`
- refs to packet, manifest, scorecard, improved brief

### 5.2 `city_dispatch_memory_unit.json`
This should be the compact retrieval export object.
It should be safe for future Acontext ingestion without requiring bundle re-interpretation.

Minimum fields:
- `review_packet_id`
- `coordination_session_id`
- `workflow_template`
- `jurisdiction_name`
- `office_name`
- `summary_judgment`
- `learning_strength`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- `replay_readiness_judgment`
- `top_guidance[]`
- `open_questions[]`
- `source_episode_ids[]`
- `event_summary_id`
- `freshness_date`

### 5.3 `continuity_observability_row.json`
This should be the compact measurement row for replay-backed continuity readiness.

Minimum fields:
- `coordination_session_id`
- `review_packet_id`
- `summary_judgment`
- `learning_strength`
- `memory_promotion_decision`
- `guidance_tone`
- `guidance_placement`
- `replay_readiness_judgment`
- `continuity_ready`
- `export_ready`
- `brief_improvement_visible`

## 6. Continuity derivation rules

### 6.1 Do not restate judgment manually
The first rule is discipline, not format:
- continuity artifacts should derive from packet + manifest + scorecard truth
- they should not re-judge the replay independently
- they may compress, but they should not reinterpret

### 6.2 Continuity truth follows promotion policy
If `memory_promotion_decision` is:
- `promote_with_confidence` -> continuity may mark guidance as ready for directive carry-forward
- `promote_cautiously` -> continuity must preserve verify-first framing
- `hold_for_more_evidence` -> continuity may surface inspectable learning but must not present it as default doctrine
- `do_not_promote` -> continuity must keep the learning out of default dispatch carry-forward

### 6.3 Continuity truth follows rendering policy
The same judgment must determine:
- brief tone
- brief placement
- whether instruction text is copyable into worker-facing instructions
- whether pickup briefing may say the seam is ready for broader UI wiring

## 7. Restart and session rebuild requirement

The continuity seam is not real unless a new work block can recover state from compact artifacts without transcript dependency.

The first rebuild target should answer:
- what replay-backed case was last proven?
- what did it prove?
- what is the next smallest proof?
- what guidance is safe to reuse now?
- what guidance is only inspectable?

Minimum rebuild inputs:
- `review_packet.json`
- `bundle_manifest.json`
- `event_summary.json`
- `morning_pickup_brief.json`
- `city_dispatch_memory_unit.json`

If a restart still requires rereading the whole bundle to recover the next step, the seam is not compressed enough yet.

## 8. Observability requirement

The same continuity seam should be queryable without custom interpretation.

Recommended first observability questions:
- how often do replay-backed cases end `continuity_ready=true`?
- how often do they end `export_ready=true`?
- how often does `promote_cautiously` later upgrade to `promote_with_confidence`?
- how often is `brief_improvement_visible=true` while `continuity_ready=false`?
- how often do rendering-alignment checks fail even when contracts pass?

This matters because the team should be able to distinguish:
- technically valid replay bundles
- continuity-ready judgments
- export-ready retrieval units

## 9. First implementation checklist

Daytime should not broaden scope until it can produce all of these from one replay-backed case:
1. valid `review_packet.json`
2. valid `bundle_manifest.json`
3. valid `event_summary.json`
4. derived `morning_pickup_brief.json`
5. derived `city_dispatch_memory_unit.json`
6. derived `continuity_observability_row.json`
7. deterministic alignment across judgment, tone, placement, and readiness

## 10. Hard acceptance gate

Do not call the continuity-and-export seam ready unless one replay-backed case proves all of the following together:
- `review_packet` promotion stance matches the improved brief tone
- `review_packet` promotion stance matches the improved brief placement
- pickup brief preserves the same truth without manual reinterpretation
- export unit is retrieval-ready without reading the whole replay bundle
- observability row can report the same case by `coordination_session_id` and `review_packet_id`
- restart/rebuild can recover the next action from compact artifacts alone

## 11. What should wait

Until this seam is proven, avoid spending the next daytime block on:
- broader dashboard polish
- more city templates
- generalized semantic retrieval
- richer Acontext plumbing
- more abstract cross-vertical cleanup

Those are downstream of the same missing proof.

## 12. Sharp recommendation

**The next engineering move should be to prove that one reviewed city decision can survive replay review, morning pickup, retrieval export, and session rebuild without changing meaning.**

That is the narrowest seam that makes the broader CaaS memory loop trustworthy.