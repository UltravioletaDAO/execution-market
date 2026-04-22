# Route Regret Reporting

*Dream Session — 2026-04-21 10 PM kickoff follow-through*

This doc defines the next operator-visible layer for the Execution Market swarm stack.

The coordinator is starting to emit replayable decision-journal records with stable `coordination_session_id`s.
That is the right foundation.

The next step is to turn those records into something a human can actually use during the day:

> **route regret reporting**

Not more hidden scoring.
Not another private heuristic.
A compact explanation of whether the routing decision was good, what alternatives existed, and what should change.

---

## 1. Why this matters now

The current swarm stack is already close to useful memory:
- `coordinator.py` can emit replayable assignment / completion events
- `reputation_bridge.py` provides portable trust signals
- `lifecycle_manager.py` provides availability and degradation context
- AutoJob is already moving toward a shared event grammar: `route`, `claim`, `degrade`, `outcome`

What is still missing is the daytime operator surface.

Right now, a human still has to read raw logs, raw tests, or raw event files to answer:
- what happened?
- was the chosen agent actually the best choice?
- did lifecycle pressure or coordination friction distort the decision?
- what should we tune next?

Route-regret reporting is the missing bridge between replayable control-plane memory and product iteration.

---

## 2. Definition

A **route regret report** compares:
1. the agent that was actually chosen at route time
2. the best alternative from the original shortlist
3. the eventual outcome of the actual choice
4. the likely counterfactual quality of the strongest alternative
5. the signals that explain the gap

A route can land in one of four practical states:

- **validated** — actual choice was clearly good
- **matched** — actual choice and top alternative look equivalent
- **regret** — alternative likely would have performed better
- **uncertain** — insufficient follow-up evidence to judge

This is not a perfect causal oracle.
It is an operator tuning instrument.

---

## 3. Minimal event requirements

To compute route regret cleanly, the control plane should persist at least these fields across the episode.

### Route event
```json
{
  "event_type": "route",
  "task_id": "em_123",
  "coordination_session_id": "coord_em_123",
  "timestamp": 1713823200.12,
  "selected_agent_id": 2106,
  "selected_score": 0.84,
  "strategy": "best_fit",
  "alternatives": [
    {"agent_id": 2107, "score": 0.81},
    {"agent_id": 2110, "score": 0.77}
  ],
  "metadata": {
    "category": "photo_geo",
    "required_tier": "oro",
    "bounty_usd": 0.42,
    "top_factors": ["tier", "quality", "availability", "recency"]
  }
}
```

### Claim / degrade / outcome companion events
At minimum, follow-up records should preserve:
- `coordination_session_id`
- `task_id`
- `agent_id`
- `event_type`
- `status`
- `quality` where available
- `payout_usd` where available
- degradation reason / timeout reason where available

The actual field names can vary by producer, but the normalized shape should remain stable.

---

## 4. Regret scoring model

Keep the first version simple and explainable.

### Inputs
- route-time selected agent and score
- top alternative(s) and their scores
- actual outcome status
- actual quality score if available
- degradation / timeout / reassignment markers
- payout result
- lifecycle friction markers

### Suggested first-pass judgment rules

#### Validated
- selected agent completed successfully
- no degradation or only minor friction
- quality >= expected threshold
- no strong evidence an alternative materially outperformed the choice

#### Matched
- selected agent completed successfully
- quality is acceptable
- route score gap between selected and runner-up was narrow
- no outcome signal suggests clear under-selection

#### Regret
One or more of:
- selected agent degraded, timed out, or required reassignment
- selected agent completed but quality was significantly below expectation
- alternative agent had similar or higher score and stronger comparable-history indicators
- repeated pattern shows this task archetype favors a different profile than the route policy selected

#### Uncertain
- task expired without enough evidence
- no quality/payout result yet
- event chain incomplete

### Compact regret score
For dashboards, one numeric field is useful:
- `-1.0` = validated strongly
- `0.0` = matched / neutral
- `+1.0` = strong regret

But the explanation text matters more than the number.

---

## 5. Example operator-facing output

```json
{
  "task_id": "em_123",
  "coordination_session_id": "coord_em_123",
  "judgment": "regret",
  "regret_score": 0.72,
  "selected_agent_id": 2106,
  "selected_score": 0.84,
  "best_alternative_agent_id": 2107,
  "best_alternative_score": 0.81,
  "outcome": {
    "status": "degraded_then_reassigned",
    "quality": 0.41,
    "payout_usd": 0.00
  },
  "explanation": [
    "Selected agent timed out after initial route despite high availability score.",
    "Runner-up agent had stronger recent performance in photo_geo tasks at this bounty range.",
    "This coordination session matches a recurring low-bounty timeout pattern during cooldown-heavy windows."
  ],
  "tuning_hints": [
    "Increase cooldown penalty for this task archetype.",
    "Weight recency-adjusted task completion higher for sub-$0.50 field tasks.",
    "Flag timeout-prone agents earlier when score gap to runner-up is <0.05."
  ]
}
```

That is the right level of output: compact, replayable, legible.

---

## 6. Where it should live

### In Execution Market
Execution Market should own the control-plane side of the story:
- route event creation
- lifecycle and degrade event emission
- outcome stitching for the same `coordination_session_id`
- operator dashboard / reporting hooks

### In AutoJob
AutoJob should own the cross-episode intelligence layer:
- comparable-history retrieval
- route-regret pattern clustering
- shadow-mode counterfactual summaries
- worker / task archetype summaries

### In Acontext
Acontext should receive only distilled summaries such as:
- route-regret pattern cards
- task archetype drift summaries
- worker reliability shift summaries

Not raw event exhaust.

---

## 7. Suggested implementation sequence

### Phase 1 — stabilize event emission
In `coordinator.py`, ensure route / completion / failure records always include:
- `coordination_session_id`
- `task_id`
- `agent_id`
- route score
- alternatives when known
- category / bounty / tier context

### Phase 2 — add local regret compiler
Add a small module such as:
- `route_regret.py`

Responsibilities:
- load normalized coordinator events
- stitch them into episodes by `coordination_session_id`
- classify judgment: validated / matched / regret / uncertain
- emit compact report objects

### Phase 3 — expose operator-readable summaries
Potential surfaces:
- CLI summary command
- dashboard JSON endpoint
- daily digest for top regret clusters
- swarm diagnostics panel

### Phase 4 — shadow-mode tuning loop
Compare:
- actual coordinator choice
- current recommended choice under updated logic
- outcome delta
- repeated regret signatures by category / bounty / time-of-day

This is where the routing policy starts improving in a disciplined way.

---

## 8. Metrics worth tracking

### Per task
- judgment
- regret score
- selected vs runner-up score gap
- degradation count
- time to claim
- time to completion
- payout success

### Per agent
- validated route rate
- regret-associated route rate
- timeout-associated regret rate
- recovery rate after degraded state

### Per archetype
- regret rate by category
- regret rate by bounty range
- regret rate by time-of-day
- regret rate by routing strategy

### Per control-plane policy
- human override rate
- false confidence rate
- narrow-gap miss rate
- cooldown penalty effectiveness

---

## 9. Design constraints

### Keep it explainable
If an operator cannot understand why a route was marked regret, the system will not be trusted.

### Prefer stable schema over clever inference
A boring shared event grammar is worth more than a smart parser over inconsistent records.

### Local-first always
Raw route-regret inputs should be reproducible from local event history.
No external mirror should be the only source of truth.

### Treat this as a tuning layer, not a blame layer
The goal is to improve routing policy and worker/task matching.
Not to create punitive scorecards disconnected from context.

---

## 10. One-sentence recommendation

> **Execution Market should turn replayable coordinator events into route-regret reports so daytime operators can tune the market from evidence instead of instinct.**

That is the next highest-leverage step after stable `coordination_session_id` event emission.
