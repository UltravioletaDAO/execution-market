# Coordination Control Plane Prep

*Dream Session — 2026-04-05 3 AM*

This is a prep doc for the next Execution Market swarm phase while Acontext remains blocked on Docker.

## Why this doc exists

The current swarm stack is already strong:
- `reputation_bridge.py` fuses on-chain and internal scoring
- `lifecycle_manager.py` manages agent states, heartbeats, cooldowns, and budgets
- `orchestrator.py` assigns tasks with anti-duplication claims and routing strategies

What is still missing is the layer **between routing and memory**:
- durable decision history
- restart-safe coordination state
- cross-project retrieval
- measurable coordination quality

That missing layer is the **coordination control plane**.

---

## 1. Control Plane Goals

The control plane should make every important routing decision:
1. durable
2. replayable
3. explainable
4. measurable
5. portable across projects

That means the swarm should be able to answer:
- Why was this agent selected?
- What comparable tasks succeeded or failed before?
- What happened in IRC before the assignment?
- Did the chosen agent outperform the alternatives?
- What changed in worker reputation after the task?

---

## 2. Proposed Architecture

```text
EM task event
    ↓
SwarmOrchestrator.route_task()
    ↓
ReputationBridge.compute_composite()
    ↓
LifecycleManager availability/budget check
    ↓
Assignment / failure
    ↓
Control-plane event log (JSONL, local-first)
    ↓
Optional mirrors:
  - Acontext semantic summaries
  - IRC coordination snapshots
  - observability dashboards / metrics sinks
```

### Local-first rule

Raw coordination events should be written locally first.
Acontext is a retrieval accelerator, not the source of truth.
IRC is a transport, not the source of truth.

If Docker is down, if IRC disconnects, or if a retrieval system is unavailable, the swarm should still retain its decision history.

---

## 3. Event Schema

Suggested append-only event envelope:

```json
{
  "event_id": "ccp_2026_04_05_0001",
  "event_type": "task_routed",
  "task_id": "task_123",
  "task_category": "photo_geo",
  "task_priority": "high",
  "required_tier": "plata",
  "selected_agent_id": 12,
  "selected_wallet": "0xabc...",
  "strategy": "best_fit",
  "score": 84.2,
  "alternatives": [
    {"agent_id": 7, "score": 81.9},
    {"agent_id": 19, "score": 80.1}
  ],
  "top_factors": ["tier", "skill", "reliability", "recency"],
  "budget_headroom": 0.76,
  "lifecycle_state": "active",
  "coordination_session_id": "kkv2-base-photo-20260405-001",
  "captured_at": "2026-04-05T07:22:00Z"
}
```

Follow-up events should use the same `coordination_session_id`:
- `task_claimed`
- `task_started`
- `task_completed`
- `task_failed`
- `heartbeat_missed`
- `agent_degraded`
- `human_override`
- `assignment_replayed`

---

## 4. Acontext Integration Plan

### Phase A — prepare now

Add local event capture around:
- assignment success/failure in `orchestrator.py`
- lifecycle transitions in `lifecycle_manager.py`
- reputation score updates in `reputation_bridge.py`

Store events in a simple JSONL ledger such as:
- `data/swarm_control_plane/events-YYYY-MM-DD.jsonl`
- `data/swarm_control_plane/agent-{id}.json`
- `data/swarm_control_plane/task-{id}.json`

### Phase B — when Docker unblocks

Mirror *distilled summaries* into Acontext, not every raw event.

Examples of summary objects:
- agent capability card
- task pattern cluster summary
- recurring failure modes by category
- routing strategy win/loss summary
- operator override archive

### Phase C — semantic recall in routing

Before assigning a task, retrieve:
- similar tasks
- prior successful agents for those tasks
- failure modes for matching categories
- budget/risk patterns for comparable bounty ranges

Then feed the retrieved summaries into the coordinator as advisory context.

---

## 5. IRC Session Management Enhancement

IRC should become the **live coordination bus** while the control plane remains the durable memory.

### Proposed rules

1. Every routed task gets a `coordination_session_id`
2. Every IRC status line includes the task id or coordination session id
3. Important IRC events are mirrored into the local event ledger
4. Restarted agents can rebuild context from the last ledger snapshot + latest IRC summary

### Recommended message format

```text
[assign] session=kkv2-base-photo-20260405-001 task=123 agent=12 score=84.2 strategy=best_fit
[status] session=kkv2-base-photo-20260405-001 state=working heartbeat=ok budget=0.62
[fail] session=kkv2-base-photo-20260405-001 reason=timeout retry=1 next_agent=7
```

That format is:
- readable by humans
- parseable by bots
- compact enough for chat
- easy to mirror into JSONL

### Shared decision grammar upgrade (Apr 22)

To connect IRC/Acontext with AutoJob decision memory and the EM coordinator journal, the transport should now support a JSON payload mode alongside the compact text mode.

Recommended envelopes:

```json
{
  "event_type": "claim",
  "grammar": "v1",
  "task_id": "em_123",
  "coordination_session_id": "coord_em_123",
  "agent_id": "EM-Agent-07",
  "worker_id": "0xabc...",
  "task_type": "photo_geo",
  "timestamp": 1713769200.0
}
```

```json
{
  "event_type": "degrade",
  "grammar": "v1",
  "task_id": "em_123",
  "coordination_session_id": "coord_em_123",
  "agent_id": "EM-Agent-07",
  "status": "degraded",
  "coordination_quality": "heartbeat_missed",
  "task_count": 2,
  "timestamp": 1713769260.0
}
```

Transport recommendation:
- `!intent-json { ... }` for claim/lock events with task/session context
- `!heartbeat-json { ... }` for status/degrade emits with task/session context
- keep legacy `!intent` / `!heartbeat` commands for backward compatibility

This keeps IRC as the live bus while making the payloads directly ingestible by `decision_journal_ingestor.py` and mirrorable into Acontext semantic summaries.

---

## 6. Observability Metrics

### Routing quality
- assignment success rate
- first-choice win rate
- regret rate (would rank #2 have performed better?)
- route confidence calibration
- human override frequency

### Lifecycle quality
- state transition frequency
- cooldown efficiency
- degraded recovery time
- heartbeat miss streaks
- suspension causes by agent/personality/category

### Budget quality
- spend per successful completion
- spend wasted on failed or reassigned tasks
- daily/monthly headroom distribution
- high-value task budget allocation accuracy

### Coordination quality
- time-to-first-claim
- claim collision rate
- restart reconstruction success rate
- IRC-to-ledger sync lag
- operator intervention latency

### Reputation quality
- on-chain vs internal reputation divergence
- tier migration velocity
- seal ratio change after recent work
- category-specific trust drift

---

## 7. Live EM API Test Checklist

When live testing resumes, do not just test unit behavior. Test the actual boundary.

### Dream-session smoke run (verified 2026-04-05 07:08 UTC)

A lightweight live coordinator smoke test was executed against `https://api.execution.market` with the current `EMApiClient` + `SwarmCoordinator` stack.

**Verified live:**
- `/health` returned `status=healthy`
- `list_tasks(limit=3)` returned live published task IDs
- `get_task_stats()` successfully unwrapped the public metrics payload
- `SwarmCoordinator.ingest_from_api(limit=2)` ingested 2 live tasks
- `process_task_queue(max_tasks=2)` assigned both tasks successfully in local simulation
- AutoJob enrichment was unavailable locally (`127.0.0.1:8765` refused), so fallback routing path was exercised cleanly

**Observed result snapshot:**
- live task IDs: `3bb97d93-250b-46ad-99c7-0aed1713cd2b`, `5ff238d4-133f-46c7-9f3b-f25b3b0578f5`
- simulated assignments: agent `2106` score `66.4`, agent `2107` score `60.21`
- routing success rate: `1.0`
- avg routing / assignment time: `325.8ms`

That is enough to confirm the live boundary is healthy and that the coordinator can ingest + route current EM task payloads without mutating production state.

### Minimum live checks
- EM health endpoint reachable
- public task discovery returns live tasks
- coordinator can normalize task payload shape
- required-tier filtering works on real data
- invalid tier values fail cleanly
- assignment simulation produces a traceable decision record
- task stats endpoint unwraps real metrics payloads

### Evidence to capture
- raw request path
- raw response payload shape
- decision trace for chosen agent
- final event written to ledger
- any IRC coordination message emitted for the same task

---

## 8. Immediate Code Hooks

### `reputation_bridge.py`
Add optional metadata output alongside `CompositeScore`:
- contributing sub-scores
- threshold/tier rationale
- confidence / data sufficiency

### `lifecycle_manager.py`
Emit events for:
- register
- transition
- assign
- complete
- degrade
- suspend
- heartbeat miss
- budget threshold crossed

### `orchestrator.py`
Emit routing trace events for:
- available candidate set
- excluded agents and reasons
- required-tier normalization
- selected strategy
- selected agent and alternatives
- retry/failure paths

---

## 9. Strategic Payoff

Once this exists, the swarm gets four big upgrades:

1. **Memory** — decisions survive crashes and handoffs
2. **Explainability** — every route has an audit trail
3. **Retrieval** — Acontext can recall similar historical situations
4. **Improvement** — the system can measure not just outcomes, but whether its choices were good

That is the bridge from a good task router to a real coordination operating system.
