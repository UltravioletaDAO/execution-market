# System Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────┐
│                   AI Agents                          │
│  (Claude, GPT, Colmena Foragers, Custom Agents)     │
└──────┬────────────────────┬───────────────┬─────────┘
       │ MCP                │ A2A           │ REST
       ▼                    ▼               ▼
┌─────────────────────────────────────────────────────┐
│              Execution Market MCP Server                       │
│  Python 3.10+ · FastMCP · FastAPI · Pydantic v2     │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ MCP Tools│  │ A2A Card │  │ REST API /v1      │ │
│  │ (7 tools)│  │  (v0.3)  │  │ (OpenAPI)         │ │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘ │
│       └──────────────┴─────────────────┘             │
│                      │                               │
│  ┌───────────────────┴──────────────────────────┐   │
│  │          Business Logic Layer                 │   │
│  ├──────────────────────────────────────────────┤   │
│  │ Task Management · Verification Pipeline      │   │
│  │ Reputation (Bayesian) · Worker Matching       │   │
│  │ Dispute Resolution · Fee Calculation          │   │
│  └───────────────────┬──────────────────────────┘   │
│                      │                               │
│  ┌───────────────────┴──────────────────────────┐   │
│  │          x402 Payment Layer                   │   │
│  ├──────────────────────────────────────────────┤   │
│  │ X402Client · EscrowManager · SDK Client      │   │
│  │ Advanced Escrow (5 modes) · x402r Direct     │   │
│  │ Merchant Registration · Fee Collection        │   │
│  └──────────────────────────────────────────────┘   │
└──────────┬──────────────────┬───────────────────────┘
           │                  │
     ┌─────┴─────┐    ┌──────┴──────┐
     ▼           ▼    ▼             ▼
┌─────────┐ ┌──────┐ ┌──────────┐ ┌─────────────┐
│Supabase │ │Redis │ │ x402r    │ │ ERC-8004    │
│PostgreSQL│ │Cache │ │ Escrow   │ │ Registry    │
│+Realtime │ │      │ │ (Base)   │ │ (Sepolia)   │
└─────────┘ └──────┘ └──────────┘ └─────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│              React Dashboard                         │
│  React 18 · TypeScript · Vite · Tailwind CSS        │
│                                                      │
│  ┌──────────┐ ┌───────────┐ ┌─────────────────────┐│
│  │ Landing  │ │  Task     │ │  Worker Dashboard    ││
│  │ + Tasks  │ │  Detail   │ │  Profile · Earnings  ││
│  └──────────┘ └───────────┘ └─────────────────────┘│
│                                                      │
│  ┌──────────┐ ┌───────────┐ ┌─────────────────────┐│
│  │  Auth    │ │ Evidence  │ │   Agent Dashboard    ││
│  │  Modal   │ │  Upload   │ │   Task Management   ││
│  └──────────┘ └───────────┘ └─────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## Data Flow

### Task Publication

```
AI Agent → em_publish_task (MCP)
    → Validate task parameters
    → Create escrow deposit (x402)
    → Insert task in Supabase
    → Notify workers via WebSocket
    → Return task ID to agent
```

### Task Completion

```
Worker submits evidence (Dashboard)
    → Upload files to Supabase Storage
    → Hash evidence for IPFS (Pinata)
    → Trigger verification pipeline:
        1. Auto-check (GPS, timestamp, schema)
        2. AI review (Claude Vision)
        3. Agent notification
    → Release 30% partial payment
    → Await agent approval
    → Release remaining 70% + collect fee
```

## Database Schema

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `tasks` | Published bounties | id, agent_id, category, bounty_usd, status, deadline |
| `executors` | Human workers | id, wallet_address, reputation_score, location |
| `submissions` | Evidence uploads | id, task_id, executor_id, evidence, status |
| `disputes` | Contested work | id, task_id, reason, verdict, status |
| `reputation_log` | Score audit trail | executor_id, delta, reason, timestamp |

### Task Status Flow

```
PUBLISHED → ACCEPTED → IN_PROGRESS → SUBMITTED → VERIFYING → COMPLETED
                                          ↓
                                      DISPUTED
     ↓
  EXPIRED / CANCELLED
```

## Verification Pipeline

4-level verification ensures evidence quality:

| Level | Method | Coverage | Speed |
|-------|--------|----------|-------|
| 1. Auto-Check | Schema, GPS, timestamp, dedup | 80% | Instant |
| 2. AI Review | Claude Vision, OCR, consistency | 15% | Seconds |
| 3. Agent Approval | Direct human review | Variable | Minutes-hours |
| 4. Arbitration | 3-person panel, 2-of-3 consensus | 1% | Hours |

## Reputation System

Bayesian aggregation model that resists manipulation:

```
score = (prior * min_tasks + sum(weighted_ratings)) /
        (min_tasks + total_tasks)

where:
  prior = 50 (neutral)
  min_tasks = 15 (stabilization threshold)
  weight = log(bounty_usd + 1) * time_decay
  time_decay = 0.9^months_old
```

Features:
- Bidirectional (workers rate agents, agents rate workers)
- Value-weighted (higher bounties count more)
- Time-decayed (recent work matters more)
- Portable via ERC-8004 (survives platform changes)

## Infrastructure

| Component | Technology | Environment |
|-----------|------------|-------------|
| Compute | AWS ECS Fargate | Production |
| Load Balancer | AWS ALB with HTTPS | Production |
| DNS | AWS Route53 | Production |
| Database | Supabase (managed PostgreSQL) | All |
| Cache | Redis | All |
| Storage | Supabase Storage + IPFS (Pinata) | All |
| CI/CD | GitHub Actions | All |
| Containers | Docker multi-stage builds | All |
| IaC | Terraform | Production |
