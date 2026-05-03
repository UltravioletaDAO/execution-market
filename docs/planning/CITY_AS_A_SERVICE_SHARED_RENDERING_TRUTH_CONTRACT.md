# City as a Service — Shared Rendering Truth Contract

> Last updated: 2026-05-03
> Parent docs:
> - `CITY_AS_A_SERVICE_REVIEW_PACKET_PROMOTION_POLICY.md`
> - `CITY_AS_A_SERVICE_OPERATOR_GUIDANCE_TONE_AND_PLACEMENT_POLICY.md`
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_REPLAY_REVIEW_PACKET_CONTRACT.md`
> - `CITY_AS_A_SERVICE_MORNING_PICKUP_BRIEF_CONTRACT.md`
> Status: implementation handoff companion

## 1. Why this doc exists

The planning stack now defines the hard parts of judgment clearly:
- replay bundles prove whether learning improved the next dispatch
- `review_packet` compresses that proof into one compact decision object
- promotion policy decides whether learning should shape future dispatch
- tone and placement policy defines how that learning should sound to operators
- the runtime alignment matrix says every consumer should mirror the same semantics rather than re-derive them

What is still too easy to misbuild is the final runtime handoff seam.
The docs currently imply that Review Console, Dispatch Brief Panel, Office Memory View, pickup continuity, memory export, and observability should stay aligned.
But they do not yet define the **single normalized rendering object** those consumers should share.

Without that object, daytime could still build five surfaces that all “follow the docs” while drifting in small but dangerous ways:
- one surface treats cautious learning as top-line doctrine
- another keeps it secondary
- one surface lets inspect-only guidance leak into copyable worker instructions
- another suppresses it entirely
- one pickup summary forgets the same anti-overclaim warning the brief preserved

This doc closes that gap.

The goal is simple:

> every city replay judgment that reaches runtime should be projected into one shared rendering truth that all downstream consumers mirror or explicitly downgrade.

## 2. Core principle

**Promotion policy decides eligibility. Shared rendering truth decides runtime expression.**

That expression should be computed once from reviewed truth, then reused everywhere.
Consumers may format differently, but they should not reinterpret:
- how strong the guidance is
- where it belongs
- whether it is copyable into worker instructions
- whether it belongs in pickup continuity or inspection-only memory
- which anti-overclaim boundaries must remain visible

## 3. What this contract is for

The first implementation should use shared rendering truth for all of these consumers:
1. Dispatch Brief composer
2. Review Console preview
3. Office Memory View grouping
4. Morning Pickup Brief writer
5. Session rebuild helper
6. Memory export writer
7. Observability row writer
8. Coordination ledger event payload mirroring

The point is not that every consumer renders identical text.
The point is that they all consume the same normalized runtime decision.

## 4. Source-of-truth order

The shared rendering truth should be derived in this order:
1. `review_packet`
2. compact decision object fields when present
3. promotion policy mapping
4. tone/placement policy mapping
5. explicit downgrade notes if a consumer cannot honor the full rendering truth

No consumer should infer rendering class from freeform notes alone if packet-level fields already exist.

## 5. Required normalized fields

The first-pass shared rendering truth should include at least:
- `compact_decision_id`
- `review_packet_id`
- `coordination_session_id`
- `workflow_template`
- `office_key`
- `summary_judgment`
- `learning_strength`
- `memory_promotion_decision`
- `guidance_mode`
- `target_section_family`
- `copyable_worker_instruction_eligibility`
- `pickup_brief_observation_class`
- `operator_surface_ready`
- `continuity_ready`
- `export_ready`
- `session_rebuild_ready`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `top_guidance[]`
- `top_open_questions[]`
- `main_improvement[]`
- `main_concern[]`
- `provenance_refs`
- `downgrade_notes[]`

Recommended additional fields:
- `freshness_date`
- `guidance_placement_label`
- `rendering_rationale[]`

## 6. Canonical object shape

```json
{
  "compact_decision_id": "cdo_city_packet_submission_20260503_001",
  "review_packet_id": "rp_city_packet_submission_20260503_001",
  "coordination_session_id": "city_packet_submission_miami_dade_20260503_001",
  "workflow_template": "packet_submission",
  "office_key": "miami_building_dept_window_b",
  "summary_judgment": "pass",
  "learning_strength": "moderate",
  "memory_promotion_decision": "promote_cautiously",
  "guidance_mode": "cautious",
  "target_section_family": "secondary_caution",
  "copyable_worker_instruction_eligibility": false,
  "pickup_brief_observation_class": "verify_first",
  "operator_surface_ready": true,
  "continuity_ready": true,
  "export_ready": true,
  "session_rebuild_ready": true,
  "safe_to_claim": [
    "recent reviewed episodes suggest packet-submission intake often redirects to Window B first"
  ],
  "not_safe_to_claim": [
    "Window B is always the correct first stop"
  ],
  "top_guidance": [
    "Likely first stop: Window B. Verify renewal routing before committing to the queue."
  ],
  "top_open_questions": [
    "Confirm whether the Window B redirect still holds for morning intake this week."
  ],
  "main_improvement": [
    "dispatch guidance now surfaces a likely redirect path before travel"
  ],
  "main_concern": [
    "pattern is useful but still supported by limited repeat evidence"
  ],
  "provenance_refs": {
    "review_packet": "review_packet.json",
    "reviewed_episode": "reviewed_episode.json",
    "office_playbook_delta": "office_playbook_delta.json"
  },
  "downgrade_notes": [],
  "rendering_rationale": [
    "promotion policy allows reuse but not top-line doctrine",
    "copyable worker text stays off because the pattern remains verify-first"
  ]
}
```

## 7. Canonical field mappings

### 7.1 Promotion to guidance mode
| `memory_promotion_decision` | `guidance_mode` |
|---|---|
| `promote_with_confidence` | `directive` |
| `promote_cautiously` | `cautious` |
| `hold_for_more_evidence` | `inspect_only` |
| `do_not_promote` | `suppressed` |

This mapping should never be reimplemented ad hoc by downstream consumers.

### 7.2 Guidance mode to target section family
| `guidance_mode` | `target_section_family` |
|---|---|
| `directive` | `top_line_doctrine` |
| `cautious` | `secondary_caution` |
| `inspect_only` | `inspection_only` |
| `suppressed` | `hidden_default` |

### 7.3 Guidance mode to copyability
| `guidance_mode` | `copyable_worker_instruction_eligibility` |
|---|---|
| `directive` | `true` |
| `cautious` | `false` |
| `inspect_only` | `false` |
| `suppressed` | `false` |

The first implementation should keep this conservative.
If later evidence justifies some cautious guidance becoming copyable, that should be an explicit policy change, not silent drift.

### 7.4 Guidance mode to pickup continuity class
| `guidance_mode` | `pickup_brief_observation_class` |
|---|---|
| `directive` | `action_now` |
| `cautious` | `verify_first` |
| `inspect_only` | `inspect_only` |
| `suppressed` | `omit_default` |

## 8. Consumer obligations

### 8.1 Dispatch Brief composer
Must preserve exactly:
- `guidance_mode`
- `target_section_family`
- `copyable_worker_instruction_eligibility`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `top_guidance[]`

Allowed freedom:
- formatting bullets
- section labels
- microcopy polish

Not allowed:
- turning `cautious` into top-line directive language
- copying `inspect_only` guidance into worker text
- dropping `not_safe_to_claim[]` without replacement warnings

### 8.2 Review Console preview
Must show:
- the predicted `guidance_mode`
- predicted `target_section_family`
- copyability result
- one-line rendering preview

The preview should help the reviewer see the future operator-facing consequence of the current promotion decision.

### 8.3 Office Memory View
Must group by:
- `directive` -> Active dispatch rules
- `cautious` -> Cautionary patterns
- `inspect_only` -> Held observations
- `suppressed` -> Blocked/suppressed history

### 8.4 Morning Pickup Brief writer
Must preserve:
- the difference between `action_now`, `verify_first`, `inspect_only`, and `omit_default`
- all active `not_safe_to_claim[]` warnings relevant to continuity

The pickup brief may summarize, but it must not strengthen the guidance class.

### 8.5 Session rebuild helper
Must recover:
- current `guidance_mode`
- current `target_section_family`
- `top_guidance[]`
- `top_open_questions[]`
- readiness flags

If those cannot be reconstructed from compact artifacts plus ledger tail, rebuild should fail loudly.

### 8.6 Memory export writer
Must export the same rendering truth fields so future Acontext or retrieval sinks inherit reviewed meaning rather than recomputing it.

### 8.7 Observability row writer
Must record:
- `memory_promotion_decision`
- `guidance_mode`
- `target_section_family`
- copyability
- readiness flags

Observability should measure how the system rendered the learning, not guess later.

### 8.8 Coordination ledger writer
Every consumer event mirrored into the ledger should preserve the same shared field subset so drift becomes queryable.

## 9. Downgrade rules

If a consumer cannot honor the full shared rendering truth, it must:
1. preserve the original fields in provenance
2. emit a `downgrade_notes[]` entry
3. write a ledger event exposing the downgrade

Typical downgrade examples:
- pickup brief omits secondary provenance details for compactness
- export sink cannot yet store one optional rendering label
- rebuild summary compresses multiple cautious notes into one grouped caution line

Non-acceptable downgrade behavior:
- silent strengthening of guidance tone
- silent top-line placement of inspect-only learning
- silent conversion of non-copyable guidance into worker-copyable text

## 10. Alignment checks that should fail loudly

### 10.1 Tone drift check
Fail if a consumer renders `guidance_mode=cautious` as directive language.

### 10.2 Placement drift check
Fail if `target_section_family=inspection_only` appears in top-line dispatch doctrine.

### 10.3 Copyability drift check
Fail if `copyable_worker_instruction_eligibility=false` but the worker instruction block includes the learning as copyable operational text.

### 10.4 Pickup drift check
Fail if pickup output upgrades `verify_first` or `inspect_only` into `action_now` style wording.

### 10.5 Anti-overclaim drop check
Fail if `not_safe_to_claim[]` disappears from brief, pickup, or rebuild outputs without explicit replacement warnings.

### 10.6 Export drift check
Fail if exported memory units omit `guidance_mode` or `memory_promotion_decision`, forcing future retrieval sinks to infer them again.

## 11. Recommended implementation order

### Step 1
Implement one helper that converts `review_packet` plus compact decision fields into shared rendering truth.

### Step 2
Have Dispatch Brief composer, Review Console preview, and Office Memory View consume that helper first.

### Step 3
Extend the same helper to pickup continuity, rebuild, export, and observability.

### Step 4
Mirror shared rendering truth into coordination ledger events.

### Step 5
Add fixture-backed drift tests for tone, placement, copyability, and anti-overclaim preservation.

## 12. Acceptance gate for this companion slice

Do not call the City-as-a-Service rendering seam aligned until one replay-backed case proves all of the following:
- one `review_packet` becomes one shared rendering truth object
- Dispatch Brief, Review Console preview, Office Memory View, and pickup continuity all consume that same object
- copyability stays conservative and consistent across surfaces
- one induced downgrade is recorded explicitly rather than mutating meaning silently
- rebuild and export can preserve guidance class without rereading full replay bundles

## 13. Sharp recommendation

**Implement one shared rendering truth helper before adding more city-ops UI surfaces.**

That is the cleanest way to keep reviewed confidence, promotion safety, and operator expression aligned as the City-as-a-Service stack moves from planning into daytime code.