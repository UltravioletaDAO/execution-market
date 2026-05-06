# City as a Service — Daytime First Proof Case Selection Card

> Last updated: 2026-05-05 07:00 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_PROGRAM_CARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_ANCHOR_FREEZE_CONTRACT.md`
> Status: daytime proof-anchor selection guide

## 1. Why this doc exists

The current planning spine is now very clear about the first shared-decision ladder.
What still remains vulnerable in daylight is the **choice of proof anchor**.

The program card already says to keep one replay-backed case stable across PR A through PR D.
But that still leaves one practical morning risk:
- choosing a case that emits artifacts but cannot justify behavior change
- choosing a case that stresses too many semantic axes at once
- rotating cases mid-ladder because the original one was not strong enough
- picking the “most interesting” case instead of the most reviewable one

This card closes that gap.

> the first daytime proof should begin by choosing one case that is strong enough to expose semantic drift, but narrow enough to remain readable across the whole four-rung ladder.

## 2. The one selection question

Before daytime starts PR A, it should be able to answer:

> if this same case stays active from projection truth through closure packaging, will reviewers be able to tell whether the next dispatch got smarter for the right reason?

If the answer is no, the case is wrong even if it looks realistic.

## 3. Best default case shape

Choose a case with all of these properties:
- **reviewed redirect or rejection** rather than clean acceptance
- **plausible next-dispatch behavior change** rather than artifact-only learning
- **clear trust posture** that can be preserved or drifted visibly
- **compact enough evidence** to inspect without transcript dependence
- **stable office context** so office-memory outputs remain legible across runs

Recommended default:
- one redirect case where the reviewed result should materially change office routing, fallback instructions, or evidence guidance on the next dispatch

Why this is the best default:
- it naturally tests `shown_only` versus real reuse
- it exposes trust inflation quickly
- it makes scoreboards and pickup packaging easier to judge
- it is more operationally meaningful than a clean success case

## 4. Case qualities that are strong enough

A first proof-anchor case is strong when it can support all four rungs:

### 4.1 Strong enough for PR A
- one `review_packet` can map to one compact decision object without semantic guessing
- promotion class, tone, placement, copyability, and readiness can all be derived conservatively

### 4.2 Strong enough for PR B
- the same judged truth can appear in brief, pickup, export, rebuild, observability, and ledger mirrors without needing consumer-specific invention

### 4.3 Strong enough for PR C
- the next dispatch can change for an inspectable reason, not just “because the brief existed”
- reuse can be classified as more than `shown_only` if warranted

### 4.4 Strong enough for PR D
- dangerous axes, claim limits, and next-smallest-proof guidance can remain visible through telemetry and pickup compression

## 5. Cases to avoid for the first ladder

Do **not** use these as the first anchor:

### Clean acceptance with little behavioral consequence
Why not:
- too easy for artifacts to align while reuse remains unproven

### Ambiguous hearsay-heavy case with unresolved trust conflict
Why not:
- useful later, but too likely to blur projection correctness with policy debate

### Mega-case with several redirects, evidence restrictions, and queue anomalies at once
Why not:
- too many semantic axes move together
- drift becomes harder to localize

### Case that requires transcript rereads to understand
Why not:
- breaks the compact proof requirement

## 6. Daytime selection checklist

Before starting PR A, confirm the chosen case can answer yes to all of these:
- [ ] does it produce a reviewed result that clearly justifies a compact decision object?
- [ ] does it have one office context stable enough for office-memory outputs?
- [ ] can the next dispatch plausibly change because of this reviewed truth?
- [ ] can that behavior change be explained without reopening transcripts?
- [ ] does it expose trust-preservation drift if consumers get stronger than the projection?
- [ ] can the same case remain readable across PR A, PR B, PR C, and PR D?
- [ ] would a pickup brief for this case still be meaningful if compressed aggressively?

If any answer is no, choose a different anchor.

## 7. Recommended morning operating rule

The first 15 minutes of the daytime window should do exactly this:
1. inspect candidate replay-backed redirect/rejection fixtures
2. choose one anchor case
3. record why it was chosen in one compact freeze note
4. freeze that case for the full first ladder unless it proves invalid

Use `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_ANCHOR_FREEZE_CONTRACT.md` for that note.
At minimum it should capture:
- selected case id / fixture name
- expected behavior change class
- main dangerous drift axes
- why this case is better than the runner-up
- invariants that PR A through PR D must preserve
- the explicit re-selection condition if the anchor proves invalid

## 8. Honest stop condition

If daytime cannot find one case that is both:
- narrow enough to stay readable
- strong enough to prove real behavior change

then the correct move is **not** to start broad implementation anyway.
The correct move is to tighten fixtures and case selection first.

## 9. Bottom line

The first daytime shared-decision ladder should start with one stable redirect or rejection case that can carry the whole proof program.

Choose the case that makes drift easiest to see and behavior change easiest to justify — not the case that looks most impressive on paper.
