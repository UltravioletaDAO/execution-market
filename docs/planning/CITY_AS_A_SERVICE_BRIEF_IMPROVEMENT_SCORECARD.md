# City as a Service — Brief Improvement Scorecard

> Last updated: 2026-04-27
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> - `CITY_AS_A_SERVICE_TYPED_VALIDATORS_AND_FIXTURE_SCHEMA.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The current CaaS planning seam already says daytime should compare a baseline dispatch brief with an improved brief after replayed learning.
What is still easy to fake is the conclusion.
A side-by-side diff alone does not force a judgment about whether the new brief is operationally better.

This doc defines the smallest scorecard that makes the first replay proof harder to hand-wave.

## 2. Core principle

**A dispatch brief is only improved if it helps the next worker avoid a real municipal failure mode more reliably than before.**

Longer is not better.
More confident is not better.
More product language is definitely not better.
The scorecard should reward only improvements that make the next dispatch materially smarter.

## 3. The first scorecard dimensions

The first implementation pass should grade only five dimensions.
That is enough to make the replay seam inspectable without overbuilding evaluation logic.

### 3.1 Routing clarity
Question:
- does the improved brief identify the likely office, window, desk, redirect path, or routing trap more clearly than the baseline?

Good signs:
- names a specific redirect target
- warns that the first destination is often wrong
- distinguishes office scope from department scope

### 3.2 Rejection avoidance
Question:
- does the improved brief help the next worker avoid the same rejection cause that appeared in reviewed history?

Good signs:
- warns about an outdated form version
- highlights a missing required document
- distinguishes accepted versus rejected submission conditions

### 3.3 Fallback usefulness
Question:
- if the worker is blocked, redirected, or refused, does the improved brief provide a more actionable fallback than the baseline?

Good signs:
- says what to ask next
- says where to go next
- says what proof to bring back if the primary path fails

### 3.4 Evidence realism
Question:
- does the improved brief reflect the real evidence/proof constraints of the office more accurately?

Good signs:
- warns that photos are not allowed at the counter
- suggests receipt/stamped-copy fallback proof
- narrows proof expectations to what is actually collectible

### 3.5 Provenance clarity
Question:
- can an operator inspect why the brief says something important?

Good signs:
- important claims point to reviewed episodes or playbook deltas
- low-confidence claims are marked as tentative
- the brief does not read like unsupported doctrine

## 4. First-pass rating scale

Use a tiny categorical scale per dimension:
- `improved`
- `unchanged`
- `worse`

That is enough for the first proof.
Do not start with weighted scoring unless the replay seam already works and the team needs tighter automation.

## 5. Recommended scorecard shape

```json
{
  "fixture_id": "packet_rejection_outdated_form_v1",
  "baseline_brief_id": "dispatch_brief_before",
  "improved_brief_id": "dispatch_brief_after",
  "ratings": {
    "routing_clarity": "unchanged",
    "rejection_avoidance": "improved",
    "fallback_usefulness": "improved",
    "evidence_realism": "unchanged",
    "provenance_clarity": "improved"
  },
  "summary_judgment": "improved",
  "rationale": [
    "brief now warns that packet is rejected when the 2024 form version is used",
    "brief now references the reviewed rejection episode that introduced the warning"
  ]
}
```

## 6. Conservative grading rules

The first scorecard should be intentionally strict.

### 6.1 Do not reward verbosity
If the improved brief says more but helps the worker no more, mark `unchanged`.

### 6.2 Do not reward unsupported certainty
If the improved brief sounds stronger without reviewed provenance, mark `worse` on provenance clarity and consider overall `unchanged` or `worse`.

### 6.3 Prefer actionable specificity
A short instruction like “If Window A rejects the packet, ask whether Window B now handles intake for renewals” is better than a paragraph of generic context.

### 6.4 Penalize drift
If a replay causes guidance wording or rank order to change unpredictably without new evidence, the scorecard should surface that as `worse` or fail the replay gate entirely.

## 7. What should count as a successful first proof

The first replay seam is convincing when a reviewer can inspect one artifact bundle and see:
- the baseline brief
- the reviewed result and reviewed episode that justify learning
- the playbook delta that captures the change
- the improved brief
- the scorecard explaining exactly how the brief got better

If that bundle is not obvious by inspection, the seam is not ready for broader UI claims yet.

## 8. Immediate daytime recommendation

Build the scorecard only after:
1. validators exist for the five core artifacts
2. one rejection fixture and one redirect fixture replay deterministically
3. before/after briefs can be emitted consistently

Then attach this scorecard as the smallest proof that City-as-a-Service learning is operational, not aspirational.
