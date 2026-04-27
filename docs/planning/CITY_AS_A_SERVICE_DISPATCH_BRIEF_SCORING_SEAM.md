# City as a Service — Dispatch Brief Scoring Seam

> Last updated: 2026-04-27
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> - `CITY_AS_A_SERVICE_REVIEW_LOOP_STATE_MACHINE.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The planning stack already defines:
- the reviewed-result contract
- the replay-fixture harness
- the review-loop promotion gate
- the observability model

What is still easy to fake is improvement.
A dispatch brief can change after replay without actually becoming more useful.

This doc defines the smallest scoring seam for deciding whether learned city memory produced a better next dispatch brief.

## 2. Core principle

**A changed brief is not the same thing as an improved brief.**

The first implementation should score replayed brief changes with explicit criteria, not intuition.

## 3. What this seam should prove

The first scoring pass should prove five things:
1. reviewed learning changed the brief in a traceable way
2. the new brief is operationally sharper, not merely longer
3. rejection or redirect learning appears where the worker needs it
4. fallback behavior becomes more actionable
5. operators can see why the brief changed

## 4. First scoring dimensions

Keep the first rubric tiny and inspectable.

### 4.1 Routing clarity
Ask:
- does the brief identify the likely office, desk, window, or redirect target more clearly?
- does it reduce ambiguity about where the worker should start?

### 4.2 Failure prevention
Ask:
- does the brief surface the exact rejection or evidence trap learned from review?
- does it help the worker avoid repeating the same avoidable mistake?

### 4.3 Fallback usefulness
Ask:
- if blocked or redirected, does the brief give a concrete next action?
- is the fallback specific enough to use under field pressure?

### 4.4 Provenance visibility
Ask:
- can an operator tell which reviewed episode or office-memory delta caused the new guidance?
- is the learning source inspectable without opening a transcript hunt?

### 4.5 Brevity under pressure
Ask:
- did the brief become sharper without turning into a wall of text?
- is the highest-value warning visible near the top?

This is the **brevity under pressure** check: improved guidance should get easier to use in the field, not just longer.

## 5. Suggested first scoring shape

The first scoring implementation can stay brutally simple.

For each dimension, score:
- `0` = no improvement or regression
- `1` = some improvement, but still muddy
- `2` = clear operational improvement

That yields a compact scorecard across five dimensions.

## 6. Minimum pass condition

A learned brief should count as improved only if:
- total score increases versus baseline
- `failure_prevention` or `routing_clarity` improves by at least 1
- no dimension regresses badly enough to make the brief less usable overall

This prevents replay from winning solely because the text became longer or more verbose.

## 7. How replay should use this seam

For a fixture pair, compare:
- **baseline brief** — before reviewed learning replay
- **learned brief** — after reviewed episode and office-memory update

Then assert:
- which dimensions improved
- which reviewed episode caused the delta
- whether the new brief passes the minimum gate

## 8. Recommended first fixture pairings

### 8.1 Rejection pair
Compare a baseline packet-submission brief against the brief after a reviewed rejection fixture.

Expected scoring pressure:
- failure prevention should improve
- brevity should not collapse

### 8.2 Redirect pair
Compare a baseline office-visit brief against the brief after a reviewed redirect fixture.

Expected scoring pressure:
- routing clarity should improve
- fallback usefulness should improve

### 8.3 Evidence-restriction pair
Compare a baseline counter brief against the brief after a reviewed evidence restriction fixture.

Expected scoring pressure:
- failure prevention should improve
- provenance visibility should remain clear

## 9. Failure modes this seam should catch

### 9.1 Text growth masquerading as learning
The brief gets longer but no clearer.

### 9.2 Hidden source problem
The brief changes, but operators cannot tell which reviewed task justified it.

### 9.3 Overfitting to one episode
One strange event turns into overconfident doctrine.

### 9.4 Replay that passes mechanically but not operationally
Artifacts validate, events emit, but the next worker still would not be better guided.

## 10. Strong recommendation

Before broad operator-surface polish, daytime should wire this scoring seam directly into fixture replay.

That gives the first CaaS implementation a harder product truth:
**reviewed city work only counts as learning when the next dispatch brief can be shown to improve by explicit criteria.**
