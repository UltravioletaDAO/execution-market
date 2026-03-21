# KK V2 Swarm — Operations Guide

## Quick Start

```bash
# Check system health
python3 scripts/kk/swarm_ops.py health

# View fleet status
python3 scripts/kk/swarm_ops.py status

# Run a simulation
python3 scripts/kk/swarm_ops.py simulate

# Run a live poll cycle
python3 scripts/kk/swarm_ops.py poll

# Full dashboard
python3 scripts/kk/swarm_ops.py dashboard

# Performance benchmark
python3 scripts/kk/swarm_ops.py benchmark
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    OPERATIONS LAYER                      │
│  swarm_ops.py CLI | OpenClaw Heartbeat | Cron Jobs      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               COORDINATION LAYER                         │
│  SwarmCoordinator → EventListener → EvidenceParser      │
│  (Task lifecycle)   (API polling)   (Skill DNA)         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                INTELLIGENCE LAYER                        │
│  SwarmOrchestrator → ReputationBridge → AutoJobClient   │
│  (Task routing)      (Scoring)          (Enrichment)    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   STATE LAYER                            │
│  LifecycleManager → WorkerRegistry → ListenerState      │
│  (Agent states)     (Skill DNA)      (Watermarks)       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 EXTERNAL SERVICES                        │
│  EM API (production) | AutoJob API | ERC-8004 (Base)    │
└─────────────────────────────────────────────────────────┘
```

## Module Inventory (7 modules, ~3,700 LOC, 295 tests)

| Module | LOC | Tests | Layer |
|--------|-----|-------|-------|
| `coordinator.py` | 1,030 | 69 | Coordination |
| `event_listener.py` | 450 | 44 | Coordination |
| `evidence_parser.py` | 550 | 50 | Coordination |
| `orchestrator.py` | 454 | 24 | Intelligence |
| `reputation_bridge.py` | 334 | 41 | Intelligence |
| `autojob_client.py` | 412 | 29 | Intelligence |
| `lifecycle_manager.py` | 470 | 38 | State |

## Deployment Modes

### Mode 1: Heartbeat Integration (Recommended for OpenClaw)

Add to your HEARTBEAT.md:

```markdown
## Swarm Check
- Run swarm poll: `python3 ~/clawd/projects/execution-market/scripts/kk/swarm_ops.py poll`
- Check for unassigned tasks
- Report any agent degradation
```

This runs during OpenClaw heartbeats (~every 30 minutes).

### Mode 2: Cron Job

```bash
# Poll every 5 minutes
*/5 * * * * cd ~/clawd/projects/execution-market && python3 scripts/kk/swarm_ops.py poll >> /tmp/swarm.log 2>&1
```

### Mode 3: Continuous Daemon

```python
from swarm.coordinator import SwarmCoordinator
from swarm.event_listener import EventListener

coordinator = SwarmCoordinator.create(
    em_api_url="https://api.execution.market",
)

# Bootstrap agents
for agent_id in range(2101, 2125):
    coordinator.register_agent(
        agent_id=agent_id,
        name=f"Agent-{agent_id}",
        wallet_address=f"0x...",  # From ERC-8004 registry
    )

# Start continuous polling
listener = EventListener(
    coordinator,
    state_path="~/.em-swarm-listener-state.json",
)
listener.run(poll_interval=30)  # Poll every 30 seconds
```

## State Files

| File | Location | Purpose |
|------|----------|---------|
| Listener state | `~/.em-swarm-listener-state.json` | Watermarks for idempotent polling |
| Worker registry | `~/.em-swarm-worker-registry.json` | Persisted Skill DNA profiles |

## Health Checks

The health command runs 11 checks:

1. **EM API reachability** — Can we reach https://api.execution.market?
2. **AutoJob availability** — Is the enrichment service running? (optional)
3. **Module imports** (×7) — Can all 7 swarm modules be imported?
4. **Listener state** — Is the state file readable?
5. **Worker registry** — Is the registry file readable?

## Performance Characteristics

Benchmarked on Apple Silicon (M-series):

| Operation | Speed | Throughput |
|-----------|-------|------------|
| Task ingestion | 0.002ms/task | 650K tasks/sec |
| Task routing | 5.65ms/task | 177 tasks/sec |
| Evidence parsing | 0.027ms/set | 37K sets/sec |
| Skill DNA updates | 0.021ms/update | 47K updates/sec |

## Monitoring Events

The coordinator emits these events for monitoring:

| Event | When | Data |
|-------|------|------|
| `TASK_INGESTED` | New task added to queue | task_id, title, bounty |
| `TASK_ASSIGNED` | Task routed to agent | task_id, agent_id |
| `TASK_COMPLETED` | Task completed | task_id, agent_id |
| `TASK_FAILED` | Task failed | task_id, reason |
| `TASK_EXPIRED` | Task expired | task_id |
| `AGENT_REGISTERED` | New agent added | agent_id |
| `AGENT_DEGRADED` | Agent health degraded | agent_id |
| `AGENT_RECOVERED` | Agent recovered | agent_id |
| `AGENT_SUSPENDED` | Agent over budget | agent_id |
| `BUDGET_WARNING` | Budget threshold hit | agent_id, remaining |
| `HEALTH_CHECK` | Health check completed | results |
| `ROUTING_FAILURE` | No agent for task | task_id, reason |
| `AUTOJOB_ENRICHED` | AutoJob boost applied | agent_id, boost |

## Troubleshooting

### EM API returns empty tasks
- Check API status: `curl -s https://api.execution.market/health`
- Verify tasks exist: `curl -s "https://api.execution.market/api/v1/tasks?status=published"`
- May be no published tasks at the moment (normal)

### AutoJob not available
- AutoJob is optional — enrichment degrades gracefully
- Start AutoJob: `cd ~/clawd/projects/autojob && python3 server.py`

### All agents in SUSPENDED state
- Check budget configuration (daily/monthly limits)
- Reset: re-register agents with higher budget limits
- Verify no runaway task spending

### Listener keeps reprocessing same tasks
- Check state file: `cat ~/.em-swarm-listener-state.json`
- Delete state file to reset: `rm ~/.em-swarm-listener-state.json`
- Verify watermark timestamps are advancing
