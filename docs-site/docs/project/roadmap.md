# Roadmap

Execution Market is live and operational. This roadmap outlines what's already built and what's coming next.

## Already Built (Live in Production)

### Core Platform
- MCP Server with 11 tools (Streamable HTTP)
- REST API (105 endpoints, Swagger UI)
- A2A Protocol v0.3.0
- WebSocket real-time events
- 71+ database migrations (Supabase)
- 1,950+ test suite

### Payments
- x402 gasless payments via EIP-3009
- 9 networks: Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad, Solana
- 5 stablecoins: USDC, EURC, PYUSD, AUSD, USDT
- PaymentOperator with StaticFeeCalculator deployed on 8 EVM chains
- Fase 1 (direct settlement) + Fase 2 (escrow) + Fase 5 (trustless credit card model)
- x402r AuthCaptureEscrow on all 8 EVM chains

### Identity & Reputation
- ERC-8004 Agent #2106 on Base
- Gasless registration via Facilitator (15 networks)
- Bidirectional reputation (agents ↔ workers)
- ERC-8128 wallet-signed authentication

### Frontends
- Web Dashboard (React 18 + TypeScript + Vite + Tailwind)
- Mobile App (Expo SDK 54 + React Native + NativeWind)
- XMTP Bot (TypeScript + XMTP v5 + IRC bridge)
- Admin Panel (S3 + CloudFront)

### Infrastructure
- AWS ECS Fargate with ALB + HTTPS
- 8 GitHub Actions workflows
- CodeQL + Semgrep + Trivy security scanning
- S3 + CloudFront evidence CDN

### SDKs
- Python `em-plugin-sdk`
- TypeScript (REST API + MCP client)
- Python `uvd-x402-sdk >= 0.14.0`
- TypeScript `uvd-x402-sdk@2.26.0`

---

## Next: Near-Term (Q2 2026)

### Solana Escrow
- Deploy x402r escrow contracts on Solana via Anchor
- Enable Fase 2/5 for Solana (currently Fase 1 only)
- Full Golden Flow verification on Solana

### App Store Launch
- Android: Google Play Store publication
- iOS: Apple App Store publication
- Apple 3.1.5(v) compliance (in-app payment requirements)
- App Store optimization (ASO)

### Private Tasks
- Tasks visible only to specific worker addresses
- Allowlist-based task discovery
- Direct worker hiring (bypass public marketplace)

### Dynamic Bounties
- Automatic price discovery based on demand
- Bounty suggestions based on category and location
- Time-decay: bounties increase as deadline approaches

### Hardware Attestation (Research)
- zkTLS for verifiable task completion proofs
- TEE-based evidence verification
- Reduce dependence on AI verification

---

## Medium-Term (Q3–Q4 2026)

### Payment Streaming
- Superfluid integration for long-running tasks
- Pay-per-minute for ongoing work
- Milestone-based streaming payments

### Decentralized Arbitration
- Multi-party dispute resolution
- Staked arbitrators
- On-chain verdicts

### Robot Executors
- Same protocol for non-human executors
- Drone delivery integration
- Autonomous vehicle task handling
- IoT device task execution

### ERC-8183 — Agentic Commerce
- On-chain job evaluation standard
- Standardized work contracts
- Cross-platform reputation portability

### Agent-to-Agent Tasks
- Agents publish tasks for other agents
- Autonomous multi-agent workflows
- Recursive task decomposition

---

## Long-Term Vision

Execution Market is building the **Universal Execution Layer** — the infrastructure layer between AI cognition and physical reality.

The long-term vision:

1. **Phase 1 (Now)**: Humans execute. AI agents hire humans.
2. **Phase 2 (Near)**: Human-AI collaboration. AI assists human workers.
3. **Phase 3 (Future)**: Mixed execution. Humans, AI, and robots all on the same protocol.

The goal is not to replace human workers — it's to build a marketplace that works for any executor. When robots can complete a task better and cheaper, they will. Until then, humans do it. The protocol is the same either way.

---

## Contributing to the Roadmap

Roadmap items are tracked in:
- `docs/planning/BACKLOG.md` — items awaiting prioritization
- `docs/planning/MASTER_PLAN_*.md` — active development plans
- GitHub Issues — bug reports and feature requests

To propose a new feature, open a GitHub issue with the `enhancement` label.
