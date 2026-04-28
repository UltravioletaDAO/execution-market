# City as a Service — Learning Strength Classification

> Last updated: 2026-04-28
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_REPLAY_BUNDLE_SPEC.md`
> - `CITY_AS_A_SERVICE_MANIFEST_ACCEPTANCE_CONTRACT.md`
> - `CITY_AS_A_SERVICE_BRIEF_IMPROVEMENT_SCORECARD.md`
> Status: implementation handoff draft

## 1. Why this doc exists

The replay bundle and manifest contract now define whether a City-as-a-Service replay run is valid, inspectable, and auditable.
What they do not yet distinguish clearly is how much useful operational learning a successful replay actually produced.

That missing distinction matters.
A technically valid replay can still represent weak learning.
If the first daytime implementation treats all successful bundles as equally meaningful, the system will overstate what has really been learned.

This doc defines the smallest first-pass classification for learning strength.

The goal is simple:

> let one replay bundle say not only whether the proof worked, but how valuable the learned office memory appears to be.

## 2. Core principle

**Validity and learning value are not the same thing.**

A replay can be:
- valid but weak
- valid and moderately useful
- valid and strongly reusable

The first city-ops seam should preserve that distinction explicitly.

## 3. Recommended manifest field

The first implementation should add a field like:

```json
{
  "summary_judgment": "pass",
  "learning_strength": "moderate",
  "learning_strength_rationale": [
    "brief now warns about outdated packet form before dispatch",
    "office playbook delta adds one new rejection-avoidance rule",
    "scorecard shows improvement in rejection avoidance and evidence realism"
  ]
}
```

Recommended values:
- `weak`
- `moderate`
- `strong`

A rationale list should stay short and operator-readable.

## 4. Classification meanings

### 4.1 `weak`

Use when the replay is valid and inspectable, but the operational learning is narrow or low-confidence.

Typical signs:
- wording changed more than actionability changed
- the office playbook delta mostly clarifies existing guidance
- only one low-stakes scorecard dimension improves
- the new brief looks cleaner but would not materially change worker behavior

`weak` still matters.
It can show the seam is functioning.
But it should not be treated as compelling memory promotion on its own.

### 4.2 `moderate`

Use when the replay creates a meaningful office-specific improvement that should influence future dispatch for similar work.

Typical signs:
- one concrete rejection-avoidance rule is added
- one redirect or office-routing pattern becomes more explicit
- the improved brief changes what evidence the worker should gather
- at least one operationally important scorecard dimension clearly improves

`moderate` means the learning is real and reusable, but still bounded.

### 4.3 `strong`

Use when the replay creates clearly reusable office memory that materially upgrades likely worker success.

Typical signs:
- a repeated rejection pattern turns into a stable prevention rule
- routing, evidence expectations, and fallback guidance all become stronger together
- the playbook delta is genuinely new, specific, and easy to apply again
- the scorecard improves across multiple meaningful dimensions
- the improved brief would likely change worker behavior in a safer or more successful way

`strong` should be uncommon in the first pass.
That is good.
If everything is `strong`, the scale is not honest enough.

## 5. Suggested first-pass decision heuristic

The first implementation does not need a hidden weighted formula.
It should stay review-friendly and explicit.

A practical heuristic is:
1. confirm the bundle is `pass` or `partial` reviewable at all
2. inspect the scorecard dimensions that improved
3. inspect whether the playbook delta introduced genuinely new behavioral guidance
4. inspect whether the improved brief changes likely worker action, routing, or evidence capture
5. assign `weak`, `moderate`, or `strong` with short rationale bullets

This keeps the first seam legible in PR review.

## 6. What should influence learning strength

The first-pass judgment should consider:
- number of scorecard dimensions improved
- importance of the dimensions improved
- whether the playbook delta is novel versus restated
- whether the learned rule is office-specific and reusable
- whether the improved brief changes likely task execution behavior
- whether the resulting guidance is easy for an operator to trust and reuse

The first pass should not depend on hidden embeddings, opaque confidence numbers, or long narrative reasoning.

## 7. Recommended relationship to summary judgment

These two fields should stay separate:
- `summary_judgment`
- `learning_strength`

Why:
- `summary_judgment` answers whether the replay proof succeeded technically and operationally
- `learning_strength` answers how valuable the resulting office memory appears to be

Examples:
- `pass` + `weak`
- `pass` + `moderate`
- `pass` + `strong`
- `partial` + `weak`

A `fail` bundle should usually omit learning strength or set it to `none` only if the implementation wants an explicit sentinel.

## 8. Sharp recommendation

**Make learning strength a first-class output of the replay manifest.**

That keeps the first City-as-a-Service proof honest:
not every successful run deserves the same memory weight, and the system should say so plainly.