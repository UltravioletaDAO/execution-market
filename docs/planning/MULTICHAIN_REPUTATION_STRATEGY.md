# Multi-Chain Reputation Strategy for ERC-8004

> Architecture decision document for extending reputation beyond Base to all 8 mainnets.
> Created: 2026-02-14 | Status: PLANNED (Base-only active)

## Current State (Base Only)

| Item | Value |
|------|-------|
| Agent ID | 2106 (Base) |
| EM_AGENT_ID env var | `2106` |
| ERC8004_NETWORK | `"base"` |
| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (CREATE2, all mainnets) |
| Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` (CREATE2, all mainnets) |
| Feedback path (agent→worker) | Direct on-chain via platform wallet (`direct_reputation.py`) |
| Feedback path (worker→agent) | Via Facilitator (fallback) or relay wallet (temporary) |
| feedbackURI domain | `execution.market` (proxied to CloudFront) |

## Critical ERC-8004 Facts

### Agent IDs are PER-CHAIN

Each chain has an independent `_lastId` counter. Agent #2106 on Base would be a **different number** on Ethereum, Polygon, etc. The global unique identifier is:

```
eip155:{chainId}:{registryAddress}:agent#{agentId}
Example: eip155:8453:0x8004A169...:#2106  (Base)
         eip155:1:0x8004A169...:#847      (Ethereum — hypothetical)
```

### No Cross-Chain Reputation in Protocol

Each `ReputationRegistry` is 100% independent. No bridge, no aggregator, no cross-chain reference. Reputation on Base is invisible from Polygon.

### Cross-Chain Identity Linking (Off-Chain Only)

The agent card JSON (`agent-card.json`) has a `registrations[]` array:
```json
{
  "registrations": [
    { "network": "base", "agentId": 2106, "registry": "0x8004A169..." },
    { "network": "ethereum", "agentId": 847, "registry": "0x8004A169..." }
  ]
}
```
And `agentWallet` serves as the correlator — same wallet = same agent across chains.

### Contracts are UUPS Upgradeable

All three registries (Identity, Reputation, Validation) use UUPS proxy pattern, owned by a single EOA (`0x5472...`). No timelock or multisig. Theoretically upgradeable to add cross-chain features, but we don't control the upgrade key.

## Strategy: "Follow the Money"

**Reputation is recorded on the chain where the payment happened.**

| Payment Chain | Identity Chain | Reputation Chain |
|---------------|---------------|-----------------|
| Base | Base | Base |
| Polygon | Polygon | Polygon |
| Ethereum | Ethereum | Ethereum |
| Arbitrum | Arbitrum | Arbitrum |

### Why This Approach

1. **Verifiable**: Escrow TX and reputation TX are on the same chain — anyone can cross-reference
2. **No new infrastructure**: Uses existing protocol exactly as designed
3. **feedbackURI links proof**: The JSON at `execution.market/feedback/...` contains `payment_tx` from the same chain
4. **Honest**: We don't pretend cross-chain reputation exists when it doesn't

### Reputation Fragmentation (Accepted Trade-off)

A worker active on Base and Polygon will have two separate reputation scores. This is a protocol-level limitation that affects ALL ERC-8004 users, not just us. We mitigate with:

#### Off-Chain Reputation Aggregator (Future)

```
GET /api/v1/reputation/aggregate?wallet=0x...
→ {
    "chains": {
      "base": { "agentId": 2106, "score": 85, "feedbacks": 47 },
      "polygon": { "agentId": 312, "score": 90, "feedbacks": 12 }
    },
    "aggregate": {
      "weighted_score": 86,
      "total_feedbacks": 59,
      "primary_chain": "base"
    }
  }
```

Priority: LOW — build when we have actual multi-chain payment volume.

## Implementation Checklist (Per New Chain)

When enabling a new chain for payments+reputation:

### 1. Register EM Agent on New Chain

```bash
# Register our agent on the new chain's IdentityRegistry
# This gives us a NEW agent ID on that chain
cd scripts && npx tsx register-erc8004.ts --network polygon
```

Store the new agent ID in the database and agent-card.json:
```json
// agent-card.json registrations[] array
{ "network": "polygon", "agentId": NEW_ID, "registry": "0x8004A169..." }
```

### 2. Update Platform Config

Add the new chain's agent ID to a lookup table:

```python
# In facilitator_client.py or a new config
EM_AGENT_IDS = {
    "base": 2106,
    "polygon": TBD,
    "ethereum": TBD,
    "arbitrum": TBD,
    "celo": TBD,
    "monad": TBD,
    "avalanche": TBD,
    "optimism": TBD,
}
```

### 3. Parameterize Reputation Functions

Current functions are Base-only. Make `network` a parameter:

```python
# rate_worker() — add network param
async def rate_worker(task_id, score, worker_address, network="base", ...):
    agent_id = EM_AGENT_IDS[network]  # Our agent ID on this chain
    # ... build TX for the correct chain's ReputationRegistry

# give_feedback_direct() — add chain_id and rpc_url params
async def give_feedback_direct(agent_id, value, chain_id=8453, rpc_url=None, ...):
    # Use chain-specific RPC and chain ID
```

### 4. Worker Identity Per Chain

Workers need an ERC-8004 identity on each chain they operate. Options:

- **Option A**: Auto-register on first task per chain (gasless via Facilitator)
- **Option B**: Worker self-registers (needs gas on each chain)
- **Recommended**: Option A for simplicity

### 5. Update feedbackURI Structure

Include chain context in the S3 key:
```
feedback/{network}/{task_id}/{type}_{timestamp}.json
```

The feedbackURI becomes:
```
https://execution.market/feedback/polygon/abc-123/worker_rating_1234.json
```

### 6. Gas Dust for Worker Ratings (Per Chain)

If using Option A1 (worker signs directly), they need native gas on each chain:

| Chain | Gas Token | Estimated Cost per TX | Dust Amount |
|-------|-----------|----------------------|-------------|
| Base | ETH | ~$0.005 | 0.0001 ETH |
| Polygon | POL | ~$0.003 | 0.01 POL |
| Arbitrum | ETH | ~$0.01 | 0.0001 ETH |
| Ethereum | ETH | ~$2-5 | NOT VIABLE for dust |
| Avalanche | AVAX | ~$0.02 | 0.001 AVAX |
| Celo | CELO | ~$0.001 | 0.01 CELO |
| Monad | MON | TBD | TBD |
| Optimism | ETH | ~$0.005 | 0.0001 ETH |

**Note**: Ethereum L1 gas is too expensive for worker-funded reputation TXs. Options:
- Use Facilitator for Ethereum L1 reputation (accept centralization trade-off)
- Wait for EIP-7702 + Paymaster on Ethereum
- Recommend workers use L2s for reputation

## Reputation Rights Matrix

| Who Rates | Who Gets Rated | Condition | Signer |
|-----------|---------------|-----------|--------|
| Agent (us) | Worker | Task approved/rejected | Platform wallet |
| Worker | Agent (us) | Task completed | Worker's wallet (A1: gas dust, A2: gasless) |
| Agent | Agent | Future: agent-to-agent delegation | Calling agent's wallet |

### Proof of Payment in Feedback

The feedback JSON document (at feedbackURI) contains:
```json
{
  "transactions": {
    "payment_tx": "0x...",  // Escrow release or settlement TX
    "reputation_tx": ""     // Filled after reputation TX confirms
  },
  "network": "base"         // Chain where payment happened
}
```

Anyone can verify: read feedbackURI → get payment_tx → check on same chain → confirm payment preceded reputation.

## Worker-Signs-Directly Plan (Option A1 → A2)

### A1: Gas Dust Funding (Immediate — Base Only)

1. Worker completes first approved task on Base
2. Backend sends 0.0001 ETH (Base) to worker's wallet
3. Worker can now sign `giveFeedback()` directly from dashboard
4. `RateAgentModal.tsx` changes from HTTP POST to web3 TX signing

**Anti-farming protections:**
- Fund ONLY after first APPROVED task (not at registration)
- One-time per wallet (flag: `executors.gas_dust_funded_at`)
- Budget cap: $50/month in gas dust
- Rate limit: max 10 new workers funded per hour

### A2: EIP-7702 + Paymaster (Future — All Chains)

1. Dynamic.xyz + ZeroDev integration (already supported)
2. Coinbase Paymaster on Base (up to $15K gas credits)
3. Worker's EOA temporarily delegates to smart account for gas sponsorship
4. Zero gas cost for workers — fully gasless reputation

**Timeline**: When Base enables EIP-7702 (OP Stack Pectra upgrade).

## Files to Modify (Multi-Chain Extension)

| File | Change |
|------|--------|
| `facilitator_client.py` | Add `EM_AGENT_IDS` dict, parameterize `network` in rate functions |
| `direct_reputation.py` | Add `chain_id` and `rpc_url` params to `give_feedback_direct()` |
| `identity.py` | Already supports `network` param — verify all paths work |
| `feedback_store.py` | Add `network` to S3 key path structure |
| `api/reputation.py` | Accept `network` param in rate endpoints |
| `server.py` (MCP tools) | Add `network` param to rating tools |
| `ecs.tf` | Add per-chain RPC URLs, agent IDs |
| `agent-card.json` | Add `registrations[]` entries for each chain |
| Dashboard `RateAgentModal.tsx` | Chain-aware TX signing (A1) |

## Open Questions

1. **Should we register our agent on ALL 8 chains upfront?** Or only when we have active escrow on that chain?
   - Recommendation: Register lazily (on first task per chain) to save gas
2. **What about Ethereum L1?** Gas is too expensive for worker reputation TXs.
   - Recommendation: Use Facilitator for ETH L1, accept the trade-off
3. **Reputation aggregation weighting?** How to weight scores across chains?
   - Recommendation: Simple average weighted by feedback count per chain
