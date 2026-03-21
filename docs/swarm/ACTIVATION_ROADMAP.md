# KK V2 Swarm — Activation Roadmap

> From "code complete" to "production active"
>
> Generated: 2026-03-18 4AM Dream Session

## Current State

| Metric | Value |
|--------|-------|
| Swarm LOC | 12,511 (22 modules) |
| Tests | 1,103 all passing |
| Live Integration Tests | 11/11 passing against production API |
| Production Status | **DISABLED** (`SWARM_ENABLED=false`) |
| API Endpoints | `/api/v1/swarm/*` (12 routes, untested in production) |

## The Problem

**35.6% of tasks expire without completion.** This is the #1 business metric to fix.

Root causes (from live ExpiryAnalyzer run, March 18):
- 🔴 **Worker concentration**: 97% of completions from 1 worker (HHI = 0.94)
- 🔴 **Zero-worker categories**: knowledge_access, research, code_execution — 100% expiry
- 🟠 **Low bounties**: 106/108 expired tasks had bounty < $0.15
- 🟢 **Physical presence**: 86% completion rate — the only healthy category

## Activation Phases

### Phase 0: Pre-Flight (Now → Day 1)
**Goal: Verify the swarm doesn't break anything when enabled**

```bash
# 1. Set environment variables in ECS task definition
SWARM_ENABLED=true
SWARM_MODE=passive
SWARM_DAILY_BUDGET=0
SWARM_MAX_TASK_BOUNTY=0

# 2. Deploy
bash scripts/deploy-manual.sh
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment

# 3. Verify
curl -s https://api.execution.market/api/v1/swarm/status | python3 -m json.tool
# Expected: { "swarm_enabled": true, "coordinator": "active", "mode": "passive" }

# 4. Check no errors in logs
aws logs tail /ecs/em-production --since 5m --filter-pattern "swarm"
```

**Success criteria:**
- `/api/v1/swarm/status` returns `coordinator: active`
- No errors in CloudWatch logs
- All existing endpoints still work (regression check)
- `/health` still returns all components healthy

### Phase 1: Passive Observation (Day 1-3)
**Goal: Collect baseline metrics without any automated actions**

The swarm ingests tasks, scores agents, and reports metrics — but takes no actions.

**Monitor daily:**
```bash
# Fleet status
curl -s https://api.execution.market/api/v1/swarm/dashboard

# Metrics for monitoring
curl -s https://api.execution.market/api/v1/swarm/metrics
```

**What to watch:**
- `tasks_ingested` increasing (swarm sees new tasks)
- `agents_registered` > 0 (agents bootstrapped from ERC-8004)
- No error spikes in CloudWatch
- Memory/CPU stable on ECS

### Phase 2: Semi-Auto Routing (Day 3-10)
**Goal: Auto-assign micro-tasks to proven workers**

```bash
# Update config
SWARM_MODE=semi-auto
SWARM_DAILY_BUDGET=5.00
SWARM_MAX_TASK_BOUNTY=0.25
```

**Rules:**
- Only tasks with bounty ≤ $0.25 are auto-assigned
- Daily spending capped at $5.00
- Only workers with ≥ 3 completed tasks qualify
- Assignments logged to CloudWatch for audit

**Success criteria:**
- At least 5 tasks auto-assigned in first week
- Completion rate for auto-assigned tasks ≥ 80%
- No false-positive assignments (wrong category/worker)

### Phase 3: Full Autonomous (Day 10+)
**Goal: Swarm handles all routing decisions**

```bash
SWARM_MODE=full-auto
SWARM_DAILY_BUDGET=25.00
SWARM_MAX_TASK_BOUNTY=5.00
```

**Includes:**
- AutoJob enrichment for scoring
- FeedbackPipeline for learning from completions
- ExpiryAnalyzer for proactive intervention
- Push notifications for matching workers

## Parallel Workstreams

### Worker Recruitment (Critical Path)
The swarm is useless without workers. Current: 2 workers total.

**Immediate actions:**
1. Create "Welcome to Execution Market" onboarding task ($0.25 bounty)
2. Post on Fiverr/Upwork pointing to EM dashboard
3. Implement referral bonus: worker gets $0.50 for each new worker who completes a task
4. Build "AI Worker" capability: let AI agents complete digital tasks (code_execution, research)

### Bounty Optimization
**Implement bounty escalation curve in the API:**
- At 50% deadline with no bids: auto-increase bounty 25%
- At 75% deadline: auto-increase 50%
- Minimum effective bounty: $0.15

### Category Expansion
**Recruit specialized workers:**
| Category | Workers Needed | Skill Profile |
|----------|---------------|---------------|
| knowledge_access | 3+ | Data analysts, researchers |
| code_execution | 3+ | Developers (any language) |
| research | 3+ | Students, domain experts |
| physical_presence | 5+ | Gig workers in key metros |

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Swarm crashes production API | Phase 0: passive mode, zero budget |
| Bad routing wastes money | Daily budget cap, max bounty per task |
| Worker leaves (97% concentration) | Recruitment sprint, referral bonus |
| False assignments | Semi-auto phase with manual review |

## Metrics Dashboard

Track these weekly:
- **Expiry Rate**: Target < 20% (currently 35.6%)
- **Worker Count**: Target 10+ (currently 2)
- **Category Coverage**: Target 5/5 categories with workers (currently 2/5)
- **HHI (Worker Concentration)**: Target < 0.3 (currently 0.94)
- **Avg Completion Time**: Track per category
- **Bounty Efficiency**: $ earned per $ spent on bounties
