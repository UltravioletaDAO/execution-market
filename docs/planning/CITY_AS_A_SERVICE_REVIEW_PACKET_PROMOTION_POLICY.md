# City as a Service — Review Packet Promotion Policy

> Last updated: 2026-04-29
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_REPLAY_REVIEW_PACKET_CONTRACT.md`
> - `CITY_AS_A_SERVICE_REPLAY_REVIEW_DISCIPLINE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_BUILD_SPEC.md`
> - `CITY_AS_A_SERVICE_IMPLEMENTATION_BACKLOG_AND_DECISIONS.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The planning stack now defines:
- the replay bundle artifact chain
- manifest acceptance checks
- compact event summaries
- learning-strength classification
- the final `review_packet` decision object

That is enough to tell whether one replay bundle looks good.
What is still not explicit enough is **how that judgment should control memory promotion behavior**.

Without a promotion policy, daytime code could still drift into unsafe or inconsistent behavior:
- treating every `pass` as equally reusable
- promoting office-memory guidance too aggressively from one narrow episode
- letting `review_packet` exist without actually governing dispatch reuse
- making future Acontext sinks ingest decision objects without a clear safety stance

This doc defines the smallest policy seam between replay judgment and reusable city memory.

The goal is simple:

> make `review_packet` the explicit gate for whether learned municipal guidance should be promoted, softened, held, or blocked before it influences future dispatch.

## 2. Core principle

**A replay proof archive explains what happened. The review packet promotion policy decides how strongly the system is allowed to reuse it.**

That distinction matters because:
- `summary_judgment` answers whether the replay proof cleared review
- `learning_strength` answers how valuable the learning appears to be
- `memory_promotion_decision` must answer what future dispatch is actually allowed to do with that learning

The first implementation should keep this policy:
- conservative
- explicit
- reviewable in PRs
- portable to local-file and future Acontext sinks

It should not rely on:
- hidden scoring formulas
- transcript re-interpretation at dispatch time
- implicit promotion from artifact presence alone
- optimistic assumptions that every office pattern is stable after one run

## 3. Policy question this doc answers

For every replay bundle that emits a valid `review_packet`, the system should be able to answer:
- should this learning affect future dispatch now?
- if yes, how strongly?
- should the learning appear as hard guidance, soft caution, or inspectable note only?
- what should be withheld until more evidence arrives?

If the system cannot answer those questions from the packet plus this policy, the first city-ops memory seam is still too ambiguous.

## 4. Canonical promotion outcomes

The first implementation should treat `memory_promotion_decision` as the authoritative policy field.

Recommended values:
- `promote_with_confidence`
- `promote_cautiously`
- `hold_for_more_evidence`
- `do_not_promote`

These should govern what later dispatch retrieval is allowed to surface.

## 5. Meaning of each promotion decision

### 5.1 `promote_with_confidence`

Use when:
- `summary_judgment = pass`
- `judgment_alignment = true`
- learning is at least `moderate`
- the main improvement is behavioral and office-specific
- provenance is clean and inspectable
- the replay suggests guidance that should actively shape the next dispatch

Effect on future dispatch:
- guidance may appear as first-class brief content
- guidance may influence fallback recommendation directly
- guidance may be used in concise operator-facing warnings without extra softening language

Typical examples:
- repeated rejection due to outdated packet form now becomes a pre-dispatch verification rule
- stable redirect pattern now becomes the default routing hint for that office/template pair
- evidence restriction repeatedly observed and now changes what proof the worker is told to seek

### 5.2 `promote_cautiously`

Use when:
- `summary_judgment = pass` or a strong `partial`
- learning is real but still narrow, fresh, or based on limited repeat evidence
- the brief should surface the guidance, but not as hard doctrine
- reviewers agree the guidance is useful, but still want visible caution at dispatch time

Effect on future dispatch:
- guidance may appear in the dispatch brief as a caution or likely pattern
- language should preserve uncertainty, for example `often`, `recently`, or `verify before assuming`
- retrieval may surface provenance/freshness markers more prominently

Typical examples:
- one office-specific redirect seems real, but only one reviewed episode supports it
- one new rejection reason is operationally useful, but repeat confirmation is still missing
- one mixed-source office rule is helpful enough to show, but not yet strong enough to harden fully

### 5.3 `hold_for_more_evidence`

Use when:
- replay artifacts are valid and reviewable
- learning is weak or bounded
- the guidance may be worth preserving for inspection, but should not actively steer default dispatch yet
- the reviewer wants another confirming episode, stronger provenance, or broader office stability first

Effect on future dispatch:
- do not surface as top-line office doctrine
- may remain available in debug/admin/memory-inspection views
- may appear only as low-priority note material, if surfaced at all

Typical examples:
- wording improved but worker behavior would probably not change much
- a new office pattern is plausible but derived from one ambiguous or mixed-confidence episode
- a playbook delta exists, but the scorecard improvement is too narrow to justify reuse pressure

### 5.4 `do_not_promote`

Use when:
- `summary_judgment = fail`, or
- the bundle is technically present but not operationally trustworthy, or
- the reviewer sees serious provenance, confidence, or overclaim problems

Effect on future dispatch:
- no guidance from this replay should shape live dispatch defaults
- artifacts may remain in the archive for debugging, but should not influence operator-facing brief content

Typical examples:
- manifest says `partial` but the scorecard improvement is cosmetic
- learning-strength claim overstates what one episode proves
- provenance is too weak to justify reuse
- contradictory signals were collapsed into premature office doctrine

## 6. Promotion policy by judgment combination

The first implementation should keep a simple review-friendly matrix.

### 6.1 Strong default matrix

| summary_judgment | learning_strength | likely promotion outcome |
|---|---|---|
| `pass` | `strong` | `promote_with_confidence` |
| `pass` | `moderate` | `promote_with_confidence` or `promote_cautiously` |
| `pass` | `weak` | `promote_cautiously` or `hold_for_more_evidence` |
| `partial` | `moderate` | `promote_cautiously` or `hold_for_more_evidence` |
| `partial` | `weak` | `hold_for_more_evidence` |
| `fail` | any / `none` | `do_not_promote` |

This matrix is guidance, not a hidden hardcoded formula.
The packet rationale should still explain the exact choice.

### 6.2 Judgment-alignment override

If `judgment_alignment = false`, the policy should become more conservative.

Practical rule:
- never escalate to `promote_with_confidence` when alignment is false
- prefer `promote_cautiously` or `hold_for_more_evidence`
- if the misalignment comes from provenance weakness or cosmetic scorecard gains, prefer `do_not_promote`

## 7. Retrieval behavior by promotion outcome

The first implementation should let promotion policy shape how the dispatch brief is composed.

### 7.1 When promoted with confidence
- include the learned rule in the main brief summary or top risk list
- allow it to influence recommended fallback behavior directly
- allow it to contribute to office playbook summary fields without hedging overload

### 7.2 When promoted cautiously
- include the learned rule, but mark it as recent, likely, or verify-first guidance
- prefer it in evidence guidance, caution notes, or fallback hints rather than as rigid doctrine
- preserve provenance and freshness markers clearly

### 7.3 When held for more evidence
- keep the learning out of top-line brief summary fields
- make it inspectable in memory/admin/debug surfaces
- optionally surface it only in low-priority notes where the UI can show it as unconfirmed

### 7.4 When not promoted
- exclude it from operator-facing dispatch doctrine
- preserve only for audit/debug purposes

## 8. Promotion safety rules

The first pass should protect against memory pollution with a few hard rules.

### 8.1 No promotion from raw uploads
No `review_packet` means no promotion policy decision.
No promotion policy decision means no live dispatch influence.

### 8.2 No hard doctrine from weak hearsay
Even if a replay bundle is reviewable, weak hearsay-only or mixed-confidence claims should not become strong routing doctrine without explicit packet support.

### 8.3 No confidence inflation from verbosity
Longer rationale or larger bundles do not justify stronger promotion by themselves.
Promotion should follow behavioral evidence, not documentation mass.

### 8.4 Provenance must survive promotion
If dispatch surfaces a learned rule, operators should still be able to trace it back to:
- the `review_packet`
- the `reviewed_episode`
- the office playbook delta

### 8.5 Promotion is reversible
The first implementation should treat office-memory guidance as revisable.
Later contradictory episodes should be able to downgrade future promotion stance rather than forcing permanent doctrine.

## 9. Recommended packet fields that should drive policy

The first implementation should consult these packet fields together:
- `summary_judgment`
- `learning_strength`
- `review_decision`
- `memory_promotion_decision`
- `judgment_alignment`
- `main_improvement`
- `main_concern`
- `rationale`

The policy should not require re-reading raw artifacts to make a promotion choice in ordinary cases.
That is the entire point of the packet.

## 10. Example policy outcomes

### 10.1 Repeated outdated form rejection
- `summary_judgment: pass`
- `learning_strength: strong`
- `review_decision: approve`
- `memory_promotion_decision: promote_with_confidence`

Expected dispatch effect:
- future packet-submission briefs tell operators/workers to verify current form revision before travel
- the rule appears in top rejection reasons and fallback behavior

### 10.2 Single redirect to Window B
- `summary_judgment: pass`
- `learning_strength: moderate`
- `review_decision: approve_with_caution`
- `memory_promotion_decision: promote_cautiously`

Expected dispatch effect:
- future briefs mention Window B as a likely redirect path
- wording preserves that the pattern may still need confirmation

### 10.3 Ambiguous office-photo restriction
- `summary_judgment: partial`
- `learning_strength: weak`
- `review_decision: needs_tightening`
- `memory_promotion_decision: hold_for_more_evidence`

Expected dispatch effect:
- the information remains inspectable in admin/debug memory views
- it does not become top-line brief doctrine yet

### 10.4 Cosmetic brief cleanup only
- `summary_judgment: partial`
- `learning_strength: weak`
- `review_decision: block`
- `memory_promotion_decision: do_not_promote`

Expected dispatch effect:
- no live guidance change
- bundle remains useful only for debugging and scoring refinement

## 11. Daytime implementation implication

The narrow next daylight seam is no longer just:
- write `review_packet`

It is:
- write `review_packet`
- apply a deterministic promotion policy from that packet
- let brief composition respect the policy outcome

That gives the first city-ops memory loop a real safety boundary between reviewed proof and live operator doctrine.

## 12. Relationship to future Acontext ingestion

When the transport later moves from local files to Acontext, the promotion policy should remain unchanged.

That means:
- the full replay bundle stays the audit archive
- the `review_packet` stays the compact decision object
- this promotion policy stays the rule for whether and how memory becomes dispatch-visible

Acontext should inherit reviewed meaning, not invent it.

## 13. Sharp recommendation

**Make `review_packet` promotion policy explicit before broader city-ops retrieval or Acontext expansion.**

If the first replay seam cannot say how strongly a reviewed learning should influence future dispatch, it is still generating interesting artifacts rather than safe reusable municipal memory.
