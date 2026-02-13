# E2E Full Lifecycle Report -- Fee Split Verification

> Generated: 2026-02-13 18:36 UTC
> API: `https://api.execution.market`
> Bounty: $0.10 USDC | Fee: $0.013000 (13%) | Total: $0.113000
> Worker: `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15`
> Treasury: `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad`

---

## Summary

| # | Scenario | Status | Key TX |
|---|----------|--------|--------|
| 1 | API health and config verification | PASS |  |
| 2 | Create -> Apply -> Assign -> Submit -> Approve (fee spl | PASS | [`0x2bdff37721...`](https://basescan.org/tx/0x2bdff37721b433d8d8fded04a021526f069ce7503f0f33026e79aa63cf19f884) |

---

## health_check

**API health and config verification**

- **Status**: SUCCESS
- **Timestamp**: 2026-02-13T18:35:06.493107+00:00
- **Payment mode**: `unknown`

## happy_path

**Create -> Apply -> Assign -> Submit -> Approve (fee split)**

- **Status**: SUCCESS
- **Timestamp**: 2026-02-13T18:36:25.458069+00:00
- **Task ID**: `852961c1-862d-4e95-88d8-348b89c37785`
- **Submission ID**: `101427c6-3646-45f8-80cd-57bd4b1ef0ac`
- **Payment mode**: `fase2`

| Step | TX Hash | Amount | BaseScan |
|------|---------|--------|----------|
| Escrow Lock | `0x21dc467c08d1be...` | $0.113000 | [View](https://basescan.org/tx/0x21dc467c08d1be2f7315970c99c98c39d4c5857b910d5fd04fc56205c4952d27) |
| Worker Disbursement | `0x2bdff37721b433...` | $0.10 | [View](https://basescan.org/tx/0x2bdff37721b433d8d8fded04a021526f069ce7503f0f33026e79aa63cf19f884) |
| Fee Collection | `0x60f00316ef97fe...` | $0.013000 | [View](https://basescan.org/tx/0x60f00316ef97fee149a344bc2eb6fc6bb1181d89a621e42b12398f4d5afb87ff) |

**Timing**: Create: 8.36s | Approve: 68.03s

---

## Invariants Verified

- [x] Worker TX and Fee TX are distinct on-chain transactions
