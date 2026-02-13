# E2E Full Lifecycle Test — Fee Split Verification

Run the complete production lifecycle test through the MCP Server REST API. This is the "test of all tests" — it proves that the full payment pipeline works end-to-end with on-chain evidence of the fee split between Worker and Treasury.

Use when the user says "e2e full lifecycle", "test full lifecycle", "fee split test", "full e2e", "test final", "complete flow test", or wants to verify that payments work correctly through the production API.

## What It Tests

### Scenario 1: Happy Path (Create → Apply → Assign → Submit → Approve → 3 TXs)

The core test. Verifies:

1. **TX 1 — Escrow Authorize**: Lock `bounty * 1.13` in on-chain escrow (Fase 2) or balance check (Fase 1)
2. **TX 2 — Worker Disbursement**: `$bounty` USDC → Worker wallet (`0x52E0...5A15`)
3. **TX 3 — Fee Collection**: `$bounty * 0.13` USDC → Treasury (`0xae07...`)

All 3 TXs are independently verifiable on BaseScan.

### Scenario 2: Cancel Path (Create → Cancel → Refund)

Verifies that cancellation returns 100% of locked funds to the agent.

### Scenario 3: Rejection Path (Create → Apply → Assign → Submit → Reject)

Verifies that rejected submissions do NOT trigger any payment. Funds remain in escrow for the next worker attempt or cancellation.

## Prerequisites

- Production MCP Server running with `EM_PAYMENT_MODE=fase2` (or `fase1`)
- `EM_PAYMENT_OPERATOR` set to the clean Fase 3 operator
- Test Worker wallet registered in Supabase (`0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15`)
- Agent wallet funded with USDC on Base (at least $0.50)

## Running the Test

```bash
# Default: run against production
python scripts/e2e_full_lifecycle.py

# Against local dev server
EM_API_URL=http://localhost:8000 python scripts/e2e_full_lifecycle.py

# Dry run (show config, don't transact)
python scripts/e2e_full_lifecycle.py --dry-run

# Only happy path (skip cancel/rejection)
python scripts/e2e_full_lifecycle.py --happy-only

# Custom bounty amount
python scripts/e2e_full_lifecycle.py --bounty 0.05
```

## Output

The script generates:
- **Console output**: Real-time progress with TX hashes and BaseScan links
- **Markdown report**: `docs/reports/E2E_FULL_LIFECYCLE_REPORT.md` — structured evidence
- **JSON data**: `docs/reports/E2E_FULL_LIFECYCLE_REPORT.json` — machine-readable results

## Key Addresses

| Role | Address | Source |
|------|---------|--------|
| Agent (production) | `0xD386...` | ECS `WALLET_PRIVATE_KEY` |
| Agent (dev) | `0x857f...` | `.env.local` |
| Worker (test) | `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` | AWS `em/test-worker` |
| Treasury | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` | Ledger cold wallet |
| PaymentOperator | `0xd5149049e7c212ce5436a9581b4307EB9595df95` | Fase 3 clean |

## Fee Math

For a `$0.10` bounty with `EM_PLATFORM_FEE=0.13`:

| Step | Amount | Destination |
|------|--------|-------------|
| Escrow lock | $0.113 | On-chain escrow |
| Worker disbursement | $0.10 | Worker wallet |
| Fee collection | $0.013 | Treasury |
| x402r on-chain fee | $0.00 | (feeCalculator=address(0)) |

## After Running

Use the generated report as evidence for the Complete Flow Report. The report includes:
- All TX hashes with BaseScan links
- Fee split verification (amounts match expected percentages)
- Timing data for each operation
- Comparison between expected and actual values
