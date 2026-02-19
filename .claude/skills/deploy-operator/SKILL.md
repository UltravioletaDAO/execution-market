# Deploy PaymentOperator — Multi-chain Operator Deployment Skill

Deploy or redeploy Fase 5 PaymentOperators across all supported chains. Use when the user says "deploy operator", "redeploy operators", "deploy on ethereum", "deploy payment operator", or similar.

## Prerequisites

1. **Deployer wallet funded** — `YOUR_DEV_WALLET` (key in `.env.local` as `WALLET_PRIVATE_KEY`) needs native gas tokens on target chain:
   - Ethereum: ~0.002 ETH ($5)
   - Polygon: ~0.5 MATIC ($0.50)
   - Arbitrum: ~0.0005 ETH ($1)
   - Avalanche: ~0.05 AVAX ($1)
   - Celo: ~0.5 CELO ($0.30)
   - Monad: ~0.001 MON
   - Optimism: ~0.0005 ETH ($1)
   - Base: ~0.0005 ETH ($1)

2. **x402r sub-factories deployed on target chain** — BackTrack deploys these. Verify with `--dry-run` first.

3. **Node.js + tsx** — `cd scripts && npm install`

## Architecture

Each Fase 5 operator deployment creates 4 contracts per chain:

```
1. StaticFeeCalculator(1300bps = 13%)     — splits fees at release
2. StaticAddressCondition(Facilitator)     — authorizes our Facilitator
3. OrCondition([Payer, Facilitator])       — release condition
4. PaymentOperator                         — the operator itself
```

All deployed via x402r factory contracts (CREATE2 pattern). The script verifies factory bytecode on-chain before attempting deployment.

**Key config:**
- Fee: 1300 BPS (13%) — agent pays bounty, worker gets 87%, operator holds 13%
- Release: OR(Payer | Facilitator) — prevents stuck funds
- Refund: FacilitatorOnly — prevents payer bypass
- TVL limit: Set per chain by BackTrack (default $1,000 for new operators)

## Step-by-Step: Deploy on a New Chain

### Step 1: Dry Run

```bash
cd scripts
npx tsx deploy-payment-operator.ts --fase5 --network <chain> --dry-run
```

**Expected output:**
- All 4 factories show "OK (XXXX bytes)"
- Steps 1-4 show "DRY RUN: Would deploy..."
- If any factory shows "MISSING" — BackTrack hasn't deployed on that chain yet. Contact Ali.

### Step 2: Deploy

```bash
cd scripts
npx tsx deploy-payment-operator.ts --fase5 --network <chain>
```

**Expected output (4 TXs):**
1. StaticFeeCalculator deployed at `0x...`
2. StaticAddressCondition(Facilitator) deployed at `0x...`
3. OrCondition deployed at `0x...`
4. PaymentOperator deployed at `0x...`
5. Verification: 5/5 checks pass

**Save the PaymentOperator address** — this goes in `sdk_client.py` and `CLAUDE.md`.

### Step 3: Update Python Config

**File**: `mcp_server/integrations/x402/sdk_client.py`

Find the network in `NETWORK_CONFIG` and set the `"operator"` field:

```python
"<network>": {
    ...
    "operator": "<deployed_operator_address>",
    ...
}
```

### Step 4: Update CLAUDE.md

Add a row to the On-Chain Contracts table:

```markdown
| **EM PaymentOperator (Fase 5)** | **<Network>** | **`<address>`** |
```

### Step 5: Register in Facilitator Allowlist

Contact the Facilitator team (IRC `#Agents` or direct):
```
New EM operators to allowlist:
- <Network>: <operator_address>
```

The Facilitator needs the operator address in its `addresses.rs` allowlist to authorize gasless operations.

### Step 6: Test

```bash
# Verify on-chain (read-only, no gas needed)
cd scripts
npx tsx deploy-payment-operator.ts --fase5 --network <chain> --dry-run
# Should show "Existing operator found: 0x..."
```

For full E2E: create a $0.10 task with `payment_network=<chain>` and run through the lifecycle.

## Redeploy All Chains

If the fee structure changes (e.g., new BPS rate) or conditions change, redeploy ALL operators:

```bash
cd scripts

# Dry run all chains first
for chain in base ethereum polygon arbitrum avalanche monad celo optimism; do
  echo "=== $chain ==="
  npx tsx deploy-payment-operator.ts --fase5 --network $chain --dry-run
done

# Deploy (skip chains that already have the right config)
npx tsx deploy-payment-operator.ts --fase5 --network ethereum
npx tsx deploy-payment-operator.ts --fase5 --network polygon
npx tsx deploy-payment-operator.ts --fase5 --network arbitrum
npx tsx deploy-payment-operator.ts --fase5 --network avalanche
npx tsx deploy-payment-operator.ts --fase5 --network monad
npx tsx deploy-payment-operator.ts --fase5 --network celo
npx tsx deploy-payment-operator.ts --fase5 --network optimism
# Base usually doesn't need redeployment (it's our primary chain)
```

Then update `sdk_client.py` with all new addresses and register in Facilitator.

## Source of Truth for Addresses

| Source | What it contains |
|--------|-----------------|
| `@x402r/sdk` repo `packages/core/src/config/index.ts` | x402r sub-factory addresses per chain (BackTrack deploys these) |
| `mcp_server/integrations/x402/sdk_client.py` (`NETWORK_CONFIG`) | Our operator addresses + x402r infra per chain |
| `scripts/deploy-payment-operator.ts` (`CHAIN_CONFIGS`) | Same x402r infra addresses (must match sdk_client.py) |
| `CLAUDE.md` On-Chain Contracts table | Human-readable reference |

**If addresses seem wrong**, always verify against the x402r-sdk repo first:
```
https://github.com/BackTrackCo/x402r-sdk/blob/main/packages/core/src/config/index.ts
```

## Currently Deployed Operators (2026-02-18)

| Chain | Operator | Status |
|-------|----------|--------|
| Base | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` | Active |
| Polygon | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` | Deployed, pending Facilitator allowlist |
| Arbitrum | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | Deployed, pending Facilitator allowlist |
| Avalanche | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | Deployed, pending Facilitator allowlist |
| Monad | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` | Deployed, pending Facilitator allowlist |
| Ethereum | — | Pending (L1 RPC too slow, needs retry) |
| Celo | — | Blocked (0 CELO on deployer) |
| Optimism | — | Blocked (0 ETH on deployer) |

## Troubleshooting

### "MISSING" factory error
BackTrack hasn't deployed sub-factories on that chain. Contact Ali on IRC.

### "insufficient funds for gas"
Fund the deployer wallet (`0x857f...`) with native tokens on that chain.

### Slow L1 RPC (Ethereum)
The default `eth.llamarpc.com` can be very slow. Options:
- Use QuikNode: set `X402_RPC_URL` env var
- Edit `CHAIN_CONFIGS.ethereum.rpcUrl` in deploy script
- Retry — L1 RPCs are sometimes just slow

### Operator deployed but not working
- Check Facilitator allowlist — operator must be registered
- Check `sdk_client.py` — operator address must be in `NETWORK_CONFIG`
- Check escrow mode: `EM_ESCROW_MODE=direct_release` for Fase 5

### Wrong fee rate
Deploy a new operator with the correct BPS. Old operators remain on-chain but unused. Update `sdk_client.py` to point to the new one.
