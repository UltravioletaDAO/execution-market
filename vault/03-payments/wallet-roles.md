---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - wallet architecture
  - key wallets
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/integrations/x402/payment_dispatcher.py
---

# Wallet Roles

Execution Market uses **5 distinct wallets**, each with a specific role. Mixing wallet purposes causes fund loss or security issues.

## Wallet Directory

### 1. Dev Wallet (`0x857f...`)
- **Purpose**: Local development scripts and tests
- **Key location**: `.env.local` (`WALLET_PRIVATE_KEY`)
- **Funded on**: All test networks
- **Risk level**: Low (test funds only)

### 2. Platform Wallet (`0xD386...`)
- **Purpose**: Production MCP server, settlement transit point
- **Key location**: AWS Secrets Manager `em/x402:PRIVATE_KEY`
- **Role**: Agent funds settle here at approval (Fase 1/2), then immediately disburse to worker (87%) + [[treasury]] (13%)
- **Funds should NOT accumulate** here long-term
- **ECS env var**: `WALLET_PRIVATE_KEY`

### 3. Treasury (`0xae07...`)
- **Purpose**: Cold storage for platform fees
- **Key location**: Ledger hardware wallet (manual signing only)
- **ONLY receives**: 13% [[platform-fee]] on successful completion
- **NEVER a settlement target** — see [[treasury]]

### 4. Test Worker (`0x52E0...`)
- **Purpose**: E2E testing (worker-side operations, reputation signing)
- **Key location**: AWS Secrets Manager `em/test-worker:private_key`
- **Used by**: Golden Flow for worker->agent reputation
- **ECS env var**: `EM_WORKER_PRIVATE_KEY`

### 5. Facilitator EOA (`0x1030...`)
- **Full address**: `0x103040545AC5031A11E8C03dd11324C7333a13C7`
- **Purpose**: Pays gas for all [[facilitator]] transactions
- **Funded on**: All 15 supported networks (native tokens for gas)
- **Managed by**: Ultravioleta DAO (our [[facilitator]] server)

## Security Notes

- **NEVER show private keys** in terminal output or logs (user is always streaming)
- Use AWS Secrets Manager for production keys
- Dev wallet key in `.env.local` only (never committed)
- To verify a key exists without exposing it: `echo "KEY is ${VAR:+set}"`

## Related Concepts

- [[treasury]] — detailed rules for the cold wallet
- [[facilitator]] — uses the Facilitator EOA for gas
- [[aws-secrets-manager]] — where production keys are stored
- [[fase-1-direct-settlement]] — no intermediary, agent pays worker and treasury directly
- [[fase-5-trustless]] — platform wallet never touches funds
