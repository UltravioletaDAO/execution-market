# Add Network / Stablecoin — Multichain Integration Skill

Add a new EVM network or stablecoin to Execution Market. Use when the user says "add network", "add chain", "add stablecoin", "add token", "enable optimism", "add USDT on polygon", or similar.

## Prerequisites

Before adding a network, confirm:
1. **Facilitator support** — The Ultravioleta Facilitator must support the network. Check `https://facilitator.ultravioletadao.xyz/health` or ask the user.
2. **x402r escrow** — Get the AuthCaptureEscrow + PaymentOperator factory addresses from the [x402r-sdk repo](https://github.com/BackTrackCo/x402r-sdk) `packages/core/src/config/index.ts`.
3. **Token addresses** — Get the official stablecoin contract addresses for the network (USDC, USDT, etc.). Use the x402 SDK or official token docs.
4. **EIP-3009 support** — The token must support `transferWithAuthorization` (EIP-3009). All Circle USDC v2 contracts do. Check `version` field (usually "1" or "2").
5. **Wallet funding** — Production wallet (`0xD386...`) needs tokens on the new chain. Use amounts < $0.30 for testing.

## Step-by-Step: Add a New Network

### Step 1: Backend — sdk_client.py (Single Source of Truth)

**File**: `mcp_server/integrations/x402/sdk_client.py`

1. Add the network to `NETWORK_CONFIG` dict:
```python
"<network_name>": {
    "chain_id": <chain_id>,
    "tokens": {
        "USDC": {
            "address": "<usdc_address>",
            "name": "USD Coin",
            "version": "<version>",  # "1" or "2"
            "decimals": 6,
        },
        # Add other tokens as needed (USDT, EURC, AUSD, PYUSD)
    },
    "escrow": "<escrow_address>",      # AuthCaptureEscrow (from x402r-sdk)
    "factory": "<factory_address>",    # PaymentOperator factory (from x402r-sdk)
},
```

2. Add to `EM_ENABLED_NETWORKS` default string (line ~93):
```python
_enabled_raw = os.environ.get(
    "EM_ENABLED_NETWORKS", "base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,<new_network>"
)
```

### Step 2: Frontend — config/networks.ts

**File**: `dashboard/src/config/networks.ts`

Add to the `NETWORKS` array:
```typescript
{ key: '<network_name>', name: '<Display Name>', chainId: <chain_id>, logo: '/<network_name>.png', live: true },
```

### Step 3: Frontend — wagmi.ts

**File**: `dashboard/src/lib/wagmi.ts`

1. Add the chain import:
```typescript
import { base, ..., <network_name> } from 'wagmi/chains'
```

2. Add to `chains` array and `transports`:
```typescript
chains: [..., <network_name>],
transports: {
    ...
    [<network_name>.id]: http(),
},
```

> **Note**: wagmi chain objects require manual import — this cannot be automated from config.

### Step 4: Logo

Place the network logo PNG at: `dashboard/public/<network_name>.png`

Recommended: 200x200px or larger, transparent background, square.

### Step 5: Test RPC Endpoint

**File**: `mcp_server/tests/e2e/shared.py`

Add the public RPC to `_RPC_ENDPOINTS`:
```python
_RPC_ENDPOINTS = {
    ...
    "<network_name>": "https://<public_rpc_url>",
}
```

### Step 6: Documentation

Update these docs with the new counts and network name:
- `CLAUDE.md` — Network counts, contract tables, supported networks lists
- `MEMORY.md` — Batch progress section, SDK versions, enabled networks

### Step 7: ECS Deployment

On next deploy, update the ECS task definition env var:
```bash
# Register new task def revision with updated EM_ENABLED_NETWORKS
# Then force new deployment
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment --region us-east-2
```

## What's Automatic (No Action Needed)

These files derive from sdk_client.py automatically:
- `facilitator_client.py` — ERC-8004 contracts (auto-generated for all NETWORK_CONFIG mainnets)
- `tests/e2e/shared.py` — ENABLED_NETWORKS + NETWORKS dict
- `tests/e2e/test_multichain_infra.py` — ESCROW_CONTRACTS dict
- `config/platform_config.py` — `get_supported_networks()` default
- `scripts/simulate_agent.py` — SUPPORTED_NETWORKS
- `dashboard/ProtocolStack.tsx` — Imports from config/networks.ts

## Step-by-Step: Add a New Stablecoin to an Existing Network

### Step 1: sdk_client.py

Add the token entry under the network's `tokens` dict:
```python
"<SYMBOL>": {
    "address": "<token_contract_address>",
    "name": "<Token Name>",
    "version": "<version>",
    "decimals": <decimals>,  # Usually 6 for stablecoins
},
```

### Step 2: Fund wallet

Ensure production wallet has the new token on that chain.

No other files need changes — stablecoin additions are a single-file edit.

## Verification

After all changes, run this integration check:
```bash
cd mcp_server && python3 -c "
import sys; sys.path.insert(0, '.')
from integrations.x402.sdk_client import NETWORK_CONFIG, ENABLED_NETWORKS, get_escrow_networks
from integrations.erc8004.facilitator_client import ERC8004_CONTRACTS

for net in ENABLED_NETWORKS:
    if net.endswith(('-sepolia','-amoy','-fuji')): continue
    cfg = NETWORK_CONFIG[net]
    tokens = list(cfg['tokens'].keys())
    has_escrow = bool(cfg.get('escrow'))
    has_erc8004 = net in ERC8004_CONTRACTS
    print(f'{net:12s} chain={cfg[\"chain_id\"]:>6d} tokens={tokens} escrow={has_escrow} erc8004={has_erc8004}')
    assert has_escrow, f'{net} missing escrow'
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

## Network Reference (Current State)

| Network | Chain ID | Tokens | Escrow | ERC-8004 |
|---------|----------|--------|--------|----------|
| base | 8453 | USDC, EURC | Yes | Yes |
| ethereum | 1 | USDC, EURC, PYUSD, AUSD | Yes | Yes |
| polygon | 137 | USDC, AUSD | Yes | Yes |
| arbitrum | 42161 | USDC, USDT, AUSD | Yes | Yes |
| celo | 42220 | USDC, USDT | Yes | Yes |
| monad | 143 | USDC, AUSD | Yes | Yes |
| avalanche | 43114 | USDC, EURC, AUSD | Yes | Yes |
| optimism | 10 | USDC, USDT | Yes | Yes |
