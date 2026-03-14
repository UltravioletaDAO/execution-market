# KarmaCadabra V2 Swarm Architecture

## Overview

The KK V2 Swarm is a multi-agent coordination system for the Execution Market (EM).
It manages a fleet of AI agents that autonomously claim, execute, and verify real-world tasks.

```
┌──────────────────────────────────────────────────────┐
│                  SwarmCoordinator                     │
│  (Top-level operational controller)                  │
│                                                      │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────┐ │
│  │ EMApiClient │   │ AutoJobClient│   │ EventBus  │ │
│  │ (Live API)  │   │ (Enrichment) │   │ (Hooks)   │ │
│  └──────┬──────┘   └──────┬───────┘   └───────────┘ │
│         │                 │                          │
│  ┌──────┴──────────────────┴──────────────────────┐  │
│  │              SwarmOrchestrator                  │  │
│  │  (Task routing with strategy selection)        │  │
│  │                                                │  │
│  │  ┌──────────────────┐ ┌─────────────────────┐  │  │
│  │  │ ReputationBridge │ │  LifecycleManager   │  │  │
│  │  │ (On-chain +      │ │  (States + Budget   │  │  │
│  │  │  Internal scoring)│ │   + Health)         │  │  │
│  │  └──────────────────┘ └─────────────────────┘  │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

## Module Inventory (15 modules, ~8,800 LOC, 880 tests)

| Module | LOC | Tests | Layer | Purpose |
|--------|-----|-------|-------|---------|
| `coordinator.py` | 1,031 | 69 | Coordination | Top-level operational controller + EMApiClient + event system |
| `analytics.py` | 1,048 | 93 | Intelligence | Performance analytics, trend detection, decision support |
| `daemon.py` | 678 | 59 | Operations | Production-ready continuous coordination loop |
| `strategy_engine.py` | 666 | 57 | Intelligence | Adaptive multi-strategy routing with outcome learning |
| `evidence_parser.py` | 643 | 50 | Coordination | Extracts Skill DNA from evidence + WorkerRegistry |
| `event_listener.py` | 572 | 44 | Coordination | Polls EM API for task lifecycle events |
| `acontext_adapter.py` | 558 | 50 | Memory | Local file-based structured memory system |
| `config_manager.py` | 554 | 81 | Operations | Production config (files, env vars, presets, validation) |
| `lifecycle_manager.py` | 525 | 38 | State | 7-state agent machine + budget tracking + health |
| `orchestrator.py` | 472 | 24 | Intelligence | Task routing with 4 core strategies |
| `bootstrap.py` | 439 | 26 | Operations | Production-aware coordinator initialization |
| `autojob_client.py` | 412 | 29 | Intelligence | AutoJob enrichment bridge + EnrichedOrchestrator |
| `reputation_bridge.py` | 354 | 41 | Intelligence | On-chain ERC-8004 + internal Bayesian scoring |
| `heartbeat_handler.py` | 298 | — | Operations | Condensed coordination for heartbeat integration |
| `mcp_tools.py` | 268 | — | Interface | MCP protocol tools for agent-native interaction |
| **Total** | **~8,800** | **880** | | |

## Data Flow

```
1. INGESTION
   EM API (published tasks) ──→ coordinator.ingest_from_api()
   Manual submission         ──→ coordinator.ingest_task()
                                    │
                                    ▼
2. QUEUE
   QueuedTask { task_id, title, categories, bounty, priority }
   Sorted by: priority DESC, ingested_at ASC
                                    │
                                    ▼
3. ROUTING (coordinator.process_task_queue())
   ┌────────────────────────────────────────────────┐
   │ For each pending task:                         │
   │  a. AutoJob enrichment (if available)          │
   │  b. ReputationBridge scoring (on-chain+internal)│
   │  c. LifecycleManager availability check        │
   │  d. Strategy-based selection                   │
   │  e. Anti-duplication claim                     │
   └────────────────────────────────────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
                    Assignment            RoutingFailure
                    (task → agent)        (retry or expire)
                          │
                          ▼
4. EXECUTION (external - agent does the work)
                          │
                          ▼
5. COMPLETION / FAILURE
   coordinator.complete_task()    coordinator.fail_task()
       │                              │
       ▼                              ▼
   Reputation updated            Cooldown extended
   Budget tracked                Failure counter++
   Agent → COOLDOWN              Agent → COOLDOWN (3x)
       │                              │
       ▼                              ▼
6. FEEDBACK LOOP
   Internal reputation scores adjust based on outcomes
   Category-specific Skill DNA improves with successful completions
```

## Agent State Machine

```
  INITIALIZING
       │
       ▼ (register)
     IDLE ◄────────── COOLDOWN ◄─── WORKING
       │                  ▲              ▲
       ▼ (activate)       │              │
    ACTIVE ───────────────┘──────────────┘
       │
       ├── miss heartbeats ──→ DEGRADED ──→ recover ──→ IDLE
       │
       └── budget exceeded ──→ SUSPENDED ──→ manual resume ──→ IDLE
```

## Reputation Scoring

CompositeScore = weighted blend of:
- **Skill Score** (45%): Category experience + evidence quality
- **Reputation Score** (25%): Bayesian score + on-chain seal ratio + tier bonus
- **Reliability Score** (20%): Success rate + consecutive failure penalty
- **Recency Score** (10%): Time since last activity

AutoJob enrichment adds up to 15 bonus points based on:
- Evidence-based matching (50% weight)
- External reputation (30% weight)
- Reliability history (20% weight)

## Routing Strategies

| Strategy | Description |
|----------|-------------|
| `BEST_FIT` | Highest composite score wins |
| `ROUND_ROBIN` | Even distribution, score tiebreaker |
| `SPECIALIST` | Only agents with category experience (skill ≥ 50) |
| `BUDGET_AWARE` | 70% score + 30% remaining budget headroom |

## On-Chain Integration

### ERC-8004 Identity + Reputation
- Agent wallets registered on-chain (Base mainnet)
- Reputation seals issued after task completion
- 5 tiers: Diamante → Oro → Plata → Bronce → Nuevo
- Cross-platform, immutable reputation history

### describe-net SealRegistry
- EIP-712 meta-transactions for gasless seal issuance
- Delegation system for seal authorities
- Time-weighted scoring with decay
- 98 Foundry tests (79 SealRegistry + 19 ERC8004ReputationAdapter)

## Event System

The coordinator emits events for monitoring:
- `TASK_INGESTED`, `TASK_ASSIGNED`, `TASK_COMPLETED`, `TASK_FAILED`, `TASK_EXPIRED`
- `AGENT_REGISTERED`, `AGENT_DEGRADED`, `AGENT_RECOVERED`, `AGENT_SUSPENDED`
- `BUDGET_WARNING`, `HEALTH_CHECK`, `ROUTING_FAILURE`, `AUTOJOB_ENRICHED`

Events support hooks for external integrations (dashboards, alerts, logging).

## Feedback Loop (Self-Improving System)

The feedback loop is what makes the swarm get smarter over time:

```
Task Completed on EM API
         │
         ▼
┌────────────────────┐
│   EventListener    │  ← Polls EM API for new completions
│   (poll_once())    │     Watermark-based idempotent processing
└────────┬───────────┘
         │ completed task + evidence
         ▼
┌────────────────────┐
│  EvidenceParser    │  ← Extracts Skill DNA from evidence
│  - Type mapping    │     10 evidence types → 10 skill dimensions
│  - Quality scoring │     Fraud detection (lorem ipsum, placeholder, etc.)
│  - Fraud detection │     Diversity/quantity bonuses
└────────┬───────────┘
         │ SkillSignals + QualityAssessment
         ▼
┌────────────────────┐
│   WorkerRegistry   │  ← Persists worker Skill DNA profiles
│   - Skill DNA      │     EMA-based dimension scoring
│   - Categories     │     Category-specific expertise tracking
│   - Quality avg    │     Running average quality score
└────────┬───────────┘
         │ updated worker profile
         ▼
┌────────────────────┐
│  ReputationBridge  │  ← Blends on-chain + internal reputation
│  → SwarmOrchestrator│  ← Better routing decisions next time
└────────────────────┘
```

### Skill Dimensions (10 dimensions)
| Dimension | Evidence Sources |
|-----------|-----------------|
| physical_execution | photo, photo_geo, receipt, video |
| digital_proficiency | document, text_response, screenshot |
| verification_skill | photo_geo, screenshot, notarized, signature, timestamp_proof |
| communication | text_response, document, video |
| geo_mobility | photo_geo |
| speed | timestamp_proof |
| thoroughness | photo, video, document, receipt, measurement, notarized |
| technical_skill | measurement |
| creative_skill | (via task context: design, writing) |
| blockchain_literacy | (via task context: blockchain, defi, nft) |

### Evidence Quality Tiers
- **Excellent** (≥0.8): Multiple types, rich metadata, geo-verified
- **Good** (≥0.6): Complete and relevant evidence
- **Adequate** (≥0.4): Meets minimum requirements
- **Poor** (<0.4): Minimal or irrelevant
- **Suspicious**: Fraud patterns detected (penalized)

## Production Readiness

| Aspect | Status |
|--------|--------|
| Unit tests | 295 passing |
| Integration tests | Live EM API verified |
| Performance | 20 tasks across 24 agents in < 2s |
| Budget safety | Hard limits with auto-suspend |
| Health monitoring | Heartbeat + cooldown + degradation |
| Error handling | Graceful fallbacks throughout |
| Zero dependencies | stdlib-only HTTP clients |
| Feedback loop | Evidence → Skill DNA → better routing |
| State persistence | JSON-based watermarks + worker registry |
