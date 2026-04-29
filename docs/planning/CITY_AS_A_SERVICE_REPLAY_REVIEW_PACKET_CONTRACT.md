# City as a Service — Replay Review Packet Contract

> Last updated: 2026-04-28
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_REPLAY_BUNDLE_SPEC.md`
> - `CITY_AS_A_SERVICE_REPLAY_REVIEW_DISCIPLINE.md`
> - `CITY_AS_A_SERVICE_MANIFEST_ACCEPTANCE_CONTRACT.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The planning stack now defines:
- the replay bundle artifacts
- manifest acceptance checks
- event ordering
- scorecard judgment
- learning-strength classification
- reviewer reading order

That is strong enough for disciplined file review.
What is still not explicit enough is the **single review-safe object** that daylight product work, operator tooling, and a future Acontext sink can all consume without re-deriving judgment from raw bundle files.

This doc defines that object as `review_packet`.

The goal is simple:

> every replay bundle should be compressible into one compact review packet that carries the final judgment, the main improvement, the main concern, and the exact memory-promotion stance.

## 2. Core principle

**The replay bundle is the proof archive. The review packet is the decision object.**

That distinction matters.
A reviewer may need the full bundle for audit, but most downstream consumers should not have to reread ten artifacts just to answer:
- did this replay prove useful learning?
- what changed operationally?
- should the learned office memory influence future dispatch?
- what remains too weak or risky to promote?

The review packet should optimize for:
- compactness
- judgment clarity
- explicit promotion safety
- Acontext-friendly portability
- direct linkage back to canonical artifacts

It should not optimize for:
- replacing the bundle archive
- long narrative prose
- hidden scoring logic
- loosely structured reviewer comments

## 3. What the review packet is for

The first implementation should use `review_packet` for four things:
1. giving operators a compact final review receipt
2. giving daylight PRs one short proof object after the manifest
3. giving the local projector or future Acontext bridge one stable ingestion object
4. deciding whether office-memory changes are safe to reuse at dispatch time

## 4. Required top-level fields

The first-pass `review_packet` should require:
- `fixture_id`
- `workflow_template`
- `office_key`
- `summary_judgment`
- `learning_strength`
- `review_decision`
- `memory_promotion_decision`
- `judgment_alignment`
- `main_improvement`
- `main_concern`
- `artifact_refs`
- `rationale`

Recommended additional fields:
- `generated_at`
- `reviewer_mode`
- `notes`

## 5. Canonical packet shape

```json
{
  "fixture_id": "packet_rejection_outdated_form_v1",
  "workflow_template": "packet_submission",
  "office_key": "miami_building_dept_counter_a",
  "summary_judgment": "pass",
  "learning_strength": "moderate",
  "review_decision": "approve",
  "memory_promotion_decision": "promote_with_confidence",
  "judgment_alignment": true,
  "main_improvement": [
    "dispatch brief now warns about outdated packet form before office visit"
  ],
  "main_concern": [],
  "artifact_refs": {
    "bundle_manifest": "bundle_manifest.json",
    "event_summary": "event_summary.json",
    "brief_improvement_scorecard": "brief_improvement_scorecard.json",
    "improved_dispatch_brief": "improved_dispatch_brief.json",
    "office_playbook_delta": "office_playbook_delta.json",
    "reviewed_episode": "reviewed_episode.json"
  },
  "rationale": [
    "scorecard shows improvement in rejection avoidance",
    "playbook delta adds one reusable office-specific prevention rule",
    "improved brief changes likely worker preparation behavior"
  ]
}
```

## 6. Field semantics

### 6.1 `summary_judgment`
Must mirror the manifest judgment exactly:
- `pass`
- `partial`
- `fail`

The packet must not invent a softer or stronger overall result than the manifest.

### 6.2 `learning_strength`
Should mirror the manifest-level learning-value assessment:
- `weak`
- `moderate`
- `strong`
- optional `none` when `summary_judgment = fail`

### 6.3 `review_decision`
Recommended values:
- `approve`
- `approve_with_caution`
- `needs_tightening`
- `block`

This field answers what a reviewer thinks should happen next, not merely what artifacts exist.

### 6.4 `memory_promotion_decision`
Recommended values:
- `promote_with_confidence`
- `promote_cautiously`
- `hold_for_more_evidence`
- `do_not_promote`

This field is the key bridge between replay proof and reusable office memory.
It keeps downstream systems from treating every valid replay as equally reusable doctrine.

### 6.5 `judgment_alignment`
Boolean.
Use `true` only when:
- the manifest judgment,
- scorecard result,
- review decision,
- and memory promotion stance
all point in the same honest direction.

Examples:
- `pass` + `approve` + `promote_with_confidence` -> likely `true`
- `pass` + `needs_tightening` because provenance is shaky -> `false`

This field helps catch overclaiming in a single glance.

### 6.6 `main_improvement`
A short list of the clearest operational improvements.
Each item should describe a behavior change, not a formatting change.

Good examples:
- `brief now warns to verify current form revision before traveling`
- `redirect expectation now points intake submissions to Window B first`
- `evidence guidance now notes that rejected packets usually get no receipt`

### 6.7 `main_concern`
A short list of the narrowest reasons the replay should be treated cautiously.
If there is no meaningful concern, use an empty list.

Good examples:
- `playbook delta is useful but still derived from one episode`
- `improvement is office-specific but not yet repeated`
- `scorecard improvement is real but limited to one dimension`

### 6.8 `artifact_refs`
Must point back to the canonical bundle artifacts.
This keeps the review packet compact while preserving auditability.
At minimum include refs for:
- `bundle_manifest`
- `event_summary`
- `brief_improvement_scorecard`
- `improved_dispatch_brief`
- `office_playbook_delta`
- `reviewed_episode`

### 6.9 `rationale`
A short bullet list explaining the packet judgment.
This is not a narrative review essay.
Three concise bullets is usually enough.

## 7. Relationship to bundle review order

The review packet should be produced only **after** the reviewer has inspected the canonical fixed order:
1. `bundle_manifest`
2. `event_summary`
3. `brief_improvement_scorecard`
4. `improved_dispatch_brief`
5. `office_playbook_delta`
6. `reviewed_episode`
7. supporting artifacts as needed

The packet is therefore a compression of reviewed truth, not a replacement for review discipline.

## 8. Relationship to Acontext and local projector flows

The review packet is the best first bridge object for memory infrastructure because it is:
- smaller than the bundle
- safer than raw coordination logs
- more decision-rich than a bare manifest
- explicit about memory promotion stance

That means the local-first implementation can:
1. write the full replay bundle
2. write the review packet beside it
3. later swap the packet sink into Acontext without changing product meaning

This keeps Acontext fed with review-safe judgments instead of raw municipal ambiguity.

## 9. Minimum acceptance rules for the review packet

A `review_packet` should be considered valid only if:
- `summary_judgment` matches the manifest
- `learning_strength` matches or honestly narrows the manifest meaning
- `review_decision` is explicit
- `memory_promotion_decision` is explicit
- `main_improvement` contains only behavioral or operational improvements
- `main_concern` is empty or narrowly honest
- all required `artifact_refs` are present
- rationale bullets are short and traceable to reviewed artifacts

## 10. How to use the packet in the first daylight proof

The first daylight replay proof should end with this reading rhythm:
1. manifest answers whether the proof passed
2. review packet answers what the proof means operationally
3. full bundle artifacts answer why

That is a better operator and PR experience than forcing every consumer to jump directly from manifest into all bundle files.

## 11. Sharp recommendation

**Add `review_packet` as the final compact decision object for every replay bundle before broader Acontext or UI expansion.**

If the first CaaS replay seam cannot summarize itself into one review-safe packet, the memory loop is still too raw for broader integration claims.
