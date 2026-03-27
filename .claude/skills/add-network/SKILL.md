# Add Network / Stablecoin — Multichain Integration Skill

Add a new EVM network or stablecoin to Execution Market. Use when the user says "add network", "add chain", "add stablecoin", "add token", "enable optimism", "add USDT on polygon", or similar.

## Prerequisites

Before adding a network, confirm:
1. **Facilitator support** — The Ultravioleta Facilitator must support the network. Check `https://facilitator.ultravioletadao.xyz/health` or ask the user.
2. **x402r escrow** — Get the AuthCaptureEscrow + PaymentOperator factory + all x402r infrastructure addresses from the [x402r-sdk repo](https://github.com/BackTrackCo/x402r-sdk) `packages/core/src/config/index.ts`.
3. **Token addresses** — Get the official stablecoin contract addresses for the network (USDC, USDT, etc.). Use the x402 SDK or official token docs.
4. **EIP-3009 support** — The token must support `transferWithAuthorization` (EIP-3009). All Circle USDC v2 contracts do. Check `version` field (usually "1" or "2").
5. **ERC-8004 contracts** — Identity Registry + Reputation Registry must be deployed on the chain (CREATE2 deterministic addresses: `0x8004A169...` / `0x8004BAa1...` for mainnets).
6. **Wallet funding** — Production wallet needs tokens on the new chain. Use amounts < $0.30 for testing.
7. **Chain details** — Chain ID, public RPC URL, block explorer URL.

## Step-by-Step: Add a New Network

### Step 1: Backend — sdk_client.py (Single Source of Truth)

**File**: `mcp_server/integrations/x402/sdk_client.py`

1. Add the network to `NETWORK_CONFIG` dict (after last mainnet, before `solana`):
```python
"<network_name>": {
    "chain_id": <chain_id>,
    "network_type": "evm",
    "rpc_url": "https://<public_rpc_url>",
    "tokens": {
        "USDC": {
            "address": "<usdc_address>",
            "name": "USD Coin",
            "version": "<version>",  # "1" or "2"
            "decimals": 6,
        },
        # Add other tokens as needed (USDT, EURC, AUSD, PYUSD)
    },
    # x402r escrow infrastructure (all addresses from x402r-sdk):
    "escrow": "<AuthCaptureEscrow_address>",
    "factory": "<PaymentOperatorFactory_address>",
    "operator": None,  # Set after deploying EM's PaymentOperator
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

2. Add to `EM_ENABLED_NETWORKS` default string (line ~104):
```python
_enabled_raw = os.environ.get(
    "EM_ENABLED_NETWORKS", "base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,<new_network>,solana"
)
```

> **Key fields explained:**
> - `network_type`: Always `"evm"` for EVM chains (only `"svm"` for Solana)
> - `rpc_url`: Public RPC endpoint. Can be overridden at runtime via `{NETWORK_UPPER}_RPC_URL` env var
> - `version`: EIP-3009 version — USDC/EURC/AUSD use `"2"`, USDT/PYUSD use `"1"`
> - `operator`: Set to `None` initially; update after deploying PaymentOperator via `deploy-payment-operator.ts`

### Step 2: Frontend — Dashboard config/networks.ts

**File**: `dashboard/src/config/networks.ts`

Add to the `NETWORKS` array:
```typescript
{ key: '<network_name>', name: '<Display Name>', chainId: <chain_id>, logo: '/<network_name>.png', live: true },
```

### Step 3: Frontend — Dashboard Logo

Place the network logo PNG at: `dashboard/public/<network_name>.png`

Recommended: 200x200px or larger, transparent background, square. Match existing logo style.

### Step 4: Mobile App — constants/networks.ts

**File**: `em-mobile/constants/networks.ts`

Add to the `NETWORKS` array:
```typescript
{ key: "<network_name>", name: "<Display Name>", chainId: <chain_id>, explorer: "https://<explorer_url>", color: "#<hex_color>" },
```

### Step 5: Mobile App — NetworkBadge + Logo

**File**: `em-mobile/components/NetworkBadge.tsx`

Add to `CHAIN_IMAGES`:
```typescript
<network_name>: require("../assets/images/chains/<network_name>.png"),
```

**Asset**: Place logo PNG at `em-mobile/assets/images/chains/<network_name>.png`

### Step 6: Backend — Explorer URLs

**File**: `mcp_server/api/routers/_helpers.py`

Add to `_EXPLORER_TX_URLS` dict (line ~1638):
```python
"<network_name>": "https://<explorer_url>/tx/",
```

### Step 6b: Dashboard — Explorer URLs

**File**: `dashboard/src/utils/blockchain.ts`

Add to both `TX_EXPLORER_URLS` and `ADDRESS_EXPLORER_URLS`:
```typescript
<network_name>: 'https://<explorer_url>/tx/',
// and
<network_name>: 'https://<explorer_url>/address/',
```

### Step 6c: Mobile — CHAIN_IMAGES in Screens

The mobile app has `CHAIN_IMAGES` maps duplicated in multiple screen files. Add the new network to ALL of them:
- `em-mobile/app/(tabs)/earnings.tsx`
- `em-mobile/app/(tabs)/publish.tsx`
- `em-mobile/app/(tabs)/index.tsx`
- `em-mobile/app/task/[id].tsx`

```typescript
<network_name>: require("../../assets/images/chains/<network_name>.png"),
```

Also update `em-mobile/app/about.tsx` `CHAINS` array with the new network name.

### Step 6d: Dashboard — i18n Network Lists

Update hardcoded network lists in all 3 locale files:
- `dashboard/src/i18n/locales/en.json` — FAQ answer (~line 1016), `payDetail1` (~line 1679), `networksTitle` count
- `dashboard/src/i18n/locales/es.json` — Same keys in Spanish
- `dashboard/src/i18n/locales/pt.json` — Same keys in Portuguese

Update the `networksTitle` from "9 Networks" to "10 Networks" (or equivalent).

### Step 7: Backend — Platform Config Defaults

**File**: `mcp_server/config/platform_config.py`

Add `"<network_name>"` to the `x402.supported_networks` default list (line ~133).

### Step 8: Test RPC Endpoint

**File**: `mcp_server/tests/e2e/shared.py`

Add the public RPC to `_RPC_ENDPOINTS` (line ~39):
```python
_RPC_ENDPOINTS = {
    ...
    "<network_name>": "https://<public_rpc_url>",
}
```

### Step 9: Plugin SDK — Static Snapshot

**File**: `em-plugin-sdk/em_plugin_sdk/networks.py`

Add to `NETWORKS` dict and `DEFAULT_ENABLED` frozenset:
```python
"<network_name>": NetworkInfo(
    name="<network_name>", chain_id=<chain_id>, network_type="evm",
    tokens=(
        TokenInfo("USDC", "<usdc_address>", "USD Coin"),
    ),
    has_escrow=True, has_operator=False,  # Set has_operator=True after deploying
),
```

And add `"<network_name>"` to `DEFAULT_ENABLED`.

### Step 10: Deploy Script — PaymentOperator Config

**File**: `scripts/deploy-payment-operator.ts`

Add to `CHAIN_CONFIGS`:
```typescript
<network_name>: {
  chain: <viem_chain_object>,  // Import from viem/chains or define custom
  rpcUrl: "https://<public_rpc_url>",
  escrow: "<AuthCaptureEscrow_address>",
  paymentOperatorFactory: "<factory_address>",
  staticAddressConditionFactory: "0x...",
  orConditionFactory: "0x...",
  staticFeeCalculatorFactory: "0x...",
  protocolFeeConfig: "0x...",
  usdcTvlLimit: "0x...",
  tokenCollector: "0x...",
  payerCondition: "0x...",
},
```

> **Note**: If the chain is not in `viem/chains`, define a custom chain object.

### Step 11: Infrastructure — Terraform

**File**: `infrastructure/terraform/ecs.tf` (line ~184)

Update `EM_ENABLED_NETWORKS` value to include the new network:
```hcl
{ name = "EM_ENABLED_NETWORKS", value = "base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,<new_network>" },
```

### Step 12: Deploy PaymentOperator (CRITICAL — DO NOT SKIP)

> **WARNING: NEVER use pre-deployed operators from the SDK or facilitator team.**
> Pre-deployed operators may be a different contract version missing critical functions
> like `release()`. Always deploy your OWN operator via the factory. This was learned
> from INC-2026-03-27 (SKALE operator missing release function, $0.05 stuck in escrow).

Run the deploy script to create EM's PaymentOperator on the new chain:
```bash
cd scripts && npx tsx deploy-payment-operator.ts --network <network_name> --fase5 --deploy
```

After deploy:
1. Update `sdk_client.py` NETWORK_CONFIG `"operator"` field with the deployed address
2. Update `em-plugin-sdk/em_plugin_sdk/networks.py` `has_operator=True`
3. **Give the operator address to the facilitator team** (IRC #agents or contact Ali) so they add it to their allowlist
4. Wait for facilitator confirmation before testing payments
5. Update `CLAUDE.md` contract table and `skill.md` contract table

### Step 13: Documentation

Update these docs with the new counts and network name:
- `CLAUDE.md` — Network counts, contract tables, supported networks lists, `EM_ENABLED_NETWORKS` default
- `MEMORY.md` — Enabled networks, SDK versions, batch progress
- `docs/SKALE-INTEGRATION.md` or equivalent — Fill in addresses if applicable

### Step 14: ECS Deployment

On next deploy, the Terraform change (Step 11) propagates. Or manually:
```bash
# Force new deployment with updated env var
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment --region us-east-2
```

## What's Automatic (No Action Needed)

These files derive from `sdk_client.py` automatically — **do NOT edit them for network additions**:
- `facilitator_client.py` — ERC-8004 contracts (auto-generated for all NETWORK_CONFIG EVM mainnets)
- `erc8004/__init__.py` — `ERC8004_SUPPORTED_NETWORKS` list (auto-derived)
- `api/routers/x402_discovery.py` — `GET /.well-known/x402` network list (auto-built from NETWORK_CONFIG + ENABLED_NETWORKS)
- `api/routers/payments.py` — Balance queries iterate ENABLED_NETWORKS automatically
- `tests/e2e/test_multichain_infra.py` — Parametrized tests auto-expand to new networks
- `config/platform_config.py` — `get_supported_networks()` falls back to `get_enabled_networks()`
- `api/reputation.py` — `GET /reputation/networks` auto-includes new network
- Admin dashboard (`admin-dashboard/`) — Reads networks dynamically from API

## Step-by-Step: Add a New Stablecoin to an Existing Network

### Step 1: sdk_client.py

Add the token entry under the network's `tokens` dict:
```python
"<SYMBOL>": {
    "address": "<token_contract_address>",
    "name": "<Token Name>",
    "version": "<version>",  # "2" for USDC/EURC/AUSD, "1" for USDT/PYUSD
    "decimals": <decimals>,  # Usually 6 for stablecoins
},
```

### Step 2: Plugin SDK (em-plugin-sdk)

Add the token to the network's `tokens` tuple in `em-plugin-sdk/em_plugin_sdk/networks.py`.

### Step 3: Fund wallet

Ensure production wallet has the new token on that chain.

No other files need changes — stablecoin additions are a 2-file edit.

## Verification

After all changes, run this integration check:
```bash
cd mcp_server && python3 -c "
import sys; sys.path.insert(0, '.')
from integrations.x402.sdk_client import NETWORK_CONFIG, ENABLED_NETWORKS, get_escrow_networks
from integrations.erc8004.facilitator_client import ERC8004_CONTRACTS

for net in ENABLED_NETWORKS:
    if net.endswith(('-sepolia','-amoy','-fuji')): continue
    cfg = NETWORK_CONFIG.get(net)
    if not cfg: print(f'MISSING: {net} not in NETWORK_CONFIG'); continue
    tokens = list(cfg['tokens'].keys())
    has_escrow = bool(cfg.get('escrow'))
    has_operator = bool(cfg.get('operator'))
    has_rpc = bool(cfg.get('rpc_url'))
    has_erc8004 = net in ERC8004_CONTRACTS
    print(f'{net:12s} chain={cfg.get(\"chain_id\",\"N/A\"):>6} tokens={tokens} escrow={has_escrow} operator={has_operator} rpc={has_rpc} erc8004={has_erc8004}')
    if cfg.get('network_type') == 'evm':
        assert has_rpc, f'{net} missing rpc_url'
        assert has_erc8004, f'{net} missing ERC-8004'
print('ALL CHECKS PASSED')
"
```

Also run TypeScript type-check:
```bash
cd dashboard && npx tsc --noEmit --skipLibCheck
```

## Testing Budget

Use amounts **under $0.30** for test tasks. Each mainnet wallet has ~$5 per token. Never use $1+ for testing.

## Complete File Checklist (Quick Reference)

| # | File | Change | Auto? |
|---|------|--------|-------|
| 1 | `mcp_server/integrations/x402/sdk_client.py` | Add to `NETWORK_CONFIG` + `EM_ENABLED_NETWORKS` default | NO |
| 2 | `dashboard/src/config/networks.ts` | Add to `NETWORKS` array | NO |
| 3 | `dashboard/public/<network>.png` | Network logo (200x200, transparent) | NO |
| 4 | `dashboard/src/utils/blockchain.ts` | Add to `TX_EXPLORER_URLS` + `ADDRESS_EXPLORER_URLS` | NO |
| 5 | `dashboard/src/i18n/locales/en.json` | Update network count + FAQ text | NO |
| 6 | `dashboard/src/i18n/locales/es.json` | Update network count + FAQ text | NO |
| 7 | `dashboard/src/i18n/locales/pt.json` | Update network count + FAQ text | NO |
| 8 | `em-mobile/constants/networks.ts` | Add to `NETWORKS` array (with explorer + color) | NO |
| 9 | `em-mobile/components/NetworkBadge.tsx` | Add to `CHAIN_IMAGES` | NO |
| 10 | `em-mobile/assets/images/chains/<network>.png` | Mobile logo asset | NO |
| 11 | `em-mobile/app/(tabs)/earnings.tsx` | Add to `CHAIN_IMAGES` | NO |
| 12 | `em-mobile/app/(tabs)/publish.tsx` | Add to `CHAIN_IMAGES` | NO |
| 13 | `em-mobile/app/(tabs)/index.tsx` | Add to `CHAIN_IMAGES` | NO |
| 14 | `em-mobile/app/task/[id].tsx` | Add to `CHAIN_IMAGES` | NO |
| 15 | `em-mobile/app/about.tsx` | Add to `CHAINS` array | NO |
| 16 | `mcp_server/api/routers/_helpers.py` | Add to `_EXPLORER_TX_URLS` | NO |
| 17 | `mcp_server/config/platform_config.py` | Add to `x402.supported_networks` defaults | NO |
| 18 | `mcp_server/tests/e2e/shared.py` | Add to `_RPC_ENDPOINTS` | NO |
| 19 | `em-plugin-sdk/em_plugin_sdk/networks.py` | Add to `NETWORKS` + `DEFAULT_ENABLED` | NO |
| 20 | `scripts/deploy-payment-operator.ts` | Add to `CHAIN_CONFIGS` | NO |
| 21 | `infrastructure/terraform/ecs.tf` | Update `EM_ENABLED_NETWORKS` value | NO |
| 22 | `CLAUDE.md` | Update network counts, contract tables | NO |
| — | `facilitator_client.py` | ERC-8004 contracts | YES |
| — | `erc8004/__init__.py` | Supported networks list | YES |
| — | `x402_discovery.py` | Discovery endpoint | YES |
| — | `reputation.py` | GET /networks endpoint | YES |
| — | `test_multichain_infra.py` | Parametrized tests | YES |
| — | Admin dashboard | Reads from API | YES |

## Network Reference (Current State)

| Network | Chain ID | Tokens | Escrow | Operator | ERC-8004 |
|---------|----------|--------|--------|----------|----------|
| base | 8453 | USDC, EURC | Yes | Yes | Yes |
| ethereum | 1 | USDC, EURC, PYUSD, AUSD | Yes | Yes | Yes |
| polygon | 137 | USDC, AUSD | Yes | Yes | Yes |
| arbitrum | 42161 | USDC, USDT, AUSD | Yes | Yes | Yes |
| celo | 42220 | USDC, USDT | Yes | Yes | Yes |
| monad | 143 | USDC, AUSD | Yes | Yes | Yes |
| avalanche | 43114 | USDC, EURC, AUSD | Yes | Yes | Yes |
| optimism | 10 | USDC, USDT | Yes | Yes | Yes |
| solana | — | USDC, AUSD | No | No | No (SVM) |
