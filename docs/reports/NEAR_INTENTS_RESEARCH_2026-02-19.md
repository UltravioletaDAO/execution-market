# NEAR Intents Research Report

> Research Date: 2026-02-19
> Context: Karma Kadabra agent swarm (34-55 AI agents) cross-chain liquidity via USDC on 8 EVM chains
> Author: Claude Code (research task)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Are NEAR Intents](#2-what-are-near-intents)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Supported Chains](#4-supported-chains)
5. [Token Support & USDC Handling](#5-token-support--usdc-handling)
6. [SDKs & Libraries](#6-sdks--libraries)
7. [Programmatic Usage & Code Examples](#7-programmatic-usage--code-examples)
8. [Fees](#8-fees)
9. [Speed & Settlement](#9-speed--settlement)
10. [Defuse Protocol](#10-defuse-protocol)
11. [MCP Server for AI Agents](#11-mcp-server-for-ai-agents)
12. [Production Readiness](#12-production-readiness)
13. [Integration Complexity Assessment](#13-integration-complexity-assessment)
14. [Comparison with Alternatives](#14-comparison-with-alternatives)
15. [Feasibility Assessment for Karma Kadabra](#15-feasibility-assessment-for-karma-kadabra)
16. [Recommendations](#16-recommendations)
17. [Sources](#17-sources)

---

## 1. Executive Summary

NEAR Intents is an intent-based cross-chain protocol built on NEAR Protocol that enables multichain token swaps and transfers across 25+ blockchains. It has processed **$10B+ in volume** across **15.7M+ swaps** since launch, making it one of the most active cross-chain protocols in production.

**Key findings for our use case:**

| Criterion | Assessment |
|-----------|------------|
| Production ready | YES -- $10B volume, 15.7M swaps, 541K unique addresses in 30 days |
| Supports our 8 EVM chains | 7/8 confirmed (Base, Polygon, Arbitrum, Avalanche, Optimism, Ethereum, Monad). Celo status unclear |
| USDC support | YES -- native USDC on all major EVM chains |
| TypeScript SDK | YES -- `@defuse-protocol/one-click-sdk-typescript` |
| Python SDK | PARTIAL -- Python agent example exists, no official pip package |
| AI Agent integration | YES -- dedicated MCP server exists (`@iqai/mcp-near-intent-swaps`) |
| Settlement speed | 2-3 seconds (solver-mediated, not bridge-dependent) |
| Fees | 0.0001% protocol fee + solver spread (with API key). 0.2% without API key |
| Programmatic API | YES -- REST API at `https://1click.chaindefuser.com/` |

**Bottom line**: NEAR Intents is a strong candidate for Karma Kadabra cross-chain liquidity. The intent-based model is a natural fit for AI agents expressing high-level goals. The existing MCP server and Python agent examples reduce integration effort significantly.

---

## 2. What Are NEAR Intents

NEAR Intents is a **multichain transaction protocol** where users (or AI agents) specify **what they want** rather than **how to do it**. Third-party solvers (called Market Makers) compete to fulfill these requests optimally.

### Core Concept

```
Traditional approach:
  Agent → Bridge A → Wait → Swap on DEX → Bridge B → Wait → Destination

Intent approach:
  Agent: "I want 100 USDC on Polygon, I have 100 USDC on Base"
  Solver: "I'll do it for 99.99 USDC delivered in 3 seconds"
  Agent: "Accepted" → Signs intent → Receives funds
```

The user/agent never interacts with bridges, DEXes, or gas on foreign chains. The solver handles all routing complexity and delivers the result.

### Three Pillars

1. **Distribution Channels** -- Applications that create and broadcast intents (wallets, dApps, our agent swarm)
2. **Market Makers (Solvers)** -- Liquidity providers competing to fulfill intents at best price
3. **Verifier Smart Contract** -- On-chain NEAR contract that atomically settles all transactions

---

## 3. Architecture Deep Dive

### Intent Lifecycle

```
                                    [Solver Bus]
                                   /     |      \
[Agent] → Intent → [1Click API] → [Solver A] [Solver B] [Solver C]
                                        ↓
                                   Best quote selected
                                        ↓
                              [Verifier Contract on NEAR]
                                        ↓
                              Atomic settlement on NEAR
                                        ↓
                              [Destination chain delivery]
                                   via OmniBridge /
                                   Chain Signatures
```

### Component Details

#### Solver Bus (RFQ System)
- **JSON-RPC**: `https://solver-relay-v2.chaindefuser.com/rpc`
- **WebSocket**: `wss://solver-relay-v2.chaindefuser.com/ws`
- Quote requests broadcast to ALL connected solvers
- **3-second timeout** -- solvers must respond within 3000ms
- All quotes returned to requester for selection
- Solvers compete on: price quality, speed, deadline flexibility

#### Verifier Smart Contract (`intents.near`)
- Deployed on NEAR mainnet
- Executes intents **atomically** -- both sides of a swap happen or neither does
- Three intent types: `Transfer`, `TokenDiff` (swaps), `FtWithdraw` (withdrawals)
- Users deposit tokens into Verifier; it maintains custody during settlement
- Verification of ownership before releasing funds to destination

#### Chain Signatures & OmniBridge
- NEAR's multichain signing system using MPC (Multi-Party Computation)
- Eliminates traditional bridge challenge periods
- Single MPC signature verification (ECDSA for EVM chains)
- Security derives from MPC threshold guarantees, not optimistic assumptions
- Enables permissionless, trustless settlement to any supported chain

#### 1Click API (Abstraction Layer)
- REST API that abstracts the full intent lifecycle
- Base URL: `https://1click.chaindefuser.com/`
- Temporarily transfers assets to a trusted swapping agent
- Coordinates with Market Makers to execute the intent
- Handles deposit address generation, status tracking, refunds

### Settlement Flow (Detailed)

```
1. Agent calls POST /v0/quote with intent parameters
   → Receives: quote with pricing, deposit address, estimated time

2. Agent deposits tokens to the provided deposit address
   (standard EVM transfer, agent pays source chain gas only)

3. Agent calls POST /v0/deposit/submit with tx hash (optional, speeds up)

4. 1Click detects deposit → routes to Solver Bus → solvers compete
   → Best execution path selected

5. Solver deposits equivalent tokens on destination chain
   (solver uses own capital for instant delivery)

6. Verifier contract on NEAR settles atomically
   (solver gets source tokens, user gets destination tokens)

7. Agent receives tokens at destination address
   Status: PROCESSING → SUCCESS (typically 2-3 seconds after deposit confirms)
```

---

## 4. Supported Chains

### Full Chain List (25+ chains)

| Chain | Code | EVM | Our Chain? | Status |
|-------|------|-----|------------|--------|
| Ethereum | `eth` | Yes | Yes | Supported |
| Base | `base` | Yes | Yes | Supported |
| Polygon | `pol` | Yes | Yes | Supported |
| Arbitrum | `arb` | Yes | Yes | Supported |
| Avalanche | `avax` | Yes | Yes | Supported |
| Optimism | `op` | Yes | Yes | Supported |
| Monad | `monad` | Yes | Yes | Supported |
| **Celo** | -- | Yes | Yes | **NOT CONFIRMED** |
| BNB Smart Chain | `bsc` | Yes | No | Supported |
| Gnosis | `gnosis` | Yes | No | Supported |
| Aurora | `aurora` | Yes | No | Supported |
| Berachain | `bera` | Yes | No | Supported |
| XLayer | `xlayer` | Yes | No | Supported |
| ADI | `adi` | Yes | No | Supported |
| Plasma | `plasma` | Yes | No | Supported |
| Starknet | `starknet` | No | No | Supported |
| NEAR | `near` | No | No | Supported |
| Solana | `sol` | No | No | Supported |
| Bitcoin | `btc` | No | No | Supported |
| TON | `ton` | No | No | Supported |
| Sui | `sui` | No | No | Supported |
| Tron | `tron` | No | No | Supported |
| XRP | `xrp` | No | No | Supported |
| Dogecoin | `doge` | No | No | Supported |
| Litecoin | `ltc` | No | No | Supported |
| Bitcoin Cash | `bch` | No | No | Supported |
| Stellar | `xlm` | No | No | Supported |
| Aleo | `aleo` | No | No | Supported |
| Cardano | `cardano` | No | No | Partial |
| ZCash | `zec` | No | No | Partial |

### Coverage for Our 8 Chains

| Our Chain | NEAR Intents Support |
|-----------|---------------------|
| Base | YES |
| Polygon | YES |
| Arbitrum | YES |
| Avalanche | YES |
| Optimism | YES |
| Ethereum | YES |
| Monad | YES |
| **Celo** | **UNCONFIRMED** -- not in official chain list. Must verify via `/v0/tokens` API |

**7/8 confirmed**, Celo needs verification. This is notably better than CCTP which only supports ~8 chains total.

---

## 5. Token Support & USDC Handling

### USDC Token Identifiers

NEAR Intents uses the NEP-141 token standard with the format:
```
nep141:{chain_prefix}-{contract_address}.omft.near
```

Known USDC identifiers (can be queried via `GET /v0/tokens`):

| Chain | USDC Contract | NEAR Intents Asset ID (estimated) |
|-------|---------------|-----------------------------------|
| Arbitrum | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | `nep141:arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near` |
| Base | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | `nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near` |
| Polygon | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | `nep141:pol-0x3c499c542cef5e3811e1192ce70d8cc03d5c3359.omft.near` |
| Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `nep141:eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near` |
| Avalanche | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | `nep141:avax-0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e.omft.near` |
| Optimism | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | `nep141:op-0x0b2c639c533813f4aa9d7837caf62653d097ff85.omft.near` |

**Note**: Exact asset IDs should be confirmed via the `/v0/tokens` endpoint. The format pattern is consistent but contract address casing may vary.

### How Cross-Chain USDC Works

1. Agent has USDC on Chain A (e.g., Base)
2. Agent requests quote: "I have 100 USDC on Base, I want USDC on Polygon"
3. Solver quotes: "I'll deliver 99.99 USDC on Polygon" (spread = 0.01 USDC)
4. Agent deposits 100 USDC to the deposit address on Base
5. Solver delivers 99.99 USDC to agent's address on Polygon (from solver's own liquidity)
6. Settlement: Verifier contract transfers agent's Base USDC to solver on NEAR
7. Agent has USDC on Polygon. Done.

The key insight: **solvers front their own capital** on the destination chain, enabling instant delivery. Settlement with the solver happens asynchronously via NEAR.

---

## 6. SDKs & Libraries

### TypeScript (Primary SDK)

#### 1Click SDK (Recommended for programmatic use)

```bash
npm install @defuse-protocol/one-click-sdk-typescript
# or
pnpm add @defuse-protocol/one-click-sdk-typescript
```

Full REST API wrapper with TypeScript types. Covers quotes, deposits, status tracking.

#### Defuse SDK (React components)

```bash
yarn add @defuse-protocol/defuse-sdk
```

**WARNING**: Documentation states "SDK is under heavy development and the API is highly unstable." Recommended for UI integration only.

#### Intents SDK (Low-level)

```bash
npm install @defuse-protocol/intents-sdk
```

Low-level intent signing and cross-chain operations. Part of the monorepo.

#### Bridge SDK

```bash
npm install @defuse-protocol/bridge-sdk
```

Withdrawal operations and multi-bridge support (Hot Bridge, PoA Bridge, Omni Bridge).

### Python (Community / Example)

**No official pip package exists.** However:

- **Agent example**: `github.com/near-examples/near-intents-agent-example` -- Python implementation of an AI agent using NEAR Intents
- Dependencies: `near-api-py`, `requests`, standard Python libs
- Can be adapted into a reusable library

```bash
git clone https://github.com/near-examples/near-intents-agent-example
cd near-intents-agent-example
pip install -r requirements.txt
```

### Alternative: Raw HTTP API

Since the 1Click API is a simple REST API, any language with HTTP support works:

```
Base URL: https://1click.chaindefuser.com/
Auth: Bearer JWT token (optional but reduces fees)
Format: JSON
Endpoints: /v0/tokens, /v0/quote, /v0/deposit/submit, /v0/status
OpenAPI Spec: https://1click.chaindefuser.com/docs/v0/openapi.yaml
```

### MCP Server (AI Agent Integration)

```bash
npx @iqai/mcp-near-intent-swaps
```

Model Context Protocol server providing 5 tools for AI agents. See section 11.

---

## 7. Programmatic Usage & Code Examples

### Example 1: Cross-Chain USDC Transfer (TypeScript)

```typescript
import { OpenAPI, QuoteRequest, OneClickService } from '@defuse-protocol/one-click-sdk-typescript';

// Configure
OpenAPI.BASE = 'https://1click.chaindefuser.com';
OpenAPI.TOKEN = 'your-jwt-token';  // Get from Partners Portal

// Step 1: Get a quote for Base USDC → Polygon USDC
const quoteRequest: QuoteRequest = {
    dry: false,  // false = real swap, true = price check only
    swapType: QuoteRequest.swapType.EXACT_INPUT,
    slippageTolerance: 100,  // 1% in basis points
    originAsset: 'nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near',
    depositType: QuoteRequest.depositType.ORIGIN_CHAIN,
    destinationAsset: 'nep141:pol-0x3c499c542cef5e3811e1192ce70d8cc03d5c3359.omft.near',
    amount: '100000000',  // 100 USDC (6 decimals)
    refundTo: '0xAgentWalletOnBase',
    refundType: QuoteRequest.refundType.ORIGIN_CHAIN,
    recipient: '0xAgentWalletOnPolygon',
    recipientType: QuoteRequest.recipientType.DESTINATION_CHAIN,
    deadline: new Date(Date.now() + 15 * 60 * 1000).toISOString()  // 15 min
};

const quote = await OneClickService.getQuote(quoteRequest);
console.log('Deposit address:', quote.depositAddress);
console.log('Amount out:', quote.amountOut);
console.log('Estimated time:', quote.estimatedTime);

// Step 2: Send USDC to the deposit address (standard EVM transfer)
// Use viem/ethers to send USDC to quote.depositAddress on Base
const txHash = await sendUSDCTransfer(
    quote.depositAddress,
    '100000000',  // 100 USDC
    'base'
);

// Step 3: Notify 1Click (optional but speeds up processing)
await OneClickService.submitDepositTx({
    txHash: txHash,
    depositAddress: quote.depositAddress
});

// Step 4: Monitor status
let status;
do {
    status = await OneClickService.getExecutionStatus(quote.depositAddress);
    console.log('Status:', status.status);
    await new Promise(r => setTimeout(r, 2000));  // Poll every 2s
} while (status.status !== 'SUCCESS' && status.status !== 'FAILED');
```

### Example 2: Dry-Run Quote Check (TypeScript)

```typescript
// Check price without executing -- useful for agent decision-making
const dryQuote: QuoteRequest = {
    dry: true,
    swapType: QuoteRequest.swapType.EXACT_INPUT,
    slippageTolerance: 100,
    originAsset: 'nep141:arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near',
    depositType: QuoteRequest.depositType.ORIGIN_CHAIN,
    destinationAsset: 'nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near',
    amount: '50000000',  // 50 USDC
    refundTo: '0xAgentWallet',
    refundType: QuoteRequest.refundType.ORIGIN_CHAIN,
    recipient: '0xAgentWallet',
    recipientType: QuoteRequest.recipientType.DESTINATION_CHAIN,
    deadline: new Date(Date.now() + 15 * 60 * 1000).toISOString()
};

const preview = await OneClickService.getQuote(dryQuote);
console.log(`${preview.amountIn} USDC on Arbitrum → ${preview.amountOut} USDC on Base`);
console.log(`Effective rate: ${Number(preview.amountOut) / Number(preview.amountIn)}`);
```

### Example 3: Python Agent (from near-intents-agent-example)

```python
from ai_agent import AIAgent

# Initialize agent with NEAR account credentials
agent = AIAgent("./account_file.json")

# Deposit tokens to intents contract
agent.deposit_near(1.0)

# Execute a swap
result = agent.swap_near_to_token("USDC", 1.0)
print(f"Swap completed: {result}")
```

### Example 4: Raw HTTP API (Python, no SDK needed)

```python
"""
Cross-chain USDC transfer using NEAR Intents 1Click API.
No SDK required -- plain HTTP requests.
"""
import requests
import time

API_BASE = "https://1click.chaindefuser.com"
JWT_TOKEN = "your-jwt-token"  # Optional, reduces fee from 0.2% to 0.0001%

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {JWT_TOKEN}" if JWT_TOKEN else None
}

# Step 1: Get quote
quote_payload = {
    "dry": False,
    "swapType": "EXACT_INPUT",
    "slippageTolerance": 100,
    "originAsset": "nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near",
    "depositType": "ORIGIN_CHAIN",
    "destinationAsset": "nep141:pol-0x3c499c542cef5e3811e1192ce70d8cc03d5c3359.omft.near",
    "amount": "10000000",  # 10 USDC
    "refundTo": "0xAgentAddressOnBase",
    "refundType": "ORIGIN_CHAIN",
    "recipient": "0xAgentAddressOnPolygon",
    "recipientType": "DESTINATION_CHAIN",
    "deadline": "2026-02-19T15:00:00Z"
}

resp = requests.post(f"{API_BASE}/v0/quote", json=quote_payload, headers=headers)
quote = resp.json()
deposit_address = quote["depositAddress"]
print(f"Deposit {quote['amountIn']} to {deposit_address} on Base")

# Step 2: Agent sends USDC to deposit_address on Base (via your existing EVM code)
# tx_hash = send_usdc_on_base(deposit_address, amount)

# Step 3: Notify 1Click (speeds up processing)
requests.post(f"{API_BASE}/v0/deposit/submit", json={
    "txHash": tx_hash,
    "depositAddress": deposit_address
}, headers=headers)

# Step 4: Poll status
while True:
    resp = requests.get(f"{API_BASE}/v0/status", params={
        "depositAddress": deposit_address
    }, headers=headers)
    status = resp.json()
    print(f"Status: {status['status']}")

    if status["status"] in ("SUCCESS", "FAILED", "REFUNDED"):
        break
    time.sleep(2)

print(f"Final: {status}")
```

### Example 5: Batch Operations (Multiple Intents)

```typescript
// Execute multiple cross-chain transfers in parallel
async function batchCrossChainTransfer(transfers: Transfer[]) {
    // Step 1: Get all quotes in parallel
    const quotePromises = transfers.map(t =>
        OneClickService.getQuote({
            dry: false,
            swapType: QuoteRequest.swapType.EXACT_INPUT,
            slippageTolerance: 100,
            originAsset: t.fromAsset,
            depositType: QuoteRequest.depositType.ORIGIN_CHAIN,
            destinationAsset: t.toAsset,
            amount: t.amount,
            refundTo: t.refundAddress,
            refundType: QuoteRequest.refundType.ORIGIN_CHAIN,
            recipient: t.recipientAddress,
            recipientType: QuoteRequest.recipientType.DESTINATION_CHAIN,
            deadline: new Date(Date.now() + 15 * 60 * 1000).toISOString()
        })
    );

    const quotes = await Promise.all(quotePromises);

    // Step 2: Execute deposits on respective source chains
    const depositPromises = quotes.map((quote, i) =>
        sendUSDCTransfer(quote.depositAddress, transfers[i].amount, transfers[i].sourceChain)
    );

    const txHashes = await Promise.all(depositPromises);

    // Step 3: Submit all deposit notifications
    await Promise.all(quotes.map((quote, i) =>
        OneClickService.submitDepositTx({
            txHash: txHashes[i],
            depositAddress: quote.depositAddress
        })
    ));

    // Step 4: Monitor all statuses
    return monitorAllStatuses(quotes.map(q => q.depositAddress));
}
```

### Example 6: Monitoring Intent Resolution

```typescript
// Status states and their meanings
type SwapStatus =
    | 'PENDING_DEPOSIT'     // Waiting for agent to deposit tokens
    | 'KNOWN_DEPOSIT_TX'    // Deposit detected, not yet confirmed
    | 'PROCESSING'          // Solvers executing the swap
    | 'SUCCESS'             // Funds delivered to recipient
    | 'INCOMPLETE_DEPOSIT'  // Deposit amount too low
    | 'REFUNDED'            // Swap failed, tokens returned to refundTo address
    | 'FAILED';             // Unrecoverable error

async function monitorIntent(depositAddress: string, timeoutMs = 120000) {
    const start = Date.now();

    while (Date.now() - start < timeoutMs) {
        const status = await OneClickService.getExecutionStatus(depositAddress);

        switch (status.status) {
            case 'SUCCESS':
                return { success: true, txHash: status.txHash };
            case 'FAILED':
            case 'REFUNDED':
                return { success: false, reason: status.status };
            case 'PROCESSING':
                // Typically resolves in 2-3 seconds
                await sleep(1000);
                break;
            default:
                await sleep(3000);
        }
    }

    return { success: false, reason: 'TIMEOUT' };
}
```

---

## 8. Fees

### Fee Structure

| Fee Layer | Amount | Who Pays | Condition |
|-----------|--------|----------|-----------|
| Protocol fee | 0.0001% (1 pip) | User/Agent | Always -- collected by `intents.near` |
| 1Click platform fee | 0.2% | User/Agent | Only without API key |
| Solver spread | Market-driven | User/Agent | Built into quote price |
| Source chain gas | Varies | User/Agent | One EVM transfer to deposit address |
| Destination chain gas | $0 | Solver | Solver pays destination gas |
| Withdrawal fee (SOL only) | 0.1% | User/Agent | NEAR/ZEC/STRK to Solana |

### Fee Scenarios for 100 USDC Transfer

| Scenario | Protocol Fee | Platform Fee | Solver Spread | Total Cost |
|----------|-------------|-------------|---------------|------------|
| With API key | $0.0001 | $0 | ~$0.01-0.05 | ~$0.01-0.05 |
| Without API key | $0.0001 | $0.20 | ~$0.01-0.05 | ~$0.21-0.25 |

### API Key Registration

Register at the [Partners Portal](https://docs.google.com/forms/d/e/1FAIpQLSdrSrqSkKOMb_a8XhwF0f7N5xZ0Y5CYgyzxiAuoC2g4a2N68g/viewform) to receive a JWT token. This eliminates the 0.2% fee, leaving only the 0.0001% protocol fee + solver spread.

### Custom App Fees

Distribution channels can add their own fees via the `appFees` parameter in the quote request. This could be used by Karma Kadabra to add a coordination fee if desired.

### Cost Comparison (100 USDC cross-chain)

| Protocol | Estimated Cost |
|----------|---------------|
| NEAR Intents (with key) | ~$0.01-0.05 |
| CCTP v2 | ~$0.50-2.00 (gas on source + destination) |
| Wormhole | ~$0.30-1.50 (relayer fees) |
| LayerZero | ~$0.20-1.00 (message fees) |
| Our x402 Facilitator | $0 (gasless, but same-chain only) |

**NEAR Intents is significantly cheaper** for cross-chain transfers, especially with an API key.

---

## 9. Speed & Settlement

### Settlement Times

| Phase | Duration |
|-------|----------|
| Quote generation | < 3 seconds (solver bus timeout) |
| Deposit confirmation | Chain-dependent (Base ~2s, Ethereum ~12s, Bitcoin ~60min) |
| Solver execution | **2-3 seconds** after deposit confirms |
| Total (EVM to EVM) | **5-15 seconds** typical |
| Total (with slow source) | Minutes to hours (Bitcoin, etc.) |

### Why It Is Fast

1. **Solvers front capital**: The solver delivers tokens on the destination chain using their own liquidity BEFORE the source chain deposit is fully settled on NEAR
2. **No bridge wait**: Unlike traditional bridges with finality periods (7-day optimistic rollup, 15-min challenge), solvers take the finality risk
3. **NEAR finality**: NEAR chain itself finalizes in ~2 seconds
4. **Chain Signatures**: Single MPC signature verification replaces multi-validator consensus

### Speed Comparison

| Protocol | EVM-to-EVM Speed |
|----------|-----------------|
| NEAR Intents | 5-15 seconds |
| CCTP v2 | 10-60 seconds |
| Wormhole | 15-120 seconds |
| Optimistic bridges | 7 days |
| LayerZero | 30-300 seconds |

---

## 10. Defuse Protocol

**Yes, Defuse is the original name of NEAR Intents.** The protocol was renamed from "Defuse" to "NEAR Intents" in late 2025.

### Key Details

| Aspect | Detail |
|--------|--------|
| Original name | Defuse Protocol |
| Current name | NEAR Intents |
| Rename date | Late 2025 |
| npm scope | Still `@defuse-protocol/*` |
| API domain | `chaindefuser.com` (still uses Defuse branding) |
| Contract | `intents.near` on NEAR mainnet |
| Governance | `fefundsadmin.sputnik-dao.near` (platform fees) |
| Explorer | `explorer.near-intents.org` |

### npm Packages (still under @defuse-protocol)

- `@defuse-protocol/one-click-sdk-typescript` -- 1Click API wrapper
- `@defuse-protocol/defuse-sdk` -- React UI components
- `@defuse-protocol/intents-sdk` -- Low-level intent operations
- `@defuse-protocol/bridge-sdk` -- Bridge/withdrawal operations

### GitHub Organization

- `github.com/defuse-protocol` -- SDK repos, solver examples
- `github.com/near/intents` -- Core smart contracts
- `github.com/near-examples/near-intents-examples` -- Educational examples

---

## 11. MCP Server for AI Agents

There is a **dedicated MCP server** for AI agents to interact with NEAR Intents, built by IQ.AI.

### Installation

```bash
npx @iqai/mcp-near-intent-swaps
```

### Claude Code Configuration

```json
{
    "mcpServers": {
        "near-intent-swaps": {
            "command": "npx",
            "args": ["-y", "@iqai/mcp-near-intent-swaps"],
            "env": {
                "NEAR_SWAP_JWT_TOKEN": "your-jwt-token"
            }
        }
    }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `GET_NEAR_SWAP_TOKENS` | Discover available tokens across all supported chains |
| `GET_NEAR_SWAP_SIMPLE_QUOTE` | Dry-run quote for price checking (no deposit address) |
| `GET_NEAR_SWAP_FULL_QUOTE` | Full quote with deposit address for real swaps |
| `EXECUTE_NEAR_SWAP` | Submit deposit tx hash to trigger swap processing |
| `CHECK_NEAR_SWAP_STATUS` | Monitor swap status (PENDING/PROCESSING/SUCCESS/FAILED) |

### Natural Language Usage

AI agents can interact via natural language:
- "What's the rate for 100 USDC from Arbitrum to Base?"
- "Execute a 50 USDC swap from Base to Polygon, recipient 0x..."
- "Check my swap status for deposit address 0x..."

### Relevance to Karma Kadabra

This MCP server means our agents could use NEAR Intents natively through the MCP protocol -- the same protocol they already use to interact with Execution Market. An agent could:

1. Check their USDC balance on current chain
2. Use the NEAR Intents MCP tool to get a quote for cross-chain transfer
3. Execute the transfer
4. Continue with their task on the destination chain

No new protocol integration needed -- it is MCP all the way down.

---

## 12. Production Readiness

### Current Status: PRODUCTION READY

| Metric | Value |
|--------|-------|
| Total volume | $10B+ |
| Total swaps | 15.7M+ |
| Fee revenue | $17M+ |
| 30-day volume | $2.15B |
| 30-day unique addresses | 541,075 |
| Supported chains | 25+ |
| Active solvers | Multiple (competitive market) |
| Teams building | 50+ |
| Mainnet since | 2025 |
| No testnet | Correct -- mainnet only, use small amounts for testing |

### Risks & Considerations

| Risk | Severity | Mitigation |
|------|----------|------------|
| No testnet | Medium | Use small amounts ($0.10-$1.00) for testing on mainnet |
| Solver liquidity gaps | Low | $10B volume suggests deep liquidity |
| API key dependency | Low | Works without key (just higher fees) |
| Celo support unclear | Medium | Verify via `/v0/tokens` API |
| Python SDK maturity | Medium | Use HTTP API directly or TypeScript SDK |
| Defuse rename confusion | Low | npm packages still under `@defuse-protocol` |
| Smart contract risk | Low | Audited, $10B TVF (Total Value Flowing) |

---

## 13. Integration Complexity Assessment

### Integration Effort Comparison

| Approach | Complexity | Time Estimate | Best For |
|----------|-----------|--------------|----------|
| MCP Server (`@iqai/mcp-near-intent-swaps`) | **Very Low** | 1-2 hours | Single agent, Claude-based |
| 1Click TypeScript SDK | **Low** | 1-2 days | TypeScript agents, batch ops |
| Raw HTTP API (Python) | **Low** | 2-3 days | Python agents, custom logic |
| Direct Solver Bus (WebSocket) | **High** | 1-2 weeks | Custom solver, advanced |
| Full Defuse SDK (React) | **Medium** | 3-5 days | Dashboard integration |

### What Integration Requires

1. **Get API key** (JWT) from Partners Portal -- reduces fees from 0.2% to 0.0001%
2. **Identify USDC asset IDs** for our 8 chains via `/v0/tokens`
3. **Build a wrapper** around the 1Click API (or use MCP server)
4. **Handle the deposit step** -- standard EVM USDC transfer to the deposit address
5. **Monitor status** -- poll `/v0/status` until SUCCESS/FAILED
6. **Handle refunds** -- if swap fails, tokens auto-refund to `refundTo` address

### What Is NOT Needed

- No NEAR account required (for 1Click API -- the API handles NEAR-side operations)
- No NEAR tokens needed
- No new smart contract deployments
- No bridge-specific code
- No solver integration (1Click handles solver routing)
- No destination chain gas (solver pays)

---

## 14. Comparison with Alternatives

### Feature Matrix

| Feature | NEAR Intents | CCTP v2 | Wormhole | LayerZero | Across |
|---------|-------------|---------|----------|-----------|--------|
| Cross-chain USDC | Native swap | Native burn/mint | Wrapped + CCTP | Wrapped | Intent-based |
| Speed (EVM-EVM) | 5-15s | 10-60s | 15-120s | 30-300s | 2-10s |
| Fee (100 USDC) | ~$0.05 | ~$1.00 | ~$0.50 | ~$0.50 | ~$0.10 |
| Chains supported | 25+ | ~8 | ~30 | ~35 | ~8 |
| AI agent tooling | MCP server | None | None | None | None |
| Python SDK | Example code | No | Yes | No | No |
| TypeScript SDK | Yes | Yes | Yes | Yes | Yes |
| Programmatic API | REST + WS | On-chain | On-chain | On-chain | REST |
| Gas on destination | None (solver) | User pays | Relayer | User pays | None (solver) |
| Testnet | No | Yes | Yes | Yes | Yes |
| Our chain coverage | 7/8 | 5/8 | 6/8 | 6/8 | 4/8 |

### Why NEAR Intents Stands Out for AI Agents

1. **MCP Server exists** -- no other cross-chain protocol has this
2. **REST API** -- simpler than on-chain contract calls for agents
3. **No destination gas** -- agents do not need gas tokens on every chain
4. **Intent-based** -- natural fit for AI expressing "what" not "how"
5. **Competitive solvers** -- better pricing than fixed-fee bridges
6. **25+ chains** -- covers almost everything we need including Monad

---

## 15. Feasibility Assessment for Karma Kadabra

### Use Case Fit: EXCELLENT

Our scenario: 34-55 AI agents transacting across 8 EVM chains, paying each other in USDC via x402 protocol.

#### How It Would Work

```
Agent A (on Base, needs to pay Agent B on Polygon):

1. Agent A has 10 USDC on Base
2. Agent A calls NEAR Intents 1Click API:
   "Transfer 10 USDC from Base to Polygon, recipient = Agent B's address"
3. Agent A sends USDC to deposit address on Base (one EVM tx)
4. NEAR Intents delivers ~9.995 USDC to Agent B on Polygon (solver handles everything)
5. Agent B receives USDC on Polygon in ~5-15 seconds
6. Agent B can now spend that USDC via x402 on Polygon
```

#### Integration Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Karma Kadabra Swarm                     │
│                                                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐   ┌─────────┐   │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │...│ Agent N  │   │
│  │ (Base)   │  │ (Polygon)│  │ (Arb)   │   │ (Avax)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘   └────┬─────┘   │
│       │              │              │              │         │
│       └──────────────┴──────────────┴──────────────┘         │
│                           │                                   │
│              ┌────────────┴────────────┐                     │
│              │  Cross-Chain Liquidity   │                     │
│              │       Router            │                     │
│              └────────────┬────────────┘                     │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │  NEAR Intents 1Click  │
                │  REST API             │
                │  (or MCP Server)      │
                └───────────┬───────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────┴─────┐ ┌────┴────┐ ┌─────┴─────┐
        │ Solver A   │ │Solver B │ │ Solver C  │
        │ (provides  │ │         │ │           │
        │  liquidity)│ │         │ │           │
        └────────────┘ └─────────┘ └───────────┘
```

#### Advantages for Our Use Case

1. **Single deposit tx per transfer** -- agent only needs gas on source chain
2. **No gas management on 8 chains** -- solvers pay destination gas
3. **USDC-native** -- no wrapped tokens, no liquidity fragmentation
4. **Sub-15-second settlement** -- fast enough for agent-to-agent commerce
5. **Batch-friendly** -- multiple transfers can run in parallel via Promise.all
6. **MCP integration** -- agents already speak MCP
7. **Low cost** -- ~$0.05 per $100 transfer with API key
8. **Automatic refunds** -- if a swap fails, funds return automatically

#### Challenges

1. **Celo support uncertain** -- 1/8 of our chains may not be supported
2. **No testnet** -- must test with real (small) amounts on mainnet
3. **Python SDK gap** -- need to build a thin wrapper around HTTP API
4. **Deposit step complexity** -- agent needs to sign an EVM tx to deposit USDC
5. **JWT token management** -- need to distribute API key to all agents
6. **Amount limits** -- solver liquidity determines max single transfer size

#### Risk Mitigation

| Challenge | Mitigation |
|-----------|------------|
| Celo support | Query `/v0/tokens` to verify. If absent, use CCTP for Celo only |
| No testnet | Use $0.10 test amounts. NEAR Intents refunds failed swaps |
| Python SDK | Build thin HTTP wrapper (see Example 4 above). ~100 LOC |
| Deposit complexity | Already have EVM signing in our codebase (viem/ethers) |
| JWT distribution | Single JWT for all agents (server-side key, not per-agent) |
| Amount limits | Split large transfers into multiple intents |

---

## 16. Recommendations

### Recommended Integration Path

**Phase 1: Validate (1-2 days)**
1. Register on Partners Portal for JWT API key
2. Query `/v0/tokens` to confirm USDC support on all 8 chains
3. Execute a $0.10 test transfer: Base USDC to Polygon USDC
4. Measure actual speed and fees

**Phase 2: Build Python Wrapper (2-3 days)**
1. Create `near_intents_client.py` -- thin wrapper around 1Click HTTP API
2. Methods: `get_quote()`, `execute_transfer()`, `check_status()`, `get_tokens()`
3. Handle retry logic, timeout, refund detection
4. Add to `mcp_server/integrations/` alongside existing x402 client

**Phase 3: Agent Integration (3-5 days)**
1. Add cross-chain transfer capability to agent swarm coordinator
2. Decision logic: "Do I need to transfer USDC to another chain for this task?"
3. Integrate with existing x402 payment flow (transfer first, then pay via x402)
4. Add MCP tools: `em_cross_chain_transfer`, `em_check_transfer_status`

**Phase 4: Production Deployment (1-2 days)**
1. Configure JWT in AWS Secrets Manager
2. Add to ECS task definitions
3. Monitor via `/v0/status` + payment_events table
4. Set up alerting for failed transfers

### Architecture Decision

**Use the 1Click REST API directly** (not the MCP server). Reasons:
- More control over error handling and retry logic
- Can batch operations efficiently
- Integrates cleanly with our existing Python backend
- MCP server is better for individual Claude instances, not a swarm coordinator

### Alternative: Hybrid Approach

For the edge case where NEAR Intents does not support a chain (possibly Celo):
- Use NEAR Intents for 7 chains (fast, cheap)
- Use CCTP v2 for Celo (if needed, slower but reliable)
- Router logic: check chain support, pick best protocol

---

## 17. Sources

- [NEAR Intents Overview (docs.near-intents.org)](https://docs.near-intents.org/near-intents)
- [NEAR Intents SDK Documentation](https://docs.near-intents.org/near-intents/sdk)
- [NEAR Intents Chain Support](https://docs.near-intents.org/near-intents/chain-address-support)
- [NEAR Intents Fees](https://docs.near-intents.org/near-intents/fees)
- [1Click API Documentation](https://docs.near-intents.org/near-intents/integration/distribution-channels/1click-api)
- [1Click TypeScript SDK (GitHub)](https://github.com/defuse-protocol/one-click-sdk-typescript)
- [NEAR Intents Examples (GitHub)](https://github.com/near-examples/near-intents-examples)
- [NEAR Intents AI Agent Example (GitHub)](https://github.com/near-examples/near-intents-agent-example)
- [MCP NEAR Intents Server (GitHub)](https://github.com/IQAIcom/mcp-near-intents)
- [NEAR Documentation - Intents Overview](https://docs.near.org/chain-abstraction/intents/overview)
- [NEAR Documentation - OmniBridge](https://docs.near.org/chain-abstraction/omnibridge/overview)
- [NEAR Documentation - Chain Signatures](https://docs.near.org/chain-abstraction/chain-signatures)
- [NEAR Intents on npm (@defuse-protocol)](https://www.npmjs.com/package/@defuse-protocol/intents-sdk)
- [NEAR Intents $10B Volume (Bitget News)](https://www.bitget.com/news/detail/12560605156555)
- [NEAR Intents $10B Volume (Yahoo Finance)](https://finance.yahoo.com/news/near-intents-achieves-10b-swap-183636390.html)
- [NEAR Intents on DefiLlama](https://defillama.com/protocol/near-intents)
- [Solver Bus API Documentation](https://docs.near-intents.org/near-intents/market-makers/bus/solver-relay)
- [Verifier Contract Documentation](https://docs.near-intents.org/near-intents/market-makers/verifier/introduction)
- [OmniBridge Blog Post](https://www.near.org/blog/omnibridge-nears-universal-solution-for-cross-chain-liquidity)
- [NEAR Intents + Starknet Integration](https://www.starknet.io/blog/bridging-the-gap-near-intents-brings-seamless-cross-chain-interoperability-to-starknet/)
- [NEAR Intents on SwapKit](https://swapkit.dev/near-intents/)
- [OpenAPI Spec](https://1click.chaindefuser.com/docs/v0/openapi.yaml)
- [MCP NEAR Intents on ADK](https://adk.iqai.com/docs/mcp-servers/iq-ai-servers/near-intents)
