# WALLET-BUG-ANALYSIS: Wrong Wallet Paying Escrow

**Date:** 2026-03-23  
**Severity:** Critical (production, real money)  
**Status:** Fixed (pending deployment)  
**Branch:** `fix/multi-wallet-escrow-payer`

---

## Summary

Production escrow payments were being signed by the **Platform Wallet** (`0xD386...5d474`) instead of the **Agent Wallet** (`0x52E0...5A15`). This caused:
1. The wrong wallet to fund on-chain escrow for task assignments
2. On-chain reputation to accrue to the platform entity instead of the agent
3. Incorrect fund flow (platform treasury paying agent task bounties)

## Root Cause

### The Bug

`PaymentDispatcher._get_fase2_client()` (line 439 of `payment_dispatcher.py`) hardcoded a single environment variable:

```python
pk = os.environ.get("WALLET_PRIVATE_KEY")
```

In the ECS production environment, `WALLET_PRIVATE_KEY` is set to the **Platform Wallet** private key (`0xD386...`). This is the wallet used for platform operations (fee distribution, escrow management, etc.).

When `authorize_escrow_for_worker()` was called during task assignment, it called `_get_fase2_client()` which always used `WALLET_PRIVATE_KEY` — the platform wallet. The `agent_address` parameter passed to the method was used only for **logging and metadata**, never for signing.

The `AdvancedEscrowClient` stores the private key as `self.private_key` and derives `self.payer = Account.from_key(private_key).address`. All on-chain operations (ERC-3009 `ReceiveWithAuthorization`, escrow authorize) sign with this key. So every escrow operation was signed by — and funded from — the platform wallet.

### Evidence (On-Chain)

| Date | TX Hash (prefix) | Task | Amount | Actual Payer | Expected Payer |
|------|-------------------|------|--------|-------------|----------------|
| Mar 22 | `0x3da3e0f1...` | Gas station task | $0.50 USDC | Platform (`0xD386...`) | Agent (`0x52E0...`) |
| Mar 23 | `0x7f22df29...` | Dispensary task | $0.25 USDC | Platform (`0xD386...`) | Agent (`0x52E0...`) |

### Why It Wasn't Caught Earlier

1. Both wallets were funded with USDC, so transactions succeeded
2. The `agent_address` parameter in logs showed the correct wallet — masking the actual signer
3. No wallet consistency validation existed at the API layer
4. The system was designed for a single-wallet setup initially; multi-wallet was added to the skill config but not the backend

## Fix Applied

### 1. Multi-Wallet Resolution (`payment_dispatcher.py`)

**New function: `_resolve_payer_wallet(payer_wallet=None)`**

Resolves which private key to use with clear priority:
1. `payer_wallet="platform"` → `WALLET_PRIVATE_KEY` (explicit platform wallet request)
2. `AGENT_WALLET_PRIVATE_KEY` env var set → use it (default for all escrow operations)
3. Fallback → `WALLET_PRIVATE_KEY` with a warning log (backward compatible)

**New function: `_get_agent_address()`**

Cached resolver for the agent wallet address from `AGENT_WALLET_PRIVATE_KEY`.

### 2. Multi-Wallet Client Cache (`_get_fase2_client`)

Cache key changed from `chain_id` to `(chain_id, wallet_label)`. Each wallet gets its own `AdvancedEscrowClient` instance, properly initialized with the correct private key.

```python
def _get_fase2_client(self, network="base", payer_wallet=None):
    pk, wallet_addr, wallet_label = _resolve_payer_wallet(payer_wallet)
    cache_key = (chain_id, wallet_label)
    ...
```

### 3. Wallet Label Persistence in Escrow Metadata

The `payer_wallet` label ("agent", "platform", "platform_fallback") is now stored in the serialized PaymentInfo metadata in the `escrows` table. This ensures that release/refund operations use the **same wallet** that authorized the escrow.

### 4. Release/Refund Path Updates

All 5 locations where `_get_fase2_client(stored_network)` was called after `_reconstruct_fase2_state()` now pass `payer_wallet=pi_meta.get("payer_wallet")` to ensure the correct wallet signs the release/refund.

### 5. API Guardrail (`tasks.py`)

- `WorkerAssignRequest` model now accepts an optional `payer_wallet` field (`"agent"` or `"platform"`)
- The assign endpoint resolves `payer_wallet` from: request body → task metadata → default (None = agent)
- Actual payer address is logged for audit trail after every escrow operation
- Default behavior: always agent wallet, platform wallet only on explicit request

### 6. Dashboard Cache Fix (`main.tsx`)

- `staleTime` reduced from 5 minutes to 30 seconds
- `refetchOnWindowFocus` enabled (was `false`)
- Prevents stale escrow_tx display when navigating between tasks

## Escrow TX Overlap (Non-Bug)

Saúl reported seeing the wrong `escrow_tx` when viewing a different task. Investigation confirmed:
- Each task has its own unique escrow record in the `escrows` table
- The API returns per-task escrow data correctly
- The overlap was caused by the **dashboard React Query cache** (5-min staleTime + no refetch on window focus)
- Fixed by reducing staleTime and enabling refetchOnWindowFocus

## Files Changed

| File | Change |
|------|--------|
| `mcp_server/integrations/x402/payment_dispatcher.py` | Multi-wallet resolution, client cache, metadata persistence |
| `mcp_server/api/routers/tasks.py` | Wallet pass-through, audit logging |
| `mcp_server/api/routers/_models.py` | `payer_wallet` field on `WorkerAssignRequest` |
| `dashboard/src/main.tsx` | Cache staleTime + refetchOnWindowFocus fix |

## Deployment Steps

### 1. ECS Environment Variables (REQUIRED)

Add this new env var to the `em-production-mcp-server` ECS task definition:

```
AGENT_WALLET_PRIVATE_KEY = <private key for 0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15>
```

The existing `WALLET_PRIVATE_KEY` (platform wallet `0xD386...`) stays unchanged — it's still used for:
- `distributeFees()` (flushing operator fees to treasury)
- Platform address derivation
- Fallback if `AGENT_WALLET_PRIVATE_KEY` is not set

### 2. Backend Deploy

```bash
cd ~/clawd/projects/execution-market
bash scripts/deploy-manual.sh
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server \
  --force-new-deployment --region us-east-2
aws ecs wait services-stable --cluster em-production-cluster --services em-production-mcp-server --region us-east-2
curl -s https://api.execution.market/health
```

### 3. Dashboard Deploy

```bash
cd ~/clawd/projects/execution-market/dashboard
npm run build
aws s3 sync dist/ s3://em-production-dashboard/ --delete \
  --cache-control 'public, max-age=31536000, immutable' \
  --exclude '*.html' --exclude '*.json' --exclude '*.md'
aws s3 cp dist/index.html s3://em-production-dashboard/index.html \
  --cache-control 'public, max-age=60' --content-type 'text/html'
aws cloudfront create-invalidation --distribution-id E2SD27QZ0GK40U --paths '/index.html' '/assets/*'
```

### 4. Post-Deploy Verification

```bash
# API health
curl -s https://api.execution.market/health

# Create a test task, assign a worker, verify the escrow TX payer on BaseScan
# The payer should be 0x52E05C8e... (agent), not 0xD3868... (platform)
```

## Backward Compatibility

- If `AGENT_WALLET_PRIVATE_KEY` is NOT set, the system falls back to `WALLET_PRIVATE_KEY` with a warning log
- Existing escrow records without `payer_wallet` metadata will use the default wallet (agent if env var is set, platform fallback otherwise)
- The `payer_wallet` API field is optional — omitting it uses the default agent wallet
- No database migrations needed

## Skill Config Changes

Added to `~/.openclaw/skills/execution-market/config.json`:

```json
{
  "default_payment_wallet": "primary",
  "allow_platform_wallet_override": true,
  "testing_wallet": "platform"
}
```

The skill should:
- Default to `"primary"` (agent wallet) for all task payments
- Only use `"platform"` wallet when operator explicitly requests testing mode
- Pass `payer_wallet: "platform"` in the assign API call when testing
