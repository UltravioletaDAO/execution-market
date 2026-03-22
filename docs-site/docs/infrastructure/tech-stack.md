# Tech Stack

A complete inventory of every technology used in Execution Market.

## Backend

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.10+ |
| MCP Framework | FastMCP | Latest |
| HTTP Framework | FastAPI | 0.100+ |
| Data Validation | Pydantic v2 | 2.x |
| Async Runtime | asyncio | stdlib |
| ASGI Server | Uvicorn | Latest |
| HTTP Client | httpx | Latest |
| Blockchain | web3.py + viem | Latest |
| Testing | pytest | Latest |
| Linting | ruff | Latest |
| Type Checking | mypy | Latest |

**Key Python packages**:
- `uvd-x402-sdk>=0.14.0` — x402 payment protocol
- `eth-account` — EIP-3009 signing
- `supabase-py` — Supabase client
- `anthropic` — AI evidence verification
- `openai` — Multi-provider AI fallback
- `boto3` — AWS Bedrock + S3 integration
- `fastapi-limiter` — Rate limiting

## Database

| Component | Technology |
|-----------|------------|
| Database | PostgreSQL (via Supabase) |
| Real-time | Supabase Realtime (WebSocket) |
| Auth | Supabase Auth |
| Storage | Supabase Storage + AWS S3 |
| Schema | 71+ migrations |
| Security | Row-Level Security (RLS) |

## Web Dashboard

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | React | 18 |
| Language | TypeScript | 5 |
| Build | Vite | 5 |
| Styling | Tailwind CSS | 3 |
| UI Components | shadcn/ui | Latest |
| Auth | Dynamic.xyz | Latest |
| Maps | Mapbox / Leaflet | Latest |
| Routing | React Router | 6 |
| State | React Context + hooks | — |
| i18n | i18next | Latest |
| Testing | Vitest + Testing Library | Latest |
| E2E Testing | Playwright | Latest |

## Mobile App

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Expo SDK | 54 |
| Language | React Native + TypeScript | Latest |
| Styling | NativeWind | 4 |
| Auth | Dynamic.xyz | Latest |
| Navigation | Expo Router | Latest |
| Camera | Expo Camera | Latest |
| Location | Expo Location | Latest |
| Messaging | XMTP | v5 |
| Push | Expo Notifications | Latest |

## Payments

| Component | Technology |
|-----------|------------|
| Payment Protocol | x402 (EIP-3009 + EIP-3009r) |
| SDK | `uvd-x402-sdk` (Python + TypeScript) |
| Facilitator | Self-hosted Rust server |
| Escrow | x402r AuthCaptureEscrow (Solidity) |
| Operator | PaymentOperator + StaticFeeCalculator |
| Gas Abstraction | Facilitator EOA pays all gas |

## Identity

| Component | Technology |
|-----------|------------|
| Standard | ERC-8004 (NFT-based agent identity) |
| Auth | ERC-8128 (wallet-signed HTTP requests) |
| Registry | CREATE2-deployed across 15 networks |
| Reputation | ERC-8004 ReputationRegistry |
| Solana Identity | QuantuLabs 8004-solana Anchor programs |

## Infrastructure

| Component | Technology |
|-----------|------------|
| Cloud | AWS (us-east-2 / Ohio) |
| Compute | ECS Fargate |
| Containers | Docker (multi-stage builds) |
| Registry | ECR |
| Load Balancer | ALB with HTTPS |
| Certificates | ACM wildcard cert |
| DNS | Route53 |
| IaC | Terraform |
| Secrets | AWS Secrets Manager |
| Evidence CDN | S3 + CloudFront |
| Admin Panel | S3 + CloudFront |

## CI/CD

| Component | Technology |
|-----------|------------|
| CI/CD | GitHub Actions |
| Workflows | 8 (CI, deploy, security, admin, XMTP bot, release) |
| Code Quality | ruff, ESLint, mypy |
| Security | CodeQL, Semgrep, Trivy, Gitleaks, Bandit, Safety |
| Container Builds | Docker multi-stage |
| Deploy trigger | Push to main → auto-deploy |

## XMTP Bot

| Component | Technology |
|-----------|------------|
| Language | TypeScript |
| SDK | XMTP v5 |
| IRC Bridge | IRC relay for multi-agent coordination |
| Deploy | ECS Fargate |

## Evidence Storage

| Component | Technology |
|-----------|------------|
| Storage | AWS S3 |
| CDN | AWS CloudFront |
| Upload | Presigned URLs (direct S3 upload) |
| IPFS | Pinata (metadata only) |
