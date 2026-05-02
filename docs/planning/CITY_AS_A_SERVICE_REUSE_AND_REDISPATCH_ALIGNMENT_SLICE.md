# City as a Service — Reuse and Redispatch Alignment Slice

> Last updated: 2026-05-02
> Parent docs:
> - `CITY_AS_A_SERVICE_RUNTIME_ALIGNMENT_MATRIX.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CONTINUITY_AND_EXPORT_SEAM.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_MORNING_PICKUP_BRIEF_CONTRACT.md`
> - `CITY_AS_A_SERVICE_COORDINATION_EVENT_CONTRACT.md`
> Status: implementation handoff slice

## 1. Why this doc exists

The current planning seam is strong on replay-time truth:
- reviewed result and packet judgment
- compact decision object derivation
- pickup/export/rebuild alignment
- append-only runtime mirroring

What is still too easy to leave fuzzy is the **reuse moment** itself:
- when a later dispatch or redispatch consumes prior judged learning
- how reuse should preserve promotion/tone/placement semantics
- how the system should record whether memory changed the next action
- how to prevent reuse surfaces from silently upgrading cautious learning into doctrine

This doc defines the narrow daylight slice for that seam.

## 2. Core principle

**Replay proof is incomplete unless the next dispatch can consume the same judged truth without reinterpreting it.**

The first implementation should treat reuse as a first-class proof surface, not a downstream convenience.

That means one replay-backed decision should drive, without semantic drift:
- operator-facing dispatch brief sections
- copyable worker instruction eligibility
- redispatch fallback guidance
- memory-reuse observability
- coordination ledger reuse events

## 3. The exact gap this slice closes

The planning docs already say what should be true at replay time.
The remaining daylight ambiguity is what should happen when that truth is reused.

Without this slice, daytime could still misbuild the system by:
- reading `city_compact_decision_object.json` in one surface but free-styling redispatch logic elsewhere
- logging that memory was "shown" without proving it changed routing or instructions
- letting cautious or inspect-only learning leak into top-line worker instructions
- producing observability rows that know a brief existed but not whether reuse followed the judged trust posture

## 4. Canonical reuse moments

The first implementation should recognize only these reuse moments:
1. initial dispatch brief composition for a new task with prior office/workflow memory
2. redispatch or reroute after a redirect/rejection signal
3. operator review of prior memory before sending worker follow-up instructions
4. session rebuild that prepares the next active dispatch step

If a new consumer does not fit one of these moments, it should wait.

## 5. Reuse-time shared truth

Reuse should start from the same compact runtime truth already defined for replay continuity.

Recommended minimum reused field set:
- `compact_decision_id`
- `coordination_session_id`
- `review_packet_id`
- `summary_judgment`
- `learning_strength`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`
- `top_guidance[]`
- `open_questions[]`
- `continuity_ready`
- `export_ready`
- `operator_surface_ready`
- provenance refs

Reuse surfaces may compress these fields, but must not reinterpret their trust class.

## 6. Reuse consumer matrix

| Reuse consumer | Required inputs | Must preserve exactly | Allowed derived fields | Must emit event |
|---|---|---|---|---|
| Initial dispatch brief composer | compact decision object + retrieval context | `promotion_class`, `guidance_tone`, `guidance_placement`, `copyable_worker_instruction`, `safe_to_claim`, `not_safe_to_claim` | office/task phrasing, section grouping, fallback ordering | `city_dispatch_context_reused` |
| Redispatch fallback composer | compact decision object + current failure signal | `guidance_tone`, `guidance_placement`, `copyable_worker_instruction`, `top_guidance`, `open_questions` | reroute summary, verify-now prompts, escalation hint | `city_redispatch_context_reused` |
| Worker-instruction block builder | compact decision object + selected brief sections | `copyable_worker_instruction`, `guidance_placement`, `not_safe_to_claim` | instruction formatting only | `city_worker_instruction_block_built` |
| Reuse observability row writer | compact decision object + action outcome | reuse identity fields, promotion/tone/placement, reuse mode, behavior-change judgment | lift tags, reuse cohort tags | `city_reuse_observability_row_emitted` |
| Reuse ledger writer | consumer event context + compact decision fields | mirrored decision fields chosen for ledger schema | event-local payload only | event being mirrored |

## 7. Reuse behavior rules

### 7.1 Initial dispatch brief composer
Rules:
- `directive` guidance may shape top-line routing or fallback instructions
- `cautious` guidance must stay verify-first and should not appear as settled office doctrine
- `inspect_only` guidance may inform operator inspection surfaces but not default worker instructions
- `suppressed` guidance must not be injected into the default brief path

### 7.2 Redispatch fallback composer
Rules:
- redispatch may become more concrete than first-dispatch only if the reused compact decision already permits that trust posture
- current-task failure signals may narrow urgency, but may not upgrade promotion class on their own
- `open_questions[]` should remain visible when redispatch still depends on on-site confirmation

### 7.3 Worker-instruction block builder
Rules:
- if `copyable_worker_instruction=false`, rendered guidance may be visible to the operator but not marked copyable for worker handoff
- `not_safe_to_claim[]` must constrain which lines are excluded, not merely styled softer
- inspect-only guidance must never enter the copyable block through fallback grouping logic

### 7.4 Reuse observability row writer
Rules:
- observability must record whether memory was merely displayed or materially used
- the first useful behavior-change classes should be:
  - `shown_only`
  - `routing_changed`
  - `instruction_changed`
  - `evidence_guidance_changed`
  - `redispatch_changed`
  - `escalation_changed`
- it must preserve the promotion/tone/placement class that governed the reused guidance

## 8. Reuse event expectations

The first slice should mirror at least these events:
- `city_dispatch_context_reused`
- `city_redispatch_context_reused`
- `city_worker_instruction_block_built`
- `city_reuse_observability_row_emitted`

Recommended required payload fields for reuse events:
- `coordination_session_id`
- `task_id`
- `compact_decision_id`
- `review_packet_id`
- `reuse_mode` (`dispatch`, `redispatch`, `instruction_build`, `resume`)
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- `behavior_change_class`
- `reused_guidance_ids[]` or equivalent refs
- `notes[]` only when needed

## 9. Reuse-specific alignment checks

The first implementation should fail loudly on at least these conditions.

### 9.1 Trust upgrade drift
Fail if reuse renders directive worker guidance when the compact decision object says `cautious`, `inspect_only`, or `suppressed`.

### 9.2 Copyability drift
Fail if the reuse flow marks guidance copyable after a replay decision set `copyable_worker_instruction=false`.

### 9.3 Anti-overclaim drift
Fail if `not_safe_to_claim[]` disappears from redispatch or worker-instruction filtering without replacement exclusion logic.

### 9.4 Reuse-proof vagueness
Fail if the system records memory reuse without recording whether dispatch behavior actually changed.

### 9.5 Provenance drift
Fail if a reuse row cannot link back to both `compact_decision_id` and `review_packet_id`.

## 10. First useful behavior-change test

One replay-backed case should be able to prove all of the following together:
1. a prior redirect/rejection packet exists
2. a later task retrieves the compact decision object
3. the dispatch brief changes because of reused guidance
4. the changed section respects the original promotion/tone/placement class
5. worker-copyable text is included only if the compact decision permits it
6. a reuse event records what changed
7. an observability row can distinguish `shown_only` from `routing_changed` or `instruction_changed`

If the system cannot prove that chain, it is still remembering artifacts, not compounding execution quality.

## 11. Recommended implementation order

### Step 1
Extend the compact decision helper so reuse consumers read the same normalized runtime view as replay consumers.

### Step 2
Implement initial dispatch and redispatch brief composition from that shared view.

### Step 3
Add explicit worker-instruction filtering based on placement and copyability.

### Step 4
Mirror reuse events into the coordination ledger with behavior-change classes.

### Step 5
Emit one reuse observability row per material reuse moment.

## 12. Acceptance gate

Do not call the replay/continuity seam complete until one replay-backed case also proves reuse alignment:
- initial dispatch reuse preserves trust posture
- redispatch reuse preserves trust posture
- worker-copyable output respects packet-derived copyability
- reuse events mirror the same decision fields as replay events
- observability can query whether memory changed routing, instructions, or nothing
- no consumer upgrades cautious learning into doctrine silently

## 13. Sharp recommendation

**The next daytime proof after compact decision/runtime alignment should be reuse alignment: the same judged city truth should survive not only review and pickup, but the next actual dispatch decision.**

That is the point where City as a Service stops being a clean replay archive and starts becoming operational learning.