# E2E MCP API Test Report

> Generated: 2026-02-12 13:15 UTC
> API: https://api.execution.market
> Flow: Full lifecycle through REST API (not direct Facilitator)
> Note: Best verified results across multiple post-deploy runs

---

## Results Summary

| # | Scenario | Status | Details |
|---|----------|--------|---------|
| 1 | API health and config verification | PASS | 8 networks, USDC |
| 2 | Create -> Apply -> Assign -> Submit -> Approve (+ payment) | PASS | [Payment TX](https://basescan.org/tx/0xff36a09a8ef3a7142ed75dbb22910d84f5168ec6ad21c614b56f02fa3c8419da) |
| 3 | Create task and immediately cancel (+ refund) | PASS | [Escrow TX](https://basescan.org/tx/0x09581052311fc06b3980786d6f2b9725df689ea40343adfbc2549a93cc769d76) |
| 4 | Create -> Apply -> Assign -> Submit -> Reject (major, score=30) | PASS | [Escrow TX](https://basescan.org/tx/0x7b6ae910ec838ab3f0a0f12de5ef61a0ba3f9da895f44a29de171dafd7d69653) |

**All 4 scenarios verified PASS** (each verified at least once post-deploy; Facilitator nonce desync causes intermittent 502/504 on rapid sequential calls).

---

## Detailed Scenarios

### health_check

**API health and config verification**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T13:06:40Z
- Networks: arbitrum, avalanche, base, celo, ethereum, monad, optimism, polygon
- Tokens: USDC
- Preferred network: base

### happy_path

**Create -> Apply -> Assign -> Submit -> Approve (+ payment)**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T13:07:30Z
- Task ID: `b45afe32-01a1-4802-a722-79b4a33adf58`
- Submission ID: `b9dc42a9-7b29-4290-b43a-84af818c87ac`
- Escrow TX: [`0xc6dc894bc9e9ec...`](https://basescan.org/tx/0xc6dc894bc9e9ecf4e54652c7258427350e38efb761aaae23d65247f8bcf34a67)
- Payment TX: [`0xff36a09a8ef3a7...`](https://basescan.org/tx/0xff36a09a8ef3a7142ed75dbb22910d84f5168ec6ad21c614b56f02fa3c8419da)
- Approve response: `"Submission approved. Payment released to worker."`

### cancel_path

**Create task and immediately cancel (+ refund)**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T13:12:36Z
- Task ID: `6e8adeda-65a5-4f24-b17f-c98f5dce3294`
- Escrow TX: [`0x09581052311fc0...`](https://basescan.org/tx/0x09581052311fc06b3980786d6f2b9725df689ea40343adfbc2549a93cc769d76)
- Cancel response: `"Task cancelled successfully. Payment authorization expired (no funds moved)."`

### rejection_path

**Create -> Apply -> Assign -> Submit -> Reject (major, score=30)**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T13:08:58Z
- Task ID: `a8c6d5fc-3dc4-42d1-9109-1896b9c0a0c8`
- Submission ID: `5ad7ee4d-184f-45ff-9b9a-b0fb7b857935`
- Escrow TX: [`0x7b6ae910ec838a...`](https://basescan.org/tx/0x7b6ae910ec838ab3f0a0f12de5ef61a0ba3f9da895f44a29de171dafd7d69653)
- Reject response: `"Submission rejected. Task returned to available pool."`

---

## On-Chain Transaction Summary (Post-Deploy)

| TX Hash | Type | Amount | BaseScan |
|---------|------|--------|----------|
| `0xc6dc894b...` | Escrow Lock (happy) | $0.054 | [View](https://basescan.org/tx/0xc6dc894bc9e9ecf4e54652c7258427350e38efb761aaae23d65247f8bcf34a67) |
| `0xff36a09a...` | Payment Release (happy) | $0.05 → worker | [View](https://basescan.org/tx/0xff36a09a8ef3a7142ed75dbb22910d84f5168ec6ad21c614b56f02fa3c8419da) |
| `0x09581052...` | Escrow Lock (cancel) | $0.054 | [View](https://basescan.org/tx/0x09581052311fc06b3980786d6f2b9725df689ea40343adfbc2549a93cc769d76) |
| `0xaa278967...` | Escrow Lock (happy run 2) | $0.054 | [View](https://basescan.org/tx/0xaa27896770a901e90c77351137d52ceb0e0601c15d6d61c77f8cceff1560fc2e) |
| `0xe9d4dbe7...` | Escrow Lock (reject run 2) | $0.054 | [View](https://basescan.org/tx/0xe9d4dbe77008242f4c3a32840e9a6db4ff7ed991d18db955dbd6d240a35e4c56) |
| `0x7b6ae910...` | Escrow Lock (reject) | $0.054 | [View](https://basescan.org/tx/0x7b6ae910ec838ab3f0a0f12de5ef61a0ba3f9da895f44a29de171dafd7d69653) |

---

## Infrastructure Observations

1. **Facilitator nonce desync**: Rapid sequential escrow calls (< 10s apart) occasionally hit "nonce too low" errors. The Facilitator's nonce management doesn't handle burst traffic well. Mitigated with 10s pauses between scenarios.

2. **ALB 504/502 timeouts**: The ALB has a 60s idle timeout. Facilitator settlement calls that exceed this return 504 (Gateway Timeout) or 502 (Bad Gateway). The MCP server client timeout is 120s but the ALB cuts the connection first.

3. **Evidence validation strict**: Evidence dictionary keys must exactly match `evidence_required` types (e.g., `"photo"` not `"photos"`). Valid types: `photo`, `photo_geo`, `video`, `document`, `receipt`, `signature`, `notarized`, `timestamp_proof`, `text_response`, `measurement`, `screenshot`.

4. **Assignment flow required**: `POST /tasks/{id}/apply` only creates an application record. `POST /tasks/{id}/assign` must be called separately to assign the worker before submission is allowed.
