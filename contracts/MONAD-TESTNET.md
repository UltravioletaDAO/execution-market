# Execution Market — Monad Testnet Deployment

**Deployed:** February 10, 2026  
**Network:** Monad Testnet (Chain ID: 10143)  
**RPC:** `https://testnet-rpc.monad.xyz`  
**Explorer:** `https://testnet.monadexplorer.com`

---

## Deployed Contracts

| Contract | Address | Description |
|----------|---------|-------------|
| **ChambaEscrow v1.4.0** | `0x6Ed128Cfc496A97a8eA8F3b2ee2350201bbF8Ec8` | Trustless escrow for human-executed tasks |
| **MockUSDC** | `0xe0e74E36D3C342ef610a0C6871DbcEaa4d6Eeb80` | ERC-20 stablecoin (6 decimals) for testing |

### Also Deployed: describe-net (Reputation Layer)

| Contract | Address | Description |
|----------|---------|-------------|
| **SealRegistry** | `0xAb06ADC19cb16728bd53755B412BadeE73335D10` | On-chain reputation seals (ERC-8004 compatible) |
| **MockIdentityRegistry** | `0xdF93dA72C2B58A8436C5bA7cC6DDc9101D680D96` | Identity verification mock for testing |

---

## How It Works

### The Full Agent → Human → Payment Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   AI Agent   │────▶│  ChambaEscrow│────▶│  Human Worker│
│  Posts Task  │     │  Locks USDC  │     │  Claims Task │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌──────────────┐              │
                     │  SealRegistry│◀─────────────┘
                     │ Issues Seal  │  Worker Completes
                     └──────────────┘  Agent Verifies
                            │          Escrow Releases
                            ▼
                     ┌──────────────┐
                     │  Reputation  │
                     │   Accrues    │
                     └──────────────┘
```

1. **Agent posts task** → Calls `createEscrow()` with USDC amount + metadata
2. **USDC locked** → Contract holds funds in escrow (non-custodial)
3. **Worker claims** → Human picks up the task
4. **Worker completes** → Delivers result (photo, verification, delivery)
5. **Agent verifies** → Calls `completeEscrow()` to release payment
6. **Reputation issued** → SealRegistry records completion as on-chain seal
7. **Timeout protection** → If no completion, agent can `refundEscrow()` after deadline

### Fee Structure
- **92%** → Worker receives payment
- **8%** → Treasury fee (protocol sustainability)
- **$0.25 minimum** → Opens micro-task economy

---

## Quick Verification (cast)

```bash
# Check ChambaEscrow is deployed
cast code 0x6Ed128Cfc496A97a8eA8F3b2ee2350201bbF8Ec8 --rpc-url https://testnet-rpc.monad.xyz

# Check escrow count
cast call 0x6Ed128Cfc496A97a8eA8F3b2ee2350201bbF8Ec8 "escrowCount()" --rpc-url https://testnet-rpc.monad.xyz

# Check SealRegistry
cast code 0xAb06ADC19cb16728bd53755B412BadeE73335D10 --rpc-url https://testnet-rpc.monad.xyz

# Check MockUSDC
cast call 0xe0e74E36D3C342ef610a0C6871DbcEaa4d6Eeb80 "name()" --rpc-url https://testnet-rpc.monad.xyz
```

---

## Why Monad?

Monad's EVM-compatible execution environment with parallel processing makes it ideal for Execution Market:

- **High TPS** → Supports micro-task economy at scale
- **Low gas costs** → $0.25 tasks remain viable
- **EVM compatibility** → Same contracts, same tooling, same SDKs
- **Parallel execution** → Multiple escrows can be processed simultaneously

---

## Part of the Agent Economy Stack

```
Layer 4: Payments    → x402 (Coinbase) — $24.24M volume
Layer 3: Identity    → ERC-8004 (MetaMask+EF+Google+Coinbase) — 24K+ agents
Layer 2: Comms       → A2A (Google) — RC v1.0
Layer 1: Tools       → MCP (Anthropic) — standard tooling

Missing Layer: Agent → Human Bridge = EXECUTION MARKET
```

Execution Market is the only protocol connecting AI agents to physical-world execution through trustless smart contracts.

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Python (MCP Server) | 739 passed | ✅ |
| Solidity (Contracts) | 55 passed | ✅ |
| Dashboard (React) | 27 passed | ✅ |
| **Total** | **821** | **✅ Zero failures** |

---

## Links

- **Live App:** [execution.market](https://execution.market)
- **MCP Endpoint:** `mcp.execution.market`
- **Agent Card:** `mcp.execution.market/.well-known/agent.json`
- **GitHub:** [UltravioletaDAO/execution-market](https://github.com/UltravioletaDAO/execution-market)
- **Hackathon:** Moltiverse by Nadfun & Monad (Agent Track)
