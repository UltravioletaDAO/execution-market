# Fase 3 E2E Escrow Test Evidence — 2026-02-13

## Executive Summary

**All Fase 3 escrow operations succeeded on Base Mainnet.** Both the happy path (authorize → release) and the refund path (authorize → refund) completed successfully using the Fase 3 PaymentOperator with OR(Payer|Facilitator) conditions and 1% on-chain fee.

| Scenario | Status |
|----------|--------|
| Dry Run (config validation) | ✅ PASS |
| Happy Path (authorize + release) | ✅ PASS |
| Refund Path (authorize + refund) | ✅ PASS |
| On-chain fee verification (1% = 100bps) | ✅ PASS |
| OR(Payer) release condition | ✅ PASS |
| OR(Payer) refund condition | ✅ PASS |
| Gasless authorize via facilitator | ✅ PASS |
| Escrow state query | ⚠️ FAIL (ABI mismatch — non-critical) |
| Identity Registry check | ⚠️ FAIL (contract not yet active) |
| Reputation Registry check | ⚠️ FAIL (contract not yet active) |
| MCP integration (Fase 3 via fase2 mode) | ⚠️ BLOCKED (Python SDK missing `advanced_escrow` module) |

---

## Configuration

| Parameter | Value |
|-----------|-------|
| **Chain** | Base Mainnet (8453) |
| **Fase 3 Operator** | `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6` |
| **Protocol Escrow** | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| **TokenCollector** | `0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8` |
| **USDC** | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| **Payer (Dev Wallet)** | `0xD3868E1eD738CED6945A574a7c769433BeD5d474` |
| **Receiver (EM Treasury)** | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` |
| **Facilitator** | `https://facilitator.ultravioletadao.xyz` |
| **Facilitator TX Sender** | `0x103040545AC5031A11E8C03dd11324C7333a13C7` |
| **Escrow Proxy** | `0x36bed84c57ec5046ca7e7011a16dca0201b353a2` |
| **Test Amount** | $0.002 USDC (2000 atomic units) |
| **Task Tier** | micro (pre: 1h, auth: 2h, refund: 24h) |
| **maxFeeBps** | 800 (8% max, operator takes 1%) |
| **SDK** | uvd-x402-sdk v2.22.0 (TypeScript) |
| **Test Script** | `scripts/test-fase3-escrow.ts` |

---

## Test 1: Happy Path (RELEASE)

### Step 1: AUTHORIZE

- **PaymentInfo:**
  - operator: `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6`
  - salt: `0x2e56684da27e91d8...`
  - preApprovalExpiry: 2026-02-13T05:47:28Z
  - authorizationExpiry: 2026-02-13T06:47:28Z
  - maxFeeBps: 800

- **TX:** [`0x5f53898e5fa88a80df59397d16cdd4986993c14e2562f8a9e36a6e030304136e`](https://basescan.org/tx/0x5f53898e5fa88a80df59397d16cdd4986993c14e2562f8a9e36a6e030304136e)
- **Block:** 42084352 (0x2822800)
- **Gas Used:** 218,236
- **From:** `0x103040545AC5031A11E8C03dd11324C7333a13C7` (facilitator — gasless for payer)
- **To:** `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6` (Fase 3 operator)
- **Duration:** 7.54s
- **Status:** ✅ SUCCESS

**On-chain events:**
1. `Authorized` event on operator (nonce `0xc01e94be...`)
2. `Authorized` event on escrow contract
3. `AuthorizationUsed` on USDC (ERC-3009)
4. USDC Transfer: Payer → TokenCollector (2000 units)
5. USDC Transfer: TokenCollector → Escrow Proxy (2000 units)

### Step 2: ESCROW STATE QUERY

- **Result:** ⚠️ FAILED — `execution reverted (require(false))`
- **Cause:** The `getEscrowState(operator, token, payer, nonce)` function signature may not match the actual contract ABI. The escrow contract may use a different query interface.
- **Impact:** Non-critical. The authorize and release operations themselves work correctly.

### Step 3: RELEASE

- **TX:** [`0x06e85fb2bcf28ab2606fed13073bf4e98c5cc1b471c2c43ad109099fea22ae54`](https://basescan.org/tx/0x06e85fb2bcf28ab2606fed13073bf4e98c5cc1b471c2c43ad109099fea22ae54)
- **Block:** 42084358 (0x2822806)
- **Gas Used:** 108,497
- **From:** `0xD3868E1eD738CED6945A574a7c769433BeD5d474` (payer — OR(Payer) condition!)
- **To:** `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6` (Fase 3 operator)
- **Duration:** 0.58s
- **Status:** ✅ SUCCESS

**On-chain fee breakdown:**

| Recipient | Amount (units) | Amount (USDC) | % |
|-----------|---------------|---------------|---|
| Operator (fee) | 20 | $0.000020 | 1.0% |
| Receiver (worker) | 1,980 | $0.001980 | 99.0% |
| **Total** | **2,000** | **$0.002000** | **100.0%** |

**USDC Transfer events:**
1. Escrow Proxy (`0x36bed8...`) → Operator (`0x8D3DeC...`): 20 units (1% fee)
2. Escrow Proxy (`0x36bed8...`) → Receiver (`0xae07ce...`): 1,980 units (99% to worker)

### Step 4: FINAL STATE

- **USDC Before:** 21.237987
- **USDC After:** 21.235987
- **Delta:** -0.002000 USDC ✅ (exact test amount)

---

## Test 2: Refund Path

### Step 1: AUTHORIZE

- **PaymentInfo:**
  - operator: `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6`
  - salt: `0x40b594eff3662b78...`
  - preApprovalExpiry: 2026-02-13T05:47:55Z
  - authorizationExpiry: 2026-02-13T06:47:55Z

- **TX:** [`0x3b1173c6a1ccb3178202bc707e18bedbd76fb667161f914618a7f68a932288f2`](https://basescan.org/tx/0x3b1173c6a1ccb3178202bc707e18bedbd76fb667161f914618a7f68a932288f2)
- **Block:** 42084365 (0x282280d)
- **Gas Used:** 218,268
- **From:** `0x103040545AC5031A11E8C03dd11324C7333a13C7` (facilitator — gasless)
- **Duration:** 7.37s
- **Status:** ✅ SUCCESS

### Step 2: REFUND IN ESCROW

- **TX:** [`0xb7709f8339aa90ddf8dc327aa4b20a50ecf322d974ff0003bc55a6dc903c3725`](https://basescan.org/tx/0xb7709f8339aa90ddf8dc327aa4b20a50ecf322d974ff0003bc55a6dc903c3725)
- **Block:** 42084372 (0x2822814)
- **Gas Used:** 87,370
- **From:** `0xD3868E1eD738CED6945A574a7c769433BeD5d474` (payer — OR(Payer) condition!)
- **Duration:** 4.77s
- **Status:** ✅ SUCCESS

**On-chain refund transfer:**

| From | To | Amount (units) | Amount (USDC) |
|------|-----|---------------|---------------|
| Escrow Proxy (`0x36bed8...`) | Payer (`0xD3868E...`) | 2,000 | $0.002000 |

**No fees deducted on refund — full amount returned to payer.** ✅

### Step 3: FINAL STATE

- **USDC Before:** 21.235987
- **USDC After:** 21.235987
- **Delta:** $0.000000 (fully refunded) ✅

---

## Transaction Summary

| # | Operation | TX Hash | Status | Gas |
|---|-----------|---------|--------|-----|
| 1 | Authorize (release path) | [`0x5f53898e...`](https://basescan.org/tx/0x5f53898e5fa88a80df59397d16cdd4986993c14e2562f8a9e36a6e030304136e) | ✅ Success | 218,236 |
| 2 | Release to worker | [`0x06e85fb2...`](https://basescan.org/tx/0x06e85fb2bcf28ab2606fed13073bf4e98c5cc1b471c2c43ad109099fea22ae54) | ✅ Success | 108,497 |
| 3 | Authorize (refund path) | [`0x3b1173c6...`](https://basescan.org/tx/0x3b1173c6a1ccb3178202bc707e18bedbd76fb667161f914618a7f68a932288f2) | ✅ Success | 218,268 |
| 4 | Refund to payer | [`0xb7709f83...`](https://basescan.org/tx/0xb7709f8339aa90ddf8dc327aa4b20a50ecf322d974ff0003bc55a6dc903c3725) | ✅ Success | 87,370 |

**Total gas used:** 632,371  
**Total USDC spent (net):** $0.002000 (release test) + $0.000000 (refund test) = **$0.002000**

---

## Registry Checks

### Identity Registry (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`)

- **Status:** ⚠️ Query failed — `execution reverted (require(false))`
- **Interpretation:** Contract may not be deployed or may have a different ABI (not standard ERC-721). The address may be reserved but the Identity Registry is not yet live.

### Reputation Registry (`0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`)

- **Status:** ⚠️ Query failed — `execution reverted (require(false))`
- **Interpretation:** Same as Identity Registry — contract may not be deployed/active yet.

---

## Key Findings

### ✅ What Works

1. **Fase 3 Operator deploys correctly** — The `0x8D3DeC...` operator handles authorize, release, and refund.
2. **OR(Payer) condition works** — The payer (dev wallet) can call `release()` and `refundInEscrow()` directly on-chain without needing the facilitator. This is the key Fase 3 improvement over Fase 2.
3. **1% on-chain fee** — The StaticFeeCalculator correctly takes 1% (100bps) on release. Fee goes to the operator address. On refund, no fee is charged.
4. **Gasless authorize** — The facilitator sends the authorize TX (payer signs ERC-3009, facilitator pays gas).
5. **Full refund integrity** — Refund returns 100% of locked funds to the payer with no fee deduction.

### ⚠️ Known Issues

1. **Escrow state query fails** — The `getEscrowState(operator, token, payer, nonce)` call reverts. The ABI used may not match the actual contract. The SDK doesn't expose a query method for escrow state.
2. **Python SDK missing `advanced_escrow` module** — The `uvd_x402_sdk` Python package doesn't have the `AdvancedEscrowClient` class. Only the TypeScript SDK has it. This blocks the MCP server's `fase2` payment mode.
3. **Identity/Reputation registries not active** — The contracts at `0x8004A1...` and `0x8004BA...` don't respond to standard ERC-721/ERC-20 queries.

### 💡 Fee Structure Clarification

The task description mentioned "1% x402r protocol + 12% EM treasury + 87% worker" but on-chain we see:
- **1% → Operator** (on-chain fee via StaticFeeCalculator)
- **99% → Receiver** (designated worker/treasury address)

The 12% EM treasury split would need to happen at the **application layer** (in the MCP server's PaymentDispatcher), not on-chain. The on-chain contract only knows about the 1% operator fee.

---

## MCP Integration Analysis

### Current State

The `PaymentDispatcher` in `mcp_server/integrations/x402/payment_dispatcher.py` supports 4 modes:
- **fase1** (default): Balance check only, 2 direct EIP-3009 settlements at approval
- **fase2**: On-chain escrow via AdvancedEscrowClient + gasless facilitator
- **preauth**: EIP-3009 pre-authorization
- **x402r**: Legacy on-chain escrow via EMAdvancedEscrow

### Fase 3 Integration Status

- The Fase 3 operator address (`0x8D3DeC...`) is **already the default** in the code:
  ```python
  EM_OPERATOR = os.environ.get("EM_PAYMENT_OPERATOR", "0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6")
  ```
- However, `fase2` mode requires `from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient` which **doesn't exist in the Python SDK**.
- When `FASE2_SDK_AVAILABLE` is `False`, the dispatcher falls back to `fase1` mode.
- **To enable Fase 3 via MCP:** Either port the TypeScript `AdvancedEscrowClient` to Python, or create a thin Python wrapper that calls the TypeScript SDK via subprocess/Node bridge.

---

## Test Artifacts

- **Test script:** `scripts/test-fase3-escrow.ts`
- **SDK:** `uvd-x402-sdk` v2.22.0 (TypeScript, via npm)
- **Test date:** 2026-02-13 ~00:47 EST
- **Executed by:** UltraClawd (automated E2E test)

---

## Conclusion

Fase 3 trustless escrow is **fully operational** on Base Mainnet. The OR(Payer|Facilitator) condition works as designed, allowing the payer to release or refund without needing facilitator involvement for those operations (only authorize is gasless via facilitator). The 1% on-chain fee is correctly applied on release and correctly waived on refund.

The main remaining work is:
1. Port `AdvancedEscrowClient` to the Python SDK to enable MCP server integration
2. Investigate the escrow state query ABI mismatch
3. Deploy/activate Identity and Reputation registries
