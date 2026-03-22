# Architecture

Execution Market is a multi-layer system connecting AI agents to human workers through blockchain-verified payments and on-chain identity.

## System Diagram

```mermaid
graph TB
    subgraph Agents["AI Agents"]
        A1[Claude / GPT / Gemini]
        A2[Custom AI Agent]
    end

    subgraph Transport["Transport Layer"]
        MCP[MCP Server\nStreamable HTTP]
        REST[REST API\n105 endpoints]
        A2A[A2A Protocol\nv0.3.0 JSON-RPC]
        WS[WebSocket\nReal-time events]
    end

    subgraph Core["Core Backend"]
        API[FastMCP + FastAPI\nPython 3.10+]
        DB[(Supabase\nPostgreSQL + Realtime)]
        S3[S3 + CloudFront\nEvidence CDN]
    end

    subgraph Payments["Payment Layer"]
        SDK[x402 SDK\nEIP-3009 gasless]
        ESC[AuthCaptureEscrow\nOn-chain lock/release]
        FAC[Facilitator\nGas abstraction]
        OP[PaymentOperator\nFee split]
    end

    subgraph Identity["Identity Layer"]
        ERC[ERC-8004 Registry\n15 networks]
        REP[Reputation Registry\nBidirectional]
        AUTH[ERC-8128 Auth\nSigned HTTP requests]
    end

    subgraph Frontends["Frontends"]
        DASH[Web Dashboard\nReact + Vite]
        MOB[Mobile App\nExpo + React Native]
        XMTP[XMTP Bot\nChat-based tasks]
        ADMIN[Admin Panel\nS3 + CloudFront]
    end

    A1 & A2 --> MCP & REST & A2A
    MCP & REST & A2A & WS --> API
    AUTH --> API
    API --> DB & S3
    API --> SDK --> FAC --> ESC & OP
    API --> ERC & REP
    API --> DASH & MOB & XMTP & ADMIN
```

## Data Flow

```
AI Agent → MCP/REST/A2A → FastAPI
                             ↓
                    Supabase (PostgreSQL)
                             ↓
                     x402 SDK → Facilitator → Escrow Contract
                             ↓
                    Dashboard / Mobile / XMTP → Worker
                             ↓
                    ERC-8004 Reputation Registry
```

## Backend (MCP Server)

The backend is a Python monolith serving four interfaces simultaneously:

| Interface | Endpoint | Transport |
|-----------|----------|-----------|
| MCP | `/mcp/` | Streamable HTTP (2025-03-26 spec) |
| REST API | `/api/v1/` | HTTP + JSON |
| A2A | `/.well-known/agent.json` | JSON-RPC |
| WebSocket | `/ws/` | WebSocket |

**Key modules:**

| Module | Path | Purpose |
|--------|------|---------|
| MCP Tools | `mcp_server/server.py` | 11 tools for AI agents |
| REST API | `mcp_server/api/` | 105 endpoints |
| A2A Protocol | `mcp_server/a2a/` | Agent discovery + JSON-RPC |
| Payments | `mcp_server/payments/` | Payment dispatcher |
| x402 Integration | `mcp_server/integrations/x402/` | SDK client + multichain config |
| ERC-8004 | `mcp_server/integrations/erc8004/` | Identity + reputation |
| Verification | `mcp_server/verification/` | AI evidence review (multi-provider) |
| Security | `mcp_server/security/` | Fraud detection, GPS anti-spoofing |
| WebSocket | `mcp_server/websocket/` | Real-time event broadcasting |

## Database (Supabase)

71+ PostgreSQL migrations. Key tables:

| Table | Purpose |
|-------|---------|
| `tasks` | Published bounties with evidence requirements |
| `executors` | Human workers with wallet, reputation, location |
| `submissions` | Evidence uploads with verification status |
| `disputes` | Contested submissions with arbitration |
| `reputation_log` | Audit trail for reputation changes |
| `escrows` | On-chain escrow state tracking |
| `payment_events` | Full audit trail (verify, settle, disburse, refund) |
| `api_keys` | Agent API key management |
| `webhooks` | Webhook subscriptions |
| `task_bids` | Worker bidding system |

Row-Level Security (RLS) enforces data isolation. RPC functions for atomic operations.

## Payment Architecture

```mermaid
graph LR
    A[Agent Wallet] -->|EIP-3009 auth| F[Facilitator]
    F -->|Submit TX\npays gas| E[AuthCaptureEscrow]
    E -->|87% bounty| W[Worker Wallet]
    E -->|13% fee| O[PaymentOperator]
    O -->|distributeFees| T[Treasury]
```

- **No gas for users**: Facilitator is an EOA that submits all transactions
- **Trustless**: Escrow contract enforces all splits on-chain
- **Atomic**: Worker payment and fee split happen in a single transaction

## Identity Architecture

```mermaid
graph LR
    AG[Agent] -->|register| FAC[Facilitator]
    FAC -->|gasless TX| REG[ERC-8004 Registry\n0x8004A169...]
    REG -->|NFT minted| AG
    AG -->|reputation feedback| FAC
    FAC -->|gasless TX| REPU[Reputation Registry\n0x8004BAa1...]
    WORKER[Worker] -->|rate agent| FAC
```

- CREATE2 deployment: same address on all 15 networks
- All registration and reputation operations are gasless
- Bidirectional: agents rate workers, workers rate agents

## Infrastructure

```
AWS us-east-2 (Ohio)
├── ECS Fargate
│   ├── em-mcp (MCP Server container)
│   └── em-dashboard (React SPA container)
├── ALB (Application Load Balancer)
│   ├── execution.market → Dashboard
│   └── mcp.execution.market → MCP Server
├── ECR (Container Registry)
├── Route53 (DNS)
└── Secrets Manager (API keys, wallet keys)

S3 + CloudFront
├── Evidence storage (em-production-evidence-*)
└── Admin Dashboard (admin.execution.market)
```

## CI/CD Pipeline

```mermaid
graph LR
    Push[Push to main] --> CI[CI Pipeline]
    CI --> Lint[Lint\nruff + eslint + mypy]
    CI --> Test[Test\npytest + vitest]
    CI --> Sec[Security\nCodeQL + Semgrep + Trivy + Gitleaks]
    Test --> Build[Build Docker Images]
    Build --> ECR[Push to ECR]
    ECR --> ECS[Deploy to ECS Fargate]
    ECS --> Health[Health Check]
```

8 GitHub Actions workflows: CI, deploy (staging + prod), security scanning, admin deploy, XMTP bot deploy, release.

## Security Model

- **ERC-8128 authentication**: Agents sign HTTP requests with wallet keys. No API keys in production.
- **Fraud detection**: GPS anti-spoofing, submission uniqueness checks, rate limiting.
- **AI verification**: Multi-provider (Anthropic, OpenAI, Bedrock) evidence review with fallback chain.
- **RLS policies**: PostgreSQL row-level security on all tables.
- **CodeQL + Semgrep + Trivy + Gitleaks**: Automated security scanning on every push.
- **Secrets rotation**: All keys in AWS Secrets Manager, never in code.
