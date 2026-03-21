# SKALE Network Integration — Execution Market

**Date:** 2026-03-21
**Status:** Pre-Integration (Blocked on x402r facilitator SKALE support)
**Priority:** HIGH — SKALE is actively courting agent/x402 projects
**Author:** Clawd (via codebase analysis)

---

## TL;DR

Add SKALE as a payment network for Execution Market. SKALE offers **zero gas fees** for all transactions — escrow lock, release, refund, and reputation all cost $0 in gas. This is a game-changer for micro-task economics where gas fees on L2s ($0.001-0.01) still add up at scale.

---

## Why SKALE

| Feature | Current (Base) | SKALE |
|---------|---------------|-------|
| Gas cost per TX | ~$0.001-0.01 | **$0.00 (zero)** |
| Block time | ~2s | ~1s |
| EVM compatible | ✅ | ✅ |
| ERC-8004 deployed | ✅ | ❌ (needs deployment) |
| x402r escrow contracts | ✅ | ❌ (Ali deploying — ETA: tomorrow) |
| USDC available | ✅ (native) | TBD (bridged or native) |
| Facilitator support | ✅ | ❌ (Ali's x402r facilitator — ETA: tomorrow) |

**Key value prop:** For a marketplace doing thousands of micro-tasks ($0.10-$5.00), zero gas fees mean:
- Workers keep 100% of their earnings minus platform fee (no gas deducted)
- Escrow lock/release/refund costs the platform $0
- ERC-8004 reputation feedback costs $0 per rating
- Can support sub-$0.01 bounties economically

---

## Current Architecture (How a new chain gets added)

### 1. NETWORK_CONFIG (sdk_client.py)

Every supported chain has an entry in `NETWORK_CONFIG`:

```python
# mcp_server/integrations/x402/sdk_client.py line ~118
NETWORK_CONFIG: Dict[str, Dict[str, Any]] = {
    "skale": {
        "chain_id": ???,             # SKALE Europa chain ID
        "network_type": "evm",
        "rpc_url": "https://???",    # SKALE Europa RPC endpoint
        "tokens": {
            "USDC": {
                "address": "0x???",  # USDC on SKALE (bridged)
                "name": "USD Coin",
                "version": "???",    # Check if EIP-3009 is supported
                "decimals": 6,
            },
        },
        # x402r escrow infrastructure (once Ali deploys):
        "escrow": "0x???",           # AuthCaptureEscrow
        "factory": "0x???",          # PaymentOperatorFactory
        "operator": "0x???",         # EM's PaymentOperator instance
        "x402r_infra": {
            "staticAddressConditionFactory": "0x???",
            "orConditionFactory": "0x???",
            "staticFeeCalculatorFactory": "0x???",
            "protocolFeeConfig": "0x???",
            "usdcTvlLimit": "0x???",
            "tokenCollector": "0x???",
            "payerCondition": "0x???",
        },
    },
}
```

### 2. Enabled Networks (Environment Variable)

```bash
# ECS task definition env var
EM_ENABLED_NETWORKS=base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,skale
```

Currently set in: ECS task definition for `em-production-mcp-server`

### 3. ERC-8004 Contracts

Need to be deployed on SKALE. Same addresses if using CREATE2:
- **IdentityRegistry:** `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
- **ReputationRegistry:** `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`

Currently deployed on: Ethereum, Base, Abstract, Arbitrum, Avalanche, BSC, Celo, Gnosis, Goat, Linea, Mantle, MegaETH, Metis, Monad, Optimism, Polygon, Scroll — **NOT on SKALE yet**.

### 4. Dashboard Network Selector

```typescript
// dashboard/src/components/... (task creation form)
// Add SKALE to the network dropdown
// File: Check CreateTask.tsx or wherever payment_network is selected
```

### 5. Facilitator Configuration

The x402r facilitator (operated by Ali/x402r team) needs to:
1. Deploy escrow contracts (AuthCaptureEscrow, PaymentOperatorFactory) on SKALE
2. Add SKALE chain support to the facilitator service
3. Share deployed contract addresses

---

## Dependencies & Blockers

### Blocker 1: x402r Facilitator Support
**Owner:** Ali (x402r team)
**ETA:** Tomorrow (per Saúl, 2026-03-20)
**What's needed:**
- x402r escrow contracts deployed on SKALE
- Facilitator service accepting SKALE transactions
- Contract addresses shared

**Note:** Saúl says the facilitator already has SKALE support in code but hasn't been pushed to the remote repo yet.

### Blocker 2: ERC-8004 Contracts on SKALE
**Owner:** ERC-8004 team (Ali)
**What's needed:**
- Deploy IdentityRegistry + ReputationRegistry on SKALE
- Verify addresses (should be deterministic: `0x8004A1...` and `0x8004BA...`)
- Add to erc-8004-contracts README

### Blocker 3: USDC on SKALE
**What's needed:**
- Identify which USDC variant exists on SKALE (native, bridged from Ethereum, etc.)
- Verify EIP-3009 support (required for gasless authorize/transfer)
- Get token contract address and version

### Blocker 4: SKALE Chain Details
**What's needed:**
- Chain ID for the specific SKALE chain (Europa? Calypso? A dedicated AppChain?)
- Public RPC endpoint
- Block explorer URL (for BaseScan-style TX links)

---

## Integration Checklist

### Phase 1: Configuration (Once Ali deploys contracts)
- [ ] Get SKALE chain ID, RPC URL, and explorer URL
- [ ] Get USDC token address on SKALE
- [ ] Get x402r contract addresses (escrow, factory, infra)
- [ ] Add `"skale"` entry to `NETWORK_CONFIG` in `sdk_client.py`
- [ ] Deploy EM's PaymentOperator on SKALE (via `deploy-payment-operator.ts`)
- [ ] Add operator address to config

### Phase 2: Backend
- [ ] Add `"skale"` to `EM_ENABLED_NETWORKS` env var in ECS
- [ ] Verify `_get_fase2_client()` works with SKALE chain ID
- [ ] Test escrow lifecycle: authorize → release / authorize → refund
- [ ] Test gasless behavior (confirm $0 gas for all TX types)
- [ ] Add SKALE explorer URL to `_EXPLORER_TX_URLS` in `_helpers.py`

### Phase 3: ERC-8004 (Identity + Reputation)
- [ ] Confirm ERC-8004 contracts deployed on SKALE
- [ ] Add SKALE to `integrations/erc8004/` network config
- [ ] Test identity registration on SKALE
- [ ] Test reputation feedback on SKALE (gasless = free ratings!)

### Phase 4: Dashboard
- [ ] Add SKALE to network selector in task creation
- [ ] Add SKALE chain icon/branding
- [ ] Add SKALE explorer links for TX display
- [ ] Test end-to-end from dashboard

### Phase 5: Testing
- [ ] Create task with SKALE payment
- [ ] Worker applies → assign → escrow locks (verify $0 gas)
- [ ] Worker submits evidence → approve → escrow releases (verify $0 gas)
- [ ] Reputation feedback submitted (verify $0 gas)
- [ ] Verify on SKALE block explorer

---

## Files to Modify

| File | Change |
|------|--------|
| `mcp_server/integrations/x402/sdk_client.py` | Add `"skale"` to `NETWORK_CONFIG` |
| `mcp_server/api/routers/_helpers.py` | Add SKALE to `_EXPLORER_TX_URLS` |
| `mcp_server/integrations/erc8004/` | Add SKALE network support |
| `mcp_server/config/platform_config.py` | Add SKALE to default supported networks |
| `dashboard/src/` | Add SKALE to network selector + explorer links |
| ECS environment | Add `skale` to `EM_ENABLED_NETWORKS` |

---

## SKALE Network Details (To Be Filled)

```
Chain Name:       SKALE ??? (Europa / Calypso / AppChain)
Chain ID:         ???
RPC URL:          https://???
Block Explorer:   https://???
Gas Model:        ZERO (sFUEL distributed free, no real cost)

USDC Address:     0x???
USDC Version:     ???
EIP-3009:         ??? (critical for gasless authorize)

x402r Escrow:     0x??? (pending Ali deployment)
x402r Factory:    0x??? (pending Ali deployment)
EM Operator:      0x??? (we deploy after factory is ready)

ERC-8004 Identity:    0x??? (pending deployment)
ERC-8004 Reputation:  0x??? (pending deployment)
```

---

## Gas Economics Comparison

For a typical task lifecycle (create → assign → submit → approve → rate):

| Transaction | Base Gas | SKALE Gas | Savings |
|------------|----------|-----------|---------|
| Escrow Lock (authorize) | ~$0.003 | $0.00 | 100% |
| Escrow Release (capture) | ~$0.003 | $0.00 | 100% |
| ERC-8004 Rate Worker | ~$0.002 | $0.00 | 100% |
| ERC-8004 Rate Agent | ~$0.002 | $0.00 | 100% |
| **Total per task** | **~$0.010** | **$0.00** | **100%** |
| **1,000 tasks/month** | **~$10** | **$0.00** | **$10/mo** |
| **100,000 tasks/month** | **~$1,000** | **$0.00** | **$1,000/mo** |

At scale, SKALE's zero-gas model is significant — especially for reputation (which fires twice per task: agent→worker + worker→agent).

---

## Strategic Notes

1. **SKALE is actively marketing to AI agent projects** — their homepage now highlights agents and x402. Partnership opportunity.

2. **SKALE Expand v1 on Base** — SKALE has a Base bridge. Could enable cross-chain workflows (create task on Base, settle on SKALE).

3. **AppChain option** — SKALE allows dedicated app chains. EM could get its own SKALE chain with custom parameters. Worth discussing if volume justifies it.

4. **Zero gas = unlimited reputation** — Currently we're strategic about on-chain reputation (costs gas). On SKALE, we could rate EVERY interaction, build richer trust profiles.

5. **First mover** — If EM is among the first agent marketplaces on SKALE, partnership/grant opportunities are likely.

---

## Next Steps

1. **Wait for Ali** — x402r facilitator SKALE support (ETA: tomorrow, 2026-03-21)
2. **Get SKALE chain details** — chain ID, RPC, USDC address
3. **Deploy ERC-8004** — Ask Ali to deploy Identity + Reputation on SKALE
4. **Add NETWORK_CONFIG** — Once addresses are known
5. **Test golden flow** — Create → Assign → Submit → Approve → Rate (all zero gas)
6. **Deploy** — Add to EM_ENABLED_NETWORKS, redeploy backend + frontend

---

*Document created 2026-03-21 1:30 AM EST — Dream Session*
*Will update when Ali provides contract addresses*
