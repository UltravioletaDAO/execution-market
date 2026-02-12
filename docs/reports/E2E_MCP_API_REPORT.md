# E2E MCP API Test Report

> Generated: 2026-02-12 17:44 UTC
> API: https://api.execution.market
> Flow: Full lifecycle through REST API (not direct Facilitator)

---

## Results Summary

| # | Scenario | Status | Details |
|---|----------|--------|---------|
| 1 | API health and config verification | PASS |  |
| 2 | Cancel flow test | FAIL | Task creation failed: HTTP 402 - Escrow lock failed: Escrow authorize failed: Es |
| 3 | Create -> Apply -> Assign -> Submit -> Reject (major, score= | PASS | [Escrow TX](https://basescan.org/tx/0xe326c60b786d05ab66cc70d42f2f95f281625470dfa60b55bd11a31a02af9fe6) |
| 4 | Full lifecycle test | FAIL | Task creation failed: HTTP 402 - Escrow lock failed: Escrow authorize failed: Es |

---

## Detailed Scenarios

### health_check

**API health and config verification**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T17:42:19.735656+00:00
- Networks: ['arbitrum', 'avalanche', 'base', 'celo', 'ethereum', 'monad', 'optimism', 'polygon']
- Tokens: ['USDC']

### cancel_path

**Cancel flow test**

- Status: **FAILED**
- Timestamp: 2026-02-12T17:43:51.399092+00:00
- Error: Task creation failed: HTTP 402 - Escrow lock failed: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("TxWatcher(Timeout)"). Task cancelled.

### rejection_path

**Create -> Apply -> Assign -> Submit -> Reject (major, score=30)**

- Status: **SUCCESS**
- Timestamp: 2026-02-12T17:44:01.079342+00:00
- Task ID: `928604f1-8390-4e8e-8149-2b93cf21eddd`
- Submission ID: `a7a4cafe-91c0-4022-aca6-770506c8cadb`
- Escrow TX: [`0xe326c60b786d05...`](https://basescan.org/tx/0xe326c60b786d05ab66cc70d42f2f95f281625470dfa60b55bd11a31a02af9fe6)

### happy_path

**Full lifecycle test**

- Status: **FAILED**
- Timestamp: 2026-02-12T17:44:07.608866+00:00
- Error: Task creation failed: HTTP 402 - Escrow lock failed: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("ErrorResp(ErrorPayload { code: 3, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"). Task cancelled.
