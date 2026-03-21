# SKALE Network Integration — Execution Market

**Date:** 2026-03-21
**Status:** Pre-Integration (Blocked on x402r contracts + facilitator SKALE support)
**Priority:** HIGH — SKALE is actively courting agent/x402 projects
**Updated:** 2026-03-21 (consolidated from 4-agent deep audit of codebase)

---

## TL;DR

Add SKALE as a payment network for Execution Market. SKALE offers **zero gas fees** for all transactions — escrow lock, release, refund, and reputation all cost $0 in gas. This is a game-changer for micro-task economics.

---

## Why SKALE

| Feature | Current (Base) | SKALE |
|---------|---------------|-------|
| Gas cost per TX | ~$0.001-0.01 | **$0.00 (zero)** |
| Block time | ~2s | ~1s |
| EVM compatible | Yes | Yes |
| ERC-8004 deployed | Yes | **Pending** (Ali deploying) |
| x402r escrow contracts | Yes | **Pending** (Ali deploying) |
| USDC available | Yes (native) | TBD (bridged or native) |
| Facilitator support | Yes | **Pending** (Ali's facilitator) |

**Key value prop:** Zero gas means workers keep 100% of earnings minus platform fee, escrow operations cost $0, and reputation feedback is free.

---

## Dependencies & Blockers (MUST resolve before integration)

### Blocker 1: x402r Facilitator Support
**Owner:** Ali (x402r team)
**What's needed:**
- x402r escrow contracts deployed on SKALE (AuthCaptureEscrow, PaymentOperatorFactory, all infra contracts)
- Facilitator service accepting SKALE transactions
- All contract addresses shared

### Blocker 2: ERC-8004 Contracts on SKALE
**Owner:** Ali (ERC-8004 team)
**What's needed:**
- Deploy IdentityRegistry + ReputationRegistry on SKALE via CREATE2
- Expected addresses (deterministic): `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (Identity) / `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` (Reputation)

### Blocker 3: USDC on SKALE
**What's needed:**
- Identify which USDC variant exists on SKALE (native, bridged)
- **Verify EIP-3009 support** (`transferWithAuthorization`) — critical for gasless payments
- Get token contract address and EIP-3009 `version` ("1" or "2")

### Blocker 4: SKALE Chain Details
**What's needed:**
- Chain ID (Europa? Calypso? Dedicated AppChain?)
- Public RPC endpoint
- Block explorer URL

---

## SKALE Network Details (To Be Filled)

```
Chain Name:       SKALE ??? (Europa / Calypso / AppChain)
Chain ID:         ???
RPC URL:          https://???
Block Explorer:   https://???
Gas Model:        ZERO (sFUEL distributed free, no real cost)
Brand Color:      #??? (hex for mobile NetworkBadge)

USDC Address:     0x???
USDC Version:     ??? (must be "1" or "2" for EIP-3009)
EIP-3009:         ??? (CRITICAL — must support transferWithAuthorization)

x402r Escrow (AuthCaptureEscrow):          0x???
x402r Factory (PaymentOperatorFactory):    0x???
x402r Infrastructure:
  staticAddressConditionFactory:           0x???
  orConditionFactory:                      0x???
  staticFeeCalculatorFactory:              0x???
  protocolFeeConfig:                       0x???
  usdcTvlLimit:                            0x???
  tokenCollector:                          0x???
  payerCondition:                          0x???

EM PaymentOperator:   0x??? (we deploy after factory is ready)

ERC-8004 Identity:    0x??? (pending CREATE2 deployment)
ERC-8004 Reputation:  0x??? (pending CREATE2 deployment)
```

---

## Full Integration Checklist (14 Steps)

> **Skill reference:** `.claude/skills/add-network/SKILL.md` has the generic procedure. This checklist is SKALE-specific with exact file locations and line numbers.

### Phase 1: Backend Configuration

- [ ] **1. sdk_client.py — NETWORK_CONFIG** (`mcp_server/integrations/x402/sdk_client.py`, after optimism ~line 400, before solana)
  ```python
  "skale": {
      "chain_id": <SKALE_CHAIN_ID>,
      "network_type": "evm",
      "rpc_url": "https://<skale_rpc_endpoint>",
      "tokens": {
          "USDC": {
              "address": "<usdc_on_skale>",
              "name": "USD Coin",
              "version": "<version>",
              "decimals": 6,
          },
      },
      "escrow": "<AuthCaptureEscrow>",
      "factory": "<PaymentOperatorFactory>",
      "operator": None,  # Updated in step 12
      "x402r_infra": {
          "staticAddressConditionFactory": "0x...",
          "orConditionFactory": "0x...",
          "staticFeeCalculatorFactory": "0x...",
          "protocolFeeConfig": "0x...",
          "usdcTvlLimit": "0x...",
          "tokenCollector": "0x...",
          "payerCondition": "0x...",
      },
  },
  ```

- [ ] **2. sdk_client.py — EM_ENABLED_NETWORKS default** (~line 104)
  Add `skale` to the default string:
  ```python
  "base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,skale,solana"
  ```

- [ ] **3. _helpers.py — Explorer URL** (`mcp_server/api/routers/_helpers.py`, `_EXPLORER_TX_URLS` dict ~line 1638)
  ```python
  "skale": "https://<skale_explorer>/tx/",
  ```

- [ ] **4. platform_config.py — Defaults** (`mcp_server/config/platform_config.py`, `x402.supported_networks` ~line 133)
  Add `"skale"` to the list.

### Phase 2: Frontend (Dashboard + Mobile)

- [ ] **5. Dashboard networks.ts** (`dashboard/src/config/networks.ts`, `NETWORKS` array)
  ```typescript
  { key: 'skale', name: 'SKALE', chainId: <chain_id>, logo: '/skale.png', live: true },
  ```

- [ ] **6. Dashboard logo** — `dashboard/public/skale.png` (200x200px, transparent, square)

- [ ] **7. Dashboard explorer URLs** (`dashboard/src/utils/blockchain.ts`)
  Add to both `TX_EXPLORER_URLS` and `ADDRESS_EXPLORER_URLS`:
  ```typescript
  skale: 'https://<skale_explorer>/tx/',
  skale: 'https://<skale_explorer>/address/',
  ```

- [ ] **8. Dashboard i18n** — Update network counts and lists in all 3 locales:
  - `dashboard/src/i18n/locales/en.json`: `networksTitle` -> "10 Networks", FAQ answer (~line 1016), `payDetail1` (~line 1679)
  - `dashboard/src/i18n/locales/es.json`: Same keys in Spanish
  - `dashboard/src/i18n/locales/pt.json`: Same keys in Portuguese

- [ ] **9. Mobile networks.ts** (`em-mobile/constants/networks.ts`)
  ```typescript
  { key: "skale", name: "SKALE", chainId: <chain_id>, explorer: "https://<explorer>", color: "#<hex>" },
  ```

- [ ] **10. Mobile NetworkBadge** (`em-mobile/components/NetworkBadge.tsx`, `CHAIN_IMAGES`)
  ```typescript
  skale: require("../assets/images/chains/skale.png"),
  ```

- [ ] **11. Mobile CHAIN_IMAGES in screens** — Add to all screen files that have their own `CHAIN_IMAGES`:
  - `em-mobile/app/(tabs)/earnings.tsx`
  - `em-mobile/app/(tabs)/publish.tsx`
  - `em-mobile/app/(tabs)/index.tsx`
  - `em-mobile/app/task/[id].tsx`

- [ ] **12. Mobile about.tsx** (`em-mobile/app/about.tsx`) — Add "SKALE" to `CHAINS` array

- [ ] **13. Mobile logo** — `em-mobile/assets/images/chains/skale.png`

### Phase 3: SDK & Tests

- [ ] **14. Plugin SDK** (`em-plugin-sdk/em_plugin_sdk/networks.py`)
  Add to `NETWORKS` dict:
  ```python
  "skale": NetworkInfo(
      name="skale", chain_id=<chain_id>, network_type="evm",
      tokens=(TokenInfo("USDC", "<address>", "USD Coin"),),
      has_escrow=True, has_operator=False,
  ),
  ```
  Add `"skale"` to `DEFAULT_ENABLED` frozenset.

- [ ] **15. Test RPC** (`mcp_server/tests/e2e/shared.py`, `_RPC_ENDPOINTS` ~line 39)
  ```python
  "skale": "https://<skale_rpc_endpoint>",
  ```

### Phase 4: Deployment Infrastructure

- [ ] **16. Deploy PaymentOperator** on SKALE
  First add to `scripts/deploy-payment-operator.ts` `CHAIN_CONFIGS`:
  ```typescript
  skale: {
    chain: <custom_or_viem_chain>,
    rpcUrl: "https://<skale_rpc>",
    escrow: "<AuthCaptureEscrow>",
    paymentOperatorFactory: "<factory>",
    staticAddressConditionFactory: "0x...",
    orConditionFactory: "0x...",
    staticFeeCalculatorFactory: "0x...",
    protocolFeeConfig: "0x...",
    usdcTvlLimit: "0x...",
    tokenCollector: "0x...",
    payerCondition: "0x...",
  },
  ```
  Then run: `cd scripts && npx tsx deploy-payment-operator.ts --network skale --deploy`
  Then update `sdk_client.py` `"operator"` field + `em-plugin-sdk` `has_operator=True`.

- [ ] **17. Terraform** (`infrastructure/terraform/ecs.tf`, line ~184)
  Update `EM_ENABLED_NETWORKS` value to include `skale`.

- [ ] **18. Documentation**
  - [ ] `CLAUDE.md` — Update network counts (9 EVM + Solana), contract table, `EM_ENABLED_NETWORKS` default
  - [ ] `MEMORY.md` — Update enabled networks, batch progress
  - [ ] This file — Fill in all `???` addresses above

### Phase 5: Verification & Golden Flow

- [ ] **19. Run verification script** (from skill):
  ```bash
  cd mcp_server && python3 -c "
  import sys; sys.path.insert(0, '.')
  from integrations.x402.sdk_client import NETWORK_CONFIG, ENABLED_NETWORKS
  from integrations.erc8004.facilitator_client import ERC8004_CONTRACTS
  cfg = NETWORK_CONFIG['skale']
  print(f'chain_id: {cfg[\"chain_id\"]}')
  print(f'tokens: {list(cfg[\"tokens\"].keys())}')
  print(f'escrow: {bool(cfg.get(\"escrow\"))}')
  print(f'operator: {cfg.get(\"operator\")}')
  print(f'erc8004: {\"skale\" in ERC8004_CONTRACTS}')
  print(f'enabled: {\"skale\" in ENABLED_NETWORKS}')
  "
  ```

- [ ] **20. TypeScript type-check**: `cd dashboard && npx tsc --noEmit --skipLibCheck`

- [ ] **21. Run pytest** (tests auto-parametrize to include SKALE):
  ```bash
  cd mcp_server && pytest tests/e2e/test_multichain_infra.py -k "skale" -v
  ```

- [ ] **22. Golden Flow on SKALE** — Full lifecycle test:
  ```bash
  python scripts/e2e_golden_flow.py --network skale
  ```
  Verify: task creation -> escrow lock ($0 gas) -> worker registration -> assignment -> evidence -> approval + payment -> bidirectional reputation ($0 gas) -> on-chain verification

- [ ] **23. Fund production wallet** with USDC on SKALE (< $5 for testing)

- [ ] **24. Deploy to ECS** (push to main triggers CI/CD, or manual force deploy)

---

## What's Automatic (No Code Changes Needed)

Once `sdk_client.py` has SKALE in NETWORK_CONFIG, these auto-derive:

| Component | File | What happens |
|-----------|------|-------------|
| ERC-8004 contracts | `facilitator_client.py` | Auto-generates `ERC8004_CONTRACTS["skale"]` with CREATE2 registry addresses |
| ERC-8004 exports | `erc8004/__init__.py` | `ERC8004_SUPPORTED_NETWORKS` includes "skale" |
| x402 discovery | `x402_discovery.py` | `GET /.well-known/x402` includes SKALE in networks array |
| Reputation API | `reputation.py` | `GET /reputation/networks` includes SKALE |
| Balance queries | `payments.py` | Auto-iterates SKALE for balance checks |
| E2E tests | `test_multichain_infra.py` | `@pytest.mark.parametrize` auto-expands to SKALE |
| Admin dashboard | `admin-dashboard/` | Reads networks from API dynamically |

---

## Gas Economics Comparison

For a typical task lifecycle (create -> assign -> submit -> approve -> rate):

| Transaction | Base Gas | SKALE Gas | Savings |
|------------|----------|-----------|---------|
| Escrow Lock (authorize) | ~$0.003 | $0.00 | 100% |
| Escrow Release (capture) | ~$0.003 | $0.00 | 100% |
| ERC-8004 Rate Worker | ~$0.002 | $0.00 | 100% |
| ERC-8004 Rate Agent | ~$0.002 | $0.00 | 100% |
| **Total per task** | **~$0.010** | **$0.00** | **100%** |
| **1,000 tasks/month** | **~$10** | **$0.00** | **$10/mo** |
| **100,000 tasks/month** | **~$1,000** | **$0.00** | **$1,000/mo** |

---

## Strategic Notes

1. **SKALE is actively marketing to AI agent projects** — partnership opportunity.
2. **SKALE Expand v1 on Base** — Base bridge could enable cross-chain workflows.
3. **AppChain option** — EM could get its own SKALE chain. Worth discussing if volume justifies it.
4. **Zero gas = unlimited reputation** — On SKALE, rate EVERY interaction, build richer trust profiles.
5. **First mover** — If EM is among the first agent marketplaces on SKALE, grant opportunities are likely.

---

## SKALE-Specific Considerations

### Zero Gas & sFUEL
- SKALE uses sFUEL (free "gas token") — no real cost, but wallets need a small sFUEL amount
- The Facilitator wallet (`0x1030...`) needs sFUEL on SKALE to submit TXs
- Workers need sFUEL for on-chain operations (if any are wallet-signed)
- sFUEL can be obtained free from SKALE faucets

### EIP-3009 Compatibility (CRITICAL)
- SKALE's USDC may be a bridged version — must verify it implements `transferWithAuthorization`
- If USDC on SKALE does NOT support EIP-3009, the gasless x402 flow won't work
- Alternative: Could use a SKALE-native stablecoin if EIP-3009 compatible

### viem Chain Definition
- SKALE may not be in `viem/chains` — check, and if not, define a custom chain:
  ```typescript
  import { defineChain } from 'viem'
  const skale = defineChain({
    id: <chain_id>,
    name: 'SKALE',
    nativeCurrency: { name: 'sFUEL', symbol: 'sFUEL', decimals: 18 },
    rpcUrls: { default: { http: ['https://<rpc>'] } },
    blockExplorers: { default: { name: 'SKALE Explorer', url: 'https://<explorer>' } },
  })
  ```

---

## Next Steps

1. **Get addresses from Ali** — All x402r infra + ERC-8004 contracts on SKALE
2. **Verify USDC EIP-3009** — Critical blocker for gasless payments
3. **Get chain details** — Chain ID, RPC, explorer, brand color
4. **Obtain SKALE logo** — PNG for dashboard + mobile (200x200, transparent)
5. **Run the 14-step checklist** above
6. **Golden Flow test** — Verify full lifecycle with zero gas

---

*Document created 2026-03-21 — Updated with comprehensive 4-agent audit*
*Synchronized with `.claude/skills/add-network/SKILL.md`*
