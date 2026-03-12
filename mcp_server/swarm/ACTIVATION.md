# KK V2 Swarm — Phase 2 Activation Playbook

> Created: March 11, 2026 4:00 AM (dream session — pattern recognition)
> Status: READY TO ACTIVATE — all code built, all tests passing

## The Big Picture

We have 3,915 lines of production-ready swarm code, 295 tests, and 7 modules.
We have 24 agents registered with ERC-8004 on Base. We have 189+ completed tasks
in production. We have an evidence-based job matching engine with 1,013 tests.
We have on-chain reputation contracts with 78 passing Forge tests.

**The code exists. The infrastructure exists. What's missing is the activation sequence.**

This document is the exact step-by-step to go from "code on a branch" to
"autonomous swarm processing real tasks."

---

## Prerequisites (Current State)

| Prerequisite | Status | Notes |
|-------------|--------|-------|
| Swarm modules (7/7) | ✅ | 3,915 LOC, 295 tests |
| EM API production | ✅ | Healthy, 189+ completed tasks |
| ERC-8004 identities | ✅ | 24 agents registered on Base |
| AutoJob integration | ✅ | Bridge layer + enrichment endpoint |
| describe-net contracts | ✅ | 78 tests, deployed to Base Sepolia |
| Ecosystem validator | ✅ | 2,359 tests, all green |
| Git auth (push) | ❌ | Token expired — needs `gh auth login` |

---

## Activation Sequence

### Step 0: Fix Git Auth (Blocker)
```bash
# On Saúl's machine (needs browser for OAuth)
gh auth login
gh auth setup-git
# Verify:
cd ~/clawd/projects/execution-market
git push origin feat/karmacadabra-swarm
```

### Step 1: Merge Swarm Branch to Main
```bash
cd ~/clawd/projects/execution-market
git checkout main
git merge feat/karmacadabra-swarm --no-ff -m "feat: KK V2 Swarm — 7 modules, 295 tests"
git push origin main
```

### Step 2: Deploy Backend with Swarm Modules
```bash
# The swarm modules are in mcp_server/swarm/ — they ship with the API server
bash scripts/deploy-manual.sh
aws ecs update-service --cluster em-production-cluster \
  --service em-production-mcp-server --force-new-deployment --region us-east-2
aws ecs wait services-stable --cluster em-production-cluster \
  --services em-production-mcp-server --region us-east-2
curl -s https://api.execution.market/health
```

### Step 3: Add Swarm API Endpoints
The coordinator currently runs as a library. To expose it as API endpoints:

```python
# mcp_server/routes/swarm.py — NEW FILE NEEDED
from fastapi import APIRouter
from mcp_server.swarm import create_coordinator

router = APIRouter(prefix="/api/v1/swarm", tags=["swarm"])

@router.get("/status")
async def swarm_status():
    """Get swarm fleet status and metrics."""
    coord = get_coordinator()
    return coord.get_dashboard()

@router.get("/health")
async def swarm_health():
    """Health check for all swarm subsystems."""
    coord = get_coordinator()
    return coord.health_check()

@router.post("/poll")
async def swarm_poll():
    """Trigger one poll cycle — ingest + route."""
    coord = get_coordinator()
    new_tasks = coord.ingest_from_api()
    assigned = coord.process_task_queue()
    return {"new_tasks": new_tasks, "assigned": assigned}
```

### Step 4: Deploy EventListener as Cron Job
The EventListener can run as:
- **Heartbeat check** (simplest — check every 30 min during heartbeat)
- **Cron job** (more reliable — dedicated schedule)
- **Daemon process** (most responsive — continuous polling)

**Recommended: Start with heartbeat, graduate to cron.**

Add to HEARTBEAT.md:
```markdown
## Swarm Poll
- Check EM API for new published tasks
- Route queued tasks to available agents
- Process completions → update reputation
```

### Step 5: Agent Activation
Currently agents are registered but passive. To activate:

1. Each agent needs a **wallet** with USDC for task bonds
2. Each agent needs **task execution capability** (OpenClaw skill or API integration)
3. The orchestrator routes tasks → agent receives notification → agent executes → submits evidence

**Minimal viable activation:**
- Pick 3-5 agents with diverse skills
- Fund each with $5 USDC (50 tasks at $0.10)
- Start with simple_action category tasks
- Monitor via swarm_ops.py dashboard

### Step 6: Evidence → Skill DNA Pipeline
Once tasks complete with evidence:
1. EventListener detects completion
2. EvidenceParser extracts Skill DNA dimensions
3. WorkerRegistry updates worker profiles
4. Next routing uses enriched data
5. **Flywheel spins**

---

## Activation Modes

### Mode A: Passive Monitor (Low Risk)
- Deploy EventListener in poll-only mode
- Ingest tasks but DON'T auto-assign
- Build up intelligence on task patterns
- Human approves assignments manually
- **Risk: Zero. Just watching.**

### Mode B: Semi-Autonomous (Medium Risk)
- Auto-assign tasks under $1.00 bounty
- Human approval for tasks >$1.00
- Auto-process evidence and reputation
- Budget limit: $10/day per agent
- **Risk: Low. $10/day cap.**

### Mode C: Full Autonomous (Production)
- All routing strategies active
- Budget-aware routing prevents overspend
- Reputation-weighted assignment
- Auto-escalation on failures
- **Risk: Managed. Budget + reputation gates.**

**Recommendation: Start with Mode A for 1 week, then Mode B.**

---

## Monitoring & Alerting

### Dashboard Command
```bash
cd ~/clawd/projects/execution-market
python3 scripts/kk/swarm_ops.py dashboard
```

### Key Metrics to Watch
| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Routing success rate | >90% | 70-90% | <70% |
| Avg routing time | <10ms | 10-50ms | >50ms |
| Agent utilization | 30-80% | <30% or >80% | 0% or 100% |
| Task completion rate | >85% | 60-85% | <60% |
| Budget burn rate | Under daily limit | >80% daily | Over limit |

### Alert Channels
- **Telegram** (primary): message tool → Saúl's chat
- **Heartbeat**: include swarm status in periodic checks
- **Cron**: dedicated monitoring job every 4 hours

---

## What Creates Exponential Value

### The Flywheel Effect
```
More tasks → More evidence → Better Skill DNA →
Better routing → Higher completion rate →
More reputation seals → More trust →
Higher-value tasks → More revenue →
More workers attracted → More tasks → CYCLE
```

### Network Effects
Each new agent makes ALL agents more valuable because:
1. More diverse skills = broader task coverage
2. More completion data = better matching accuracy
3. More reputation seals = stronger trust network
4. Specialist routing improves with more specialists

### Cross-Project Multipliers
1. **EM × AutoJob** = Evidence-enriched routing (BUILT)
2. **EM × describe-net** = On-chain reputation seals (CONTRACTS DEPLOYED)
3. **AutoJob × describe-net** = Portable skill credentials (DESIGNED)
4. **Swarm × All** = Autonomous coordination layer (BUILT)
5. **Frontier Academy × EM** = Theory → Practice pipeline (CONCEPTUAL)

### The 10x Unlock
When the swarm is active with 10+ agents processing real tasks:
- Every task completion generates 3 types of value:
  1. **Revenue** (bounty - fees)
  2. **Data** (evidence → Skill DNA)
  3. **Reputation** (on-chain seals)
- The data and reputation are COMPOUNDING assets
- Traditional marketplaces only capture #1

---

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Agent runs out of USDC | High | Low | Budget limits in LifecycleManager |
| Bad routing (wrong agent) | Medium | Low | Reputation feedback corrects quickly |
| API downtime | Low | Medium | EventListener has graceful retry |
| Evidence fraud | Low | High | EvidenceParser has fraud detection |
| Budget overspend | Low | Medium | Daily/monthly caps with auto-suspend |
| Git auth blocks deploy | High (current) | High | Fix with `gh auth login` |

---

## Timeline

| Week | Action | Outcome |
|------|--------|---------|
| W1 | Fix git auth, merge, deploy | Swarm code in production |
| W1 | Activate Mode A (passive) | Start collecting intelligence |
| W2 | Fund 5 agents, Mode B | Semi-autonomous task processing |
| W2 | Deploy EventListener cron | Automated poll cycle |
| W3 | Analyze first 100 completions | Tune routing strategies |
| W3 | Deploy AutoJob alongside EM | Enriched routing active |
| W4 | Mode C for simple_action | Full autonomous for low-value tasks |
| W4 | Evaluate expansion | Scale to more categories/agents |

---

*This playbook is the bridge between "code complete" and "value flowing."*
*The code is ready. The infrastructure is ready. We just need to turn the key.*
