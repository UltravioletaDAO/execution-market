# KarmaCadabra Swarm — AWS Terraform Architecture

> **STATUS**: Implementation (2026-02-15)
> **Author**: Clawd (Dream Session)
> **Branch**: `feat/karmacadabra-swarm`
> **Prerequisites**: [KARMACADABRA_V2_ARCHITECTURE.md](./KARMACADABRA_V2_ARCHITECTURE.md)

---

## 1. Overview

This document describes the **Terraform-based deployment system** for deploying
multiple OpenClaw AI agents on AWS ECS Fargate. The system is designed to deploy
5 to 200 agents programmatically with a **single input**: the Anthropic API key.

### Design Principles

1. **One input** — The deployer provides only the Anthropic API key
2. **Sequential deployment** — Agents deploy in configurable batches, not all at once
3. **Unique personalities** — Each agent gets a distinct SOUL.md, identity, and config
4. **Cost optimized** — Fargate Spot instances, minimal resources per agent
5. **State persistence** — Agent memory survives container restarts via S3
6. **Security first** — API keys in AWS Secrets Manager, never in code

---

## 2. Architecture

### 2.1 High-Level View

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AWS (us-east-2)                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    VPC (10.0.0.0/16)                           │  │
│  │                                                                │  │
│  │  ┌──────────────────┐    ┌──────────────────┐                 │  │
│  │  │  Public Subnet 1 │    │  Public Subnet 2 │                 │  │
│  │  │   10.0.1.0/24    │    │   10.0.2.0/24    │                 │  │
│  │  │   [NAT Gateway]  │    │                  │                 │  │
│  │  └──────────────────┘    └──────────────────┘                 │  │
│  │                                                                │  │
│  │  ┌──────────────────┐    ┌──────────────────┐                 │  │
│  │  │  Private Subnet 1│    │  Private Subnet 2│                 │  │
│  │  │   10.0.10.0/24   │    │   10.0.11.0/24   │                 │  │
│  │  │                  │    │                  │                 │  │
│  │  │  ┌────────────┐  │    │  ┌────────────┐  │                 │  │
│  │  │  │ Agent-000  │  │    │  │ Agent-003  │  │                 │  │
│  │  │  │ "aurora"   │  │    │  │ "drift"    │  │                 │  │
│  │  │  │ Explorer   │  │    │  │ Analyst    │  │                 │  │
│  │  │  └────────────┘  │    │  └────────────┘  │                 │  │
│  │  │  ┌────────────┐  │    │  ┌────────────┐  │                 │  │
│  │  │  │ Agent-001  │  │    │  │ Agent-004  │  │                 │  │
│  │  │  │ "blaze"    │  │    │  │ "echo"     │  │                 │  │
│  │  │  │ Builder    │  │    │  │ Creator    │  │                 │  │
│  │  │  └────────────┘  │    │  └────────────┘  │                 │  │
│  │  │  ┌────────────┐  │    │                  │                 │  │
│  │  │  │ Agent-002  │  │    │                  │                 │  │
│  │  │  │ "cipher"   │  │    │                  │                 │  │
│  │  │  │ Connector  │  │    │                  │                 │  │
│  │  │  └────────────┘  │    │                  │                 │  │
│  │  └──────────────────┘    └──────────────────┘                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐    │
│  │  ECS Cluster │  │ Secrets Manager  │  │    S3 Bucket         │    │
│  │ kk-swarm-   │  │ anthropic-api-key│  │  agent-state/        │    │
│  │ production   │  └──────────────────┘  │  ├─ aurora/memory/   │    │
│  └─────────────┘                         │  ├─ blaze/memory/    │    │
│                                          │  └─ cipher/memory/   │    │
│  ┌──────────────────┐                    └──────────────────────┘    │
│  │ ECR Repository   │                                                │
│  │ openclaw-agent   │  ┌──────────────────┐                          │
│  │ :latest          │  │ CloudWatch Logs  │                          │
│  └──────────────────┘  │ /ecs/kk-swarm    │                          │
│                         └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Per-Agent Architecture

Each agent is an ECS Fargate task running a container with:

```
┌─────────────────────────────────────────────┐
│            Fargate Task (Agent)              │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │          OpenClaw Container           │  │
│  │                                       │  │
│  │  /agent/workspace/                    │  │
│  │  ├── SOUL.md         (personality)    │  │
│  │  ├── IDENTITY.md     (unique ID)      │  │
│  │  ├── AGENTS.md       (instructions)   │  │
│  │  ├── USER.md         (context)        │  │
│  │  ├── TOOLS.md        (tool config)    │  │
│  │  ├── MEMORY.md       (long-term)      │  │
│  │  ├── memory/         (daily notes)    │  │
│  │  └── .openclaw.json  (runtime config) │  │
│  │                                       │  │
│  │  Processes:                           │  │
│  │  ├── OpenClaw Gateway (:18789)        │  │
│  │  └── S3 Sync (every 5 min)           │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  CPU: 0.25 vCPU  │  Memory: 512 MiB        │
│  Spot: enabled   │  Platform: linux/arm64   │
└─────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
  Anthropic API          S3 State Bucket
  (Claude Haiku)         (memory persistence)
```

---

## 3. File Structure

```
terraform/swarm/
├── main.tf                          # Provider, VPC, ECS cluster, IAM, S3
├── variables.tf                     # All variables (only API key required)
├── outputs.tf                       # Deployment info + cost estimates
├── Dockerfile                       # Agent container image
│
├── modules/
│   └── agent/
│       ├── main.tf                  # Per-agent: task def, service
│       ├── variables.tf             # Agent-specific vars
│       └── outputs.tf               # Agent outputs
│
├── templates/
│   ├── README.md                    # Personality template guide
│   ├── soul-explorer.md             # Explorer archetype
│   └── soul-builder.md              # Builder archetype
│
└── scripts/
    ├── deploy.sh                    # Main deployment script
    ├── entrypoint.sh                # Container entrypoint
    ├── bootstrap-workspace.sh       # Workspace generator
    └── sync-state.sh                # S3 state sync
```

---

## 4. Deployment Flow

### 4.1 Sequential Deployment

Agents are deployed in configurable batches to avoid overwhelming the system:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Batch 1 │───►│ Batch 2 │───►│ Batch 3 │───►│ Batch N │
│ 5 agents│    │ 5 agents│    │ 5 agents│    │remaining│
│         │    │         │    │         │    │         │
│ 30s     │    │ 30s     │    │ 30s     │    │ done    │
│ cooldown│    │ cooldown│    │ cooldown│    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### 4.2 Deploy Command

```bash
# Phase 0: 5 agents (~$104/mo)
./scripts/deploy.sh --api-key sk-ant-xxx

# Phase 1: 55 agents (~$250/mo with Spot)
./scripts/deploy.sh --api-key sk-ant-xxx --agents 55 --batch 5

# Phase 2: 200 agents (~$800/mo with Spot)
./scripts/deploy.sh --api-key sk-ant-xxx --agents 200 --batch 10
```

### 4.3 What Happens

1. **Prerequisites check** — Terraform, AWS CLI, Docker, jq
2. **Terraform init** — Initialize providers
3. **Docker build** — Build OpenClaw agent image, push to ECR
4. **Batch loop** — For each batch:
   a. `terraform apply` with increasing `agent_count`
   b. Wait 30 seconds for services to stabilize
   c. Move to next batch
5. **Output** — Show deployment summary and cost estimates

---

## 5. Cost Analysis

### 5.1 Phase 0 — 5 Agents (~$104/mo target)

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| **ECS Fargate Spot** | $18.30 | 5 × 0.25 vCPU × 512 MiB × 730h × 0.3 (Spot) |
| **NAT Gateway** | $32.40 | 1 NAT × $0.045/h × 730h |
| **NAT Data** | ~$5.00 | API calls, S3 sync |
| **S3 Storage** | ~$1.00 | Memory files, minimal |
| **CloudWatch** | ~$2.00 | Log storage |
| **Secrets Manager** | $0.40 | 1 secret |
| **ECR** | ~$1.00 | Image storage |
| **LLM API (Haiku)** | ~$2.00 | 5 agents × $0.003/day × 30 |
| **Total** | **~$62/mo** | Well under $104 target |

### 5.2 Phase 1 — 55 Agents

| Component | Monthly Cost |
|-----------|-------------|
| ECS Fargate Spot | $201 |
| NAT Gateway + Data | $42 |
| S3 + CloudWatch | $8 |
| Secrets + ECR | $2 |
| LLM API (Haiku) | $5 |
| **Total** | **~$258/mo** |

### 5.3 Phase 2 — 200 Agents

| Component | Monthly Cost |
|-----------|-------------|
| ECS Fargate Spot | $732 |
| NAT Gateway + Data | $55 |
| S3 + CloudWatch | $20 |
| Secrets + ECR | $2 |
| LLM API (Haiku) | $18 |
| **Total** | **~$827/mo** |

### 5.4 Cost Optimization Strategies

| Strategy | Savings | Applied |
|----------|---------|---------|
| **Fargate Spot** | 70% on compute | ✅ Default |
| **0.25 vCPU** per agent | 75% vs 1 vCPU | ✅ Default |
| **Single NAT Gateway** | 50% vs multi-AZ NAT | ✅ Default |
| **Haiku model** | 95% vs Sonnet | ✅ Default |
| **Log retention 14d** | vs 30d+ | ✅ Default |
| **S3 lifecycle** | Auto-archive old memory | ✅ Configured |
| **VPC endpoints** (future) | Eliminate NAT for S3/ECR | 🔜 Phase 1 |

---

## 6. Agent Identity System

### 6.1 Naming

Each agent gets a unique name from a deterministic list of 200+ names:

| Index | Name | Personality |
|-------|------|-------------|
| 0 | aurora | Explorer |
| 1 | blaze | Builder |
| 2 | cipher | Connector |
| 3 | drift | Analyst |
| 4 | echo | Creator |
| 5 | flux | Strategist |
| ... | ... | ... |

Names cycle through 8 personality archetypes:
1. **Explorer** — curious, adventurous, open-minded
2. **Builder** — methodical, persistent, detail-oriented
3. **Connector** — empathetic, social, collaborative
4. **Analyst** — analytical, skeptical, data-driven
5. **Creator** — creative, expressive, visionary
6. **Strategist** — strategic, patient, calculating
7. **Educator** — patient, knowledgeable, articulate
8. **Maverick** — bold, unconventional, risk-taking

### 6.2 Workspace Files

Each agent receives at container start:

| File | Source | Purpose |
|------|--------|---------|
| `SOUL.md` | Generated from personality template | Who the agent is |
| `IDENTITY.md` | Generated from name + index | Agent metadata |
| `AGENTS.md` | Shared template with per-agent vars | Instructions |
| `USER.md` | Shared template | Deployer context |
| `TOOLS.md` | Generated | Tool configuration |
| `MEMORY.md` | Restored from S3 | Long-term memory |
| `memory/*.md` | Restored from S3 | Daily session notes |

### 6.3 Future: Chat-Log Personalities

For KK v2 production, personalities should be sourced from Karma-Hello:

```
Chat Logs → Karma-Hello → Voice-Extractor → SOUL.md
                        → Skill-Extractor → SOUL.md (skills section)
```

The `soul_templates` variable in `variables.tf` accepts custom personality objects.

---

## 7. State Persistence

### 7.1 S3 Structure

```
s3://kk-swarm-agent-state-{account_id}/
├── agents/
│   ├── aurora/
│   │   ├── memory/
│   │   │   ├── 2026-02-15.md
│   │   │   └── 2026-02-16.md
│   │   ├── MEMORY.md
│   │   └── data/
│   ├── blaze/
│   │   ├── memory/
│   │   └── MEMORY.md
│   └── cipher/
│       ├── memory/
│       └── MEMORY.md
```

### 7.2 Sync Lifecycle

```
Container Start → Restore from S3 → Run Agent → Sync every 5 min → Graceful shutdown sync
```

On Fargate Spot interruption (2-minute warning):
1. SIGTERM received
2. Entrypoint trap fires
3. Final S3 sync
4. Container stops
5. ECS reschedules → new container restores from S3

---

## 8. Scaling Architecture

### 8.1 How 5 → 55 → 200 Works

```
Phase 0 (5 agents):
  terraform apply -var="agent_count=5"
  → 5 ECS services, 5 Fargate tasks
  → ~$62/mo

Phase 1 (55 agents):
  terraform apply -var="agent_count=55"
  → Terraform adds 50 new services (existing 5 untouched)
  → ~$258/mo

Phase 2 (200 agents):
  terraform apply -var="agent_count=200"
  → Terraform adds 145 new services
  → ~$827/mo
```

### 8.2 Scaling Considerations

| Concern | Solution |
|---------|----------|
| **Fargate service limit** (default 500) | Fine up to 200. Request increase for 500+ |
| **NAT Gateway bandwidth** | Single NAT handles 45 Gbps — no bottleneck |
| **S3 request rate** | 5,500 PUT/s — plenty for 200 agents syncing every 5 min |
| **Anthropic rate limits** | Haiku: 50 RPM per key → stagger agent actions with cron offsets |
| **CloudWatch log volume** | Lifecycle policy, consider S3 export for 200+ agents |
| **Terraform state size** | ~200 resources for 200 agents — manageable |

### 8.3 Beyond 200 Agents

For 200+ agents, consider:

1. **Multiple ECS clusters** — One per region or per 100 agents
2. **VPC endpoints** — Eliminate NAT costs for S3/ECR/Secrets Manager
3. **EFS** instead of S3 — Shared filesystem for inter-agent data
4. **Service mesh** — App Mesh for inter-agent communication
5. **Multiple API keys** — Spread across Anthropic rate limits

---

## 9. Security

### 9.1 Secrets Management

| Secret | Storage | Access |
|--------|---------|--------|
| Anthropic API key | AWS Secrets Manager | ECS execution role |
| AWS credentials | IAM task role (no keys) | Automatic |
| Agent workspace | S3 with SSE-AES256 | ECS task role |

### 9.2 Network Security

- Agents run in **private subnets** (no public IPs)
- Outbound only via **NAT Gateway** (no inbound from internet)
- Security group allows **egress only** (HTTPS to APIs)
- No ALB or public endpoints (agents are autonomous, not serving)

### 9.3 IAM Principle of Least Privilege

| Role | Permissions |
|------|-------------|
| ECS Execution | Pull ECR images, read secrets, write logs |
| ECS Task | Read/write own S3 prefix only |

---

## 10. Monitoring

### 10.1 CloudWatch

- **Log group**: `/ecs/kk-swarm` with per-agent stream prefix
- **Retention**: 14 days (configurable)
- **Container Insights**: Optional ($3/mo) for CPU/memory metrics

### 10.2 Recommended Alarms (Future)

| Alarm | Condition | Action |
|-------|-----------|--------|
| Agent stopped | ECS service desired=1, running=0 | SNS notification |
| High memory | Memory > 80% for 5 min | Scale up agent memory |
| API errors | 5xx errors in logs > 10/min | Alert + investigate |
| S3 sync failure | "Failed to sync" in logs | Alert |
| Spot interruption | Task stopped by Spot reclaim | Auto-restart (ECS handles) |

---

## 11. Comparison: AWS vs Cherry Servers

The original KK v2 architecture proposed Cherry Servers. This implementation
uses AWS for several advantages:

| Factor | AWS ECS Fargate | Cherry Servers |
|--------|----------------|----------------|
| **Setup time** | `terraform apply` (5 min) | Manual server setup + Ansible |
| **Scaling** | Change `agent_count`, apply | New servers, rebalance agents |
| **Cost (5 agents)** | ~$62/mo | ~$15/mo |
| **Cost (55 agents)** | ~$258/mo | ~$30/mo (2 servers) |
| **Cost (200 agents)** | ~$827/mo | ~$60/mo (4 servers) |
| **Reliability** | 99.99% SLA, auto-restart | Manual recovery |
| **Security** | Secrets Manager, IAM, VPC | Manual key management |
| **State persistence** | S3 automatic | Manual backup |
| **Monitoring** | CloudWatch built-in | Manual setup |
| **Maintenance** | Zero (managed service) | OS updates, Docker updates |
| **Flexibility** | Per-agent scaling | Per-server scaling |

**Recommendation**: Use **AWS for Phase 0-1** (ease of deployment, reliability,
Terraform automation). Consider **Cherry for Phase 2+** if cost becomes critical
and the team is comfortable with server management.

---

## 12. Roadmap

### Phase 0 — MVP (Week 1)
- [x] Terraform architecture design
- [x] Per-agent module with personality system
- [x] Sequential deployment script
- [x] S3 state persistence
- [ ] Build and test Docker image
- [ ] Deploy 5 agents on AWS
- [ ] Validate agent startup and S3 sync

### Phase 1 — Integration (Week 2-3)
- [ ] Connect agents to Execution Market API
- [ ] Add EM skill to agent workspaces
- [ ] Inter-agent communication via sessions
- [ ] Scale to 55 agents
- [ ] Add VPC endpoints to reduce NAT costs

### Phase 2 — Full Swarm (Week 4-6)
- [ ] Chat-log personality extraction pipeline
- [ ] MeshRelay IRC integration
- [ ] Scale to 200 agents
- [ ] Multi-region deployment
- [ ] Cost optimization audit

### Phase 3 — Autonomy (Ongoing)
- [ ] Agents publish own tasks
- [ ] Self-funding via EM earnings
- [ ] Auto-scaling based on activity
- [ ] Community dashboard

---

## 13. Quick Start

```bash
# 1. Clone and navigate
cd terraform/swarm

# 2. Deploy 5 agents (only input: API key)
./scripts/deploy.sh --api-key sk-ant-your-key-here

# 3. Check status
./scripts/deploy.sh --status

# 4. Scale up
./scripts/deploy.sh --api-key sk-ant-your-key-here --agents 55

# 5. Tear down
./scripts/deploy.sh --destroy
```

That's it. One command, one input, autonomous agents. 🪄
