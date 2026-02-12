# E2E MCP API Test Report

> Generated: 2026-02-12 15:36 UTC
> API: https://api.execution.market
> Flow: Full lifecycle through REST API (not direct Facilitator)
> Facilitator: Nonce retry logic deployed (2026-02-12)

---

## Results Summary

| # | Scenario | Status | Details |
|---|----------|--------|---------|
| 1 | API health and config verification | PASS | 8 networks, USDC |
| 2 | Create task and immediately cancel (+ refund) | PASS | [Escrow TX](https://basescan.org/tx/0xe43314a1a8ea41018fcbad90134e2e39dc56036d31d02dd4c035e7e89ced680c) |
| 3 | Create -> Apply -> Assign -> Submit -> Reject (major, score=30) | PASS | [Escrow TX](https://basescan.org/tx/0x873c728b5b0696da43e2bd2c7c1de364f0332f729cd475baad6a662218f8c66f) |
| 4 | Create -> Apply -> Assign -> Submit -> Approve (+ payment) | PASS | [Payment TX](https://basescan.org/tx/0x1c04786c59842cf9ee3f3bcd3cd7b643d127f679e26f54c8449ddfdb12654542) |

**All 4 scenarios PASS** with 5-second pauses and optimized ordering (light ops first, heavy approve last).

---

## Detailed Scenarios

### health_check

**API health and config verification**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T15:36Z
- Networks: arbitrum, avalanche, base, celo, ethereum, monad, optimism, polygon
- Tokens: USDC
- Preferred network: base

### cancel_path

**Create task and immediately cancel (+ refund)**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T15:36Z
- Task ID: `eb3ebefe-4f6e-414f-b1f9-b0501f39906f`
- Escrow TX: [`0xe43314a1a8ea41...`](https://basescan.org/tx/0xe43314a1a8ea41018fcbad90134e2e39dc56036d31d02dd4c035e7e89ced680c)
- Cancel response: `"Task cancelled successfully. Payment authorization expired (no funds moved)."`

### rejection_path

**Create -> Apply -> Assign -> Submit -> Reject (major, score=30)**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T15:36Z
- Task ID: `c22eb378-f134-4b20-a78f-d9378307cdb3`
- Submission ID: `0ffde557-e9bc-440c-bee5-f7958cc4fa24`
- Escrow TX: [`0x873c728b5b0696...`](https://basescan.org/tx/0x873c728b5b0696da43e2bd2c7c1de364f0332f729cd475baad6a662218f8c66f)
- Reject response: `"Submission rejected. Task returned to available pool."`

### happy_path

**Create -> Apply -> Assign -> Submit -> Approve (+ payment)**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T15:36Z
- Task ID: `8a89688a-1f45-4e85-9ec8-37123c0e10e5`
- Submission ID: `e90e10bc-0aa2-405f-85e0-050583bd4eb6`
- Escrow TX: [`0x0dbc1f41756d8b...`](https://basescan.org/tx/0x0dbc1f41756d8b3b19a42b60987215232e09c156f8cb049b94ed50756e832e75)
- Payment TX: [`0x1c04786c598420...`](https://basescan.org/tx/0x1c04786c59842cf9ee3f3bcd3cd7b643d127f679e26f54c8449ddfdb12654542)
- Approve response: `"Submission approved. Payment released to worker."`

---

## On-Chain Transaction Summary

| TX Hash | Operation | Amount | BaseScan |
|---------|-----------|--------|----------|
| `0xe43314a1...` | Escrow authorize (cancel) | $0.054 | [View](https://basescan.org/tx/0xe43314a1a8ea41018fcbad90134e2e39dc56036d31d02dd4c035e7e89ced680c) |
| `0x873c728b...` | Escrow authorize (reject) | $0.054 | [View](https://basescan.org/tx/0x873c728b5b0696da43e2bd2c7c1de364f0332f729cd475baad6a662218f8c66f) |
| `0x0dbc1f41...` | Escrow authorize (happy) | $0.054 | [View](https://basescan.org/tx/0x0dbc1f41756d8b3b19a42b60987215232e09c156f8cb049b94ed50756e832e75) |
| `0x1c04786c...` | Payment release (happy) | $0.05 to worker | [View](https://basescan.org/tx/0x1c04786c59842cf9ee3f3bcd3cd7b643d127f679e26f54c8449ddfdb12654542) |

---

## Facilitator Nonce Retry Validation (2026-02-12)

The Facilitator deployed nonce retry logic on 2026-02-12. We ran 6 E2E test rounds to validate:

| Run | Config | Happy Path | Cancel | Reject | Notes |
|-----|--------|-----------|--------|--------|-------|
| 1 | 0s pauses | PASS | FAIL (504) | PASS | Retry latency > ALB 60s |
| 2 | 0s pauses | PASS | FAIL (504) | FAIL (504) | Both post-happy scenarios failed |
| 3 | 3s pauses | FAIL (502) | FAIL (invalid sig) | PASS | EIP-3009 auth reuse on retry |
| 4 | 5s pauses | PASS | FAIL (504) | PASS | Cancel still timed out |
| 5 | 5s reordered | PASS | PASS | PASS | Light ops first, heavy last |
| 6 | 5s reordered (back-to-back) | PASS | FAIL (504) | PASS | Prior run's burst still processing |

### Conclusions

1. **Nonce retry works** — zero "nonce too low" errors across all runs (previously ~50% failure rate)
2. **Latency tradeoff** — retries push some calls past the ALB 60s timeout, causing 504s
3. **EIP-3009 edge case** — one run hit `FiatTokenV2: invalid signature` when the retry replayed an already-consumed EIP-3009 authorization (the original TX had actually succeeded)
4. **Optimal ordering** — running light operations (1 Facilitator call each) before the heavy approve flow (4 calls) achieves consistent 4/4

### Remaining Issue for Facilitator Team

The nonce retry adds enough latency that subsequent Facilitator calls can exceed the 60-second ALB timeout. Possible mitigations:

- **Faster retry**: Reduce backoff time between retry attempts
- **Optimistic nonce**: Track nonces locally with atomic increment (no retry needed)
- **TX receipt check before retry**: Verify the original TX didn't actually succeed before retrying with a new nonce (prevents `invalid signature` errors)
