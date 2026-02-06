# Ship Report - PaymentTx Hardening + Prod Validation (2026-02-06)

## Summary
This release closes the critical gap where a submission could be marked accepted/completed without confirmed on-chain payout evidence.

## Code Changes
- `mcp_server/api/routes.py`
- `mcp_server/integrations/x402/sdk_client.py`
- `mcp_server/tests/test_p0_routes_idempotency.py`

### Behavior Changes
- `approve_submission` now blocks acceptance when settlement has no tx hash.
- Release payments are no longer treated as finalized by status-only (`confirmed`) without tx hash.
- Settlement tx extraction is robust to SDK response variants (`tx_hash`, `transaction_hash`, `transaction`, nested fields).

## Tests Run
- `python -m pytest -q mcp_server/tests/test_p0_routes_idempotency.py` -> PASS (17)
- `python -m pytest -q mcp_server/tests/test_task_expiration_job.py` -> PASS (3)

## Deployment
- Target cluster/service: `em-production-cluster` / `em-production-mcp-server`
- New image: `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:ship-20260206-0036-275d829`
- New task definition: `em-production-mcp-server:20`
- Rollout: `COMPLETED`

## Live Validation Commands + Evidence
1) Deposit state
- Command: `cd scripts && npm exec -- tsx check-deposit-state.ts`
- Wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
- Result: wallet USDC `8.827674`

2) Rapid full flow (strict, no fallback)
- Command: `cd scripts && npm exec -- tsx test-x402-rapid-flow.ts -- --count 1 --deadline 2 --auto-approve --run-refund-check --strict true --allow-supabase-fallback false`
- Task ID: `4a5549de-5cd3-4b38-b800-25e69a0e09e6`
- Submission ID: `590d90fa-ca41-477d-91b3-e0d292f33652`
- Payment tx: `0x0e5295b9075dc28d92a3b349f5df13ee586c8eeee4465a5f249a797bfefef41e`
- BaseScan: `https://basescan.org/tx/0x0e5295b9075dc28d92a3b349f5df13ee586c8eeee4465a5f249a797bfefef41e`
- Final task status: `completed`
- Assignment mode: `api`
- Fallback paths used: none

3) Payment timeline endpoint verification
- Endpoint: `GET /api/v1/tasks/4a5549de-5cd3-4b38-b800-25e69a0e09e6/payment`
- Event includes: `type=final_release`, tx hash matches submission `payment_tx`

4) Refund path sanity
- Task ID: `94e2ac34-27a7-4aae-a430-2663bd4d524c`
- Cancel response: `authorization_expired`
- Interpretation: authorize-only path; no escrow-settled funds, so no on-chain refund tx expected.

## Known Remaining Gap
- Need at least one live run with **escrow-funded** refund path to capture real refund tx hash evidence (not authorization expiry).
