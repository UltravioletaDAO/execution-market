# Acontext Integration Plan for KK V2 Swarm

> **Status:** Architecture Draft — Feb 22, 2026
> **Author:** Clawd (dream session)
> **Priority:** P1 — Infrastructure for agent intelligence

## 1. Overview

[Acontext](https://docs.acontext.io/) is a context data platform for AI agents ("Supabase for agents").
It provides: session storage, context engineering, agent observability, self-learning skills, 
and sandboxed execution — all accessible via REST API + Python/TS SDKs.

### Why Acontext for KK V2?

KK V2 has 24 agents operating on Execution Market. Currently their "memory" is:
- `WORKING.md` files per workspace (local, non-shared)
- Supabase `kk_swarm_state` table (basic status only)
- IRC messages (ephemeral, unstructured)

**Problems this creates:**
1. No cross-session learning — agents repeat mistakes
2. No structured context window management — token limits hit unpredictably
3. No observability — can't measure agent success rates
4. No skill sharing — each agent reinvents approaches
5. No context compression — stale context wastes tokens

**Acontext solves all five.**

## 2. Architecture

```
┌─────────────────────────────────────────────────┐
│                  KK V2 Swarm                     │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │coordinator│ │karma-hello│ │ skill-   │  ...x24 │
│  │  service  │ │  service  │ │extractor │         │
│  └─────┬─────┘ └─────┬─────┘ └─────┬────┘        │
│        │              │              │             │
│  ┌─────┴──────────────┴──────────────┴──────┐    │
│  │           Acontext Client Layer            │    │
│  │  (Python SDK — per-agent sessions)        │    │
│  └─────────────────┬─────────────────────────┘    │
└────────────────────┼──────────────────────────────┘
                     │ REST API
         ┌───────────┴───────────┐
         │   Acontext Server     │
         │  (Docker, localhost)  │
         │                       │
         │  ┌─────────────────┐ │
         │  │ Session Store   │ │  ← Agent conversation history
         │  ├─────────────────┤ │
         │  │ Disk Storage    │ │  ← Agent workspaces, artifacts
         │  ├─────────────────┤ │
         │  │ Skills Registry │ │  ← Shared EM skills (browse, publish, etc.)
         │  ├─────────────────┤ │
         │  │ Observability   │ │  ← Success rate, task extraction
         │  ├─────────────────┤ │
         │  │ Learning Spaces │ │  ← Cross-agent skill learning
         │  └─────────────────┘ │
         └───────────────────────┘
```

## 3. Integration Points

### 3.1 Session Management (Priority: HIGH)

Each KK agent gets a persistent Acontext session per "work cycle":

```python
from acontext import AcontextClient

# Per-agent initialization
client = AcontextClient(
    base_url="http://localhost:8029/api/v1",
    api_key=ACONTEXT_ROOT_KEY,
)

# Create session for this agent's work cycle
session = client.sessions.create(
    metadata={
        "agent_name": "kk-coordinator",
        "agent_id": 18775,
        "cycle": "2026-02-22T00:00:00Z",
        "archetype": "system",
    }
)

# Store LLM interactions
client.sessions.store_message(
    session_id=session.id,
    blob={"role": "system", "content": coordinator_system_prompt},
    format="anthropic",
)

# Retrieve with context engineering (auto-compress)
messages = client.sessions.get_messages(
    session_id=session.id,
    format="anthropic",
    edit_strategies=[
        {"type": "remove_tool_result", "params": {"keep_recent_n_tool_results": 5}},
        {"type": "token_limit", "params": {"limit_tokens": 50000}},
    ],
)
```

**Replaces:** WORKING.md per workspace, manual context truncation

### 3.2 Agent Workspaces as Disks (Priority: HIGH)

Each agent's workspace maps to an Acontext Disk:

```python
# Create disk per agent
disk = client.disks.create(
    name=f"kk-{agent_name}-workspace",
    metadata={
        "agent_id": agent_erc8004_id,
        "wallet": agent_wallet_address,
    },
)

# Store agent artifacts
client.artifacts.upsert(
    disk_id=disk.id,
    path="data/",
    filename="profile.json",
    content=agent_profile_json,
)

# Search across all agent artifacts
results = client.artifacts.search_content(
    disk_id=disk.id,
    pattern="task.*completed",
)
```

**Replaces:** Local filesystem workspace dirs, manual artifact management

### 3.3 Shared EM Skills (Priority: MEDIUM)

The 9 EM skills (browse, publish, apply, submit-evidence, approve, rate, etc.)
become shared Acontext skills that any agent can mount:

```python
# Upload EM skill pack
with open("skills/em-browse-tasks/skill.zip", "rb") as f:
    skill = client.skills.create(
        file=FileUpload(filename="em-browse-tasks.zip", content=f.read())
    )

# Mount into agent's sandbox
client.skills.download_to_sandbox(
    skill_id=skill.id,
    sandbox_id=sandbox.id,
)
```

**Replaces:** Manual skill file copying, per-agent skill installation

### 3.4 Observability (Priority: HIGH)

Automatic task extraction and success rate tracking:

```python
# Session summaries for coordinator oversight
summary = client.sessions.get_session_summary(session_id=agent_session.id)

# Coordinator can monitor all agent sessions
for agent in agents:
    summary = client.sessions.get_session_summary(agent.session_id)
    if "failed" in summary.lower():
        # Route to coordinator for intervention
        notify_coordinator(agent.name, summary)
```

**Replaces:** Manual log parsing, `aggregate-logs.py` script

### 3.5 Self-Learning (Priority: FUTURE)

Agents learn from past sessions — skills improve over time:

```python
# Create learning space for EM task execution
space = client.learning_spaces.create(name="em-task-execution")

# Include relevant skills
client.learning_spaces.include_skill(space_id=space.id, skill_id=browse_skill.id)
client.learning_spaces.include_skill(space_id=space.id, skill_id=submit_skill.id)

# After successful task completion, the session feeds into learning
# Acontext automatically extracts patterns from successful sessions
```

**Future value:** Agents get better at EM tasks without explicit retraining

## 4. Implementation Plan

### Phase 1: Local Server Setup (1-2 hours)
- [x] Install Acontext Python SDK (v0.1.13)
- [ ] Start Docker daemon
- [ ] Run `acontext server up` (creates local server + dashboard)
- [ ] Verify API at `http://localhost:8029/api/v1`
- [ ] Verify dashboard at `http://localhost:3000`

### Phase 2: Agent Session Integration (3-4 hours)
- [ ] Create `scripts/kk/lib/acontext_client.py` — shared client wrapper
- [ ] Integrate into `coordinator_service.py` — session per coordination cycle
- [ ] Integrate into `swarm_runner.py` — session per agent work cycle
- [ ] Store LLM interactions from agent actions
- [ ] Context engineering for long-running sessions

### Phase 3: Workspace Migration (2-3 hours)
- [ ] Create Disk per agent (24 disks)
- [ ] Migrate agent profiles from local JSON to Acontext artifacts
- [ ] Migrate WORKING.md state to Acontext sessions
- [ ] Search/query across agent workspaces via Acontext API

### Phase 4: Observability Dashboard (1-2 hours)
- [ ] Configure Acontext dashboard for KK metrics
- [ ] Set up success rate tracking per agent
- [ ] Coordinator reads summaries instead of parsing logs
- [ ] Alert on agent failures/stalls

### Phase 5: Skill Registry (2-3 hours)
- [ ] Package 9 EM skills as Acontext skill ZIPs
- [ ] Upload to Acontext skills registry
- [ ] Mount skills into sandboxes on-demand
- [ ] Version management for skill updates

## 5. Configuration

### Docker Compose (Acontext Server)
```yaml
# Created automatically by `acontext server up`
# Default ports:
#   API: 8029
#   Dashboard: 3000
#   Postgres: 5432 (internal)
```

### Environment Variables
```bash
# Add to scripts/kk/.env
ACONTEXT_API_URL=http://localhost:8029/api/v1
ACONTEXT_API_KEY=sk-ac-root-key-from-server-init
ACONTEXT_PROJECT=kk-v2-swarm
```

### Integration with Existing Stack
- **Supabase `kk_swarm_state`**: Keep for real-time agent status (coordinator needs fast reads)
- **Acontext Sessions**: Use for rich conversation history + context engineering
- **IRC**: Keep for human-visible coordination; mirror key events to Acontext
- **DynamoDB Nonce Store**: Unchanged (separate concern)

## 6. Migration Strategy

**Additive, not replacement.** Acontext layers ON TOP of existing infrastructure:

| Component | Current | + Acontext | Notes |
|-----------|---------|------------|-------|
| Agent state | kk_swarm_state (Supabase) | Same | Fast status queries stay in Supabase |
| Conversation history | WORKING.md | Acontext Sessions | Structured, searchable, compressible |
| Agent files | Local filesystem | Acontext Disks | Persistent, cross-agent searchable |
| Skills | `scripts/kk/skills/` dirs | Acontext Skills | Versioned, mountable, shareable |
| Metrics | `aggregate-logs.py` | Acontext Dashboard | Automatic success rate tracking |
| IRC | MeshRelay | Same + Acontext mirror | Key events stored for learning |

## 7. Cost Analysis

- **Self-hosted:** Free (Docker on Mac mini)
- **OpenAI API for observability:** ~$0.01/session (GPT-4.1 for summarization)
- **Storage:** Local Postgres (included in Docker)
- **Total additional cost:** ~$0.50-1.00/day at 24 agents × 2-4 cycles/day

## 8. Open Questions

1. **Docker on Mac mini:** Is Docker daemon configured to auto-start? Need to confirm with Saúl.
2. **OpenAI API key:** Acontext uses GPT-4.1 for observability. Do we have an OpenAI key configured?
3. **Persistence:** Where should Acontext Docker volumes mount? `~/clawd/data/acontext/`?
4. **IRC bridge:** Should IRC messages auto-store in Acontext sessions? Could enable learning from IRC coordination.
5. **Multi-server:** If KK agents run on EC2, should Acontext also be on AWS? Or keep centralized on Mac mini?

---

*This plan bridges the KK V2 swarm infrastructure (24 agents, 9 EM skills, coordinator + services) with Acontext's context management. The key insight: agents need structured memory and context engineering to improve over time, not just task execution loops.*
