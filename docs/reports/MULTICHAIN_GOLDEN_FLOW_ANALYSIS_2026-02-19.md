# Multichain Golden Flow Analysis — 2026-02-19

> **Date**: 2026-02-19 17:50 UTC
> **Script**: `scripts/e2e_golden_flow_multichain.py`
> **Cost**: $0.40 USDC consumed (4 chains completed, 3 failed before escrow)
> **Result**: **4/7 PASS, 3/7 FAIL** (2 distinct root causes)

---

## Executive Summary

The first-ever Multichain Golden Flow tested the complete Execution Market lifecycle
(task creation -> escrow lock -> payment release -> on-chain verification) across all
7 chains with deployed Fase 5 PaymentOperators.

**4 chains passed perfectly** with verified on-chain transactions and correct fee math.
**3 chains failed** due to 2 distinct bugs, both in the `uvd-x402-sdk`:

| Bug | Chains | Root Cause | Fix Location |
|-----|--------|------------|--------------|
| BUG-1 | Monad, Celo | EIP-712 domain separator hardcoded as "USD Coin" v2, but USDC on Monad/Celo uses "USDC" as name | `uvd-x402-sdk` `advanced_escrow.py:550-552` |
| BUG-2 | Optimism | Chain ID 10 missing from SDK's `ESCROW_CONTRACTS` registry, falls back to legacy Base operator `0xa069...` | `uvd-x402-sdk` `advanced_escrow.py` ESCROW_CONTRACTS dict |

---

## Chains That Passed (4/7)

### Base (chain 8453) — PASS

| Metric | Value |
|--------|-------|
| Operator | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` |
| Escrow Lock TX | [`0xd4e030...`](https://basescan.org/tx/0xd4e0300d025eb1ecd86f82e7ba20839f22d72d0054b24a5e7e0e166002dba2e9) |
| Release TX | [`0xd2bab2...`](https://basescan.org/tx/0xd2bab27cf0b1ce698b852be913d528391f067890eb90ba823e73314508a3d0ca) |
| Worker Net | $0.087000 (87%) |
| Operator Fee | $0.013000 (13%) |
| Fee Math | CORRECT |
| Time | 37.95s |

### Polygon (chain 137) — PASS

| Metric | Value |
|--------|-------|
| Operator | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` |
| Escrow Lock TX | [`0x781e08...`](https://polygonscan.com/tx/0x781e08f4b2ab1130416cb8ac2a1d8c9a4df338923d2ea2e1bb437ec87539a192) |
| Release TX | [`0xb93190...`](https://polygonscan.com/tx/0xb93190a576ad429b1a3051697e05cbfb4cbcb4e4c075b4f7b3acb2bdb7c36532) |
| Worker Net | $0.087000 (87%) |
| Operator Fee | $0.013000 (13%) |
| Fee Math | CORRECT |
| Time | 50.14s |

### Arbitrum (chain 42161) — PASS

| Metric | Value |
|--------|-------|
| Operator | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Escrow Lock TX | [`0xfb471b...`](https://arbiscan.io/tx/0xfb471b4d807faa08d2c8c71feb5cad619b9b85798c827d13ab9d7083904e3e3c) |
| Release TX | [`0xeb7557...`](https://arbiscan.io/tx/0xeb7557d811f390c24a49567571779915dfe6e3ded5cabea5460e6d7424ccf52d) |
| Worker Net | $0.087000 (87%) |
| Operator Fee | $0.013000 (13%) |
| Fee Math | CORRECT |
| Time | 50.47s |

### Avalanche (chain 43114) — PASS

| Metric | Value |
|--------|-------|
| Operator | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Escrow Lock TX | [`0xfae22b...`](https://snowtrace.io/tx/0xfae22be2707484bc1216fc7dcd97e4a05dc0de957cfcc3d91449827e54214b46) |
| Release TX | [`0x07a4e9...`](https://snowtrace.io/tx/0x07a4e92d8f06f18a79f9f5bbee7843d57d92f22e3b451605a38751ef91066550) |
| Worker Net | $0.087000 (87%) |
| Operator Fee | $0.013000 (13%) |
| Fee Math | CORRECT |
| Time | 43.95s |

---

## Chains That Failed (3/7)

### BUG-1: Monad + Celo — "FiatTokenV2: invalid signature"

**Symptom**: EIP-3009 `ReceiveWithAuthorization` reverts with "FiatTokenV2: invalid signature" during escrow lock (task assignment step).

**Root Cause**: The `uvd-x402-sdk` (`advanced_escrow.py`, line 550-552) **hardcodes** the EIP-712 domain separator:

```python
domain = {
    "name": "USD Coin",   # <-- HARDCODED
    "version": "2",        # <-- HARDCODED
    "chainId": self.chain_id,
    "verifyingContract": ...,
}
```

But Monad and Celo USDC contracts use different values for `name()`:

| Chain | On-chain `name()` | On-chain `version()` | SDK assumes | Match? |
|-------|-------------------|---------------------|-------------|--------|
| Base | "USD Coin" | "2" | "USD Coin" / "2" | YES |
| Polygon | "USD Coin" | "2" | "USD Coin" / "2" | YES |
| Arbitrum | "USD Coin" | "2" | "USD Coin" / "2" | YES |
| Avalanche | "USD Coin" | "2" | "USD Coin" / "2" | YES |
| Optimism | "USD Coin" | "2" | "USD Coin" / "2" | YES |
| **Monad** | **"USDC"** | **"2"** | "USD Coin" / "2" | **NO** |
| **Celo** | **"USDC"** | **"2"** | "USD Coin" / "2" | **NO** |

The EIP-712 domain separator is computed from `name + version + chainId + verifyingContract`. If `name` doesn't match, the signature computed off-chain differs from what the USDC contract expects on-chain, causing "invalid signature".

**Fix Required**: `uvd-x402-sdk` should either:
1. Read `name()` and `version()` from the USDC contract on-chain before signing (best), or
2. Accept `token_name` and `token_version` parameters in the constructor (acceptable), or
3. Maintain a per-chain lookup table for USDC domain parameters (fragile)

**Responsibility**: BackTrack (x402r-SDK maintainers). This is a bug in `uvd-x402-sdk`.

**Workaround**: Until fixed, we could monkey-patch `_sign_erc3009()` to use correct values from our NETWORK_CONFIG. Not recommended for production.

---

### BUG-2: Optimism — "operator address mismatch"

**Symptom**: Facilitator rejects the authorize request: `operator address mismatch: client=0xa06958d93135bed7e43893897c0d9fa931ef051c, allowed=[0xc2377a9db1de2520bd6b2756ed012f4e82f7938e]`.

**Root Cause**: Chain ID 10 (Optimism) is **missing** from the SDK's `ESCROW_CONTRACTS` registry. The `AdvancedEscrowClient.__init__` has this fallback logic:

```python
if chain_id in ESCROW_CONTRACTS:
    # Resolve from registry
    ...
else:
    # Fall back to legacy Base Mainnet default
    self.contracts = BASE_MAINNET_CONTRACTS
```

`BASE_MAINNET_CONTRACTS` contains a **legacy operator**: `0xa06958D93135BEd7e43893897C0d9fA931EF051C` (not our Fase 5 operator). Even though our code passes `operator_address="0xC2377..."` to the constructor, the SDK **ignores** it when falling back to `BASE_MAINNET_CONTRACTS` (the explicit contracts dict path is used instead).

**SDK Chain Registry Status**:

| Chain | Chain ID | In `ESCROW_CONTRACTS`? | Result |
|-------|----------|----------------------|--------|
| Base | 8453 | YES | Uses registry + our operator |
| Polygon | 137 | YES | Uses registry + our operator |
| Arbitrum | 42161 | YES | Uses registry + our operator |
| Avalanche | 43114 | YES | Uses registry + our operator |
| Monad | 143 | YES | Uses registry + our operator (but signature fails) |
| Celo | 42220 | YES | Uses registry + our operator (but signature fails) |
| **Optimism** | **10** | **NO** | Falls back to BASE_MAINNET legacy |

**Fix Required**: `uvd-x402-sdk` needs to add Optimism (chain 10) to `ESCROW_CONTRACTS`:
```python
10: {
    "escrow": "0x320a3c35F131E5D2Fb36af56345726B298936037",
    "operator_factory": "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
    "token_collector": "0x230fd3A171750FA45db2976121376b7F47Cba308",
    "protocol_fee_config": "0xD979dBfBdA5f4b16AAF60Eaab32A44f352076838",
    "refund_request": "...",
    "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
}
```

**Responsibility**: BackTrack (x402r-SDK maintainers) OR we can patch our local SDK install.

**Workaround**: Pass an explicit `contracts` dict to `AdvancedEscrowClient()` instead of relying on the registry. This bypasses the chain_id lookup entirely.

---

## Reputation Phase

| Direction | Status | TX |
|-----------|--------|----|
| Agent -> Worker (score: 90) | PASS | `f8c0c652f8c3f61ee04e75bcb21601689e29c110a7cc3d0e7e7315b94f7dba79` |
| Worker -> Agent (score: 85) | SKIP | `EM_WORKER_PRIVATE_KEY` not set in local env |

**Note**: The worker private key IS available in AWS Secrets Manager (`em/test-worker` secret, key `private_key`). Future runs should source it from there:

```bash
# Fetch worker private key for full bidirectional reputation testing
export EM_WORKER_PRIVATE_KEY=$(aws secretsmanager get-secret-value \
  --secret-id em/test-worker --region us-east-2 \
  --query 'SecretString' --output text | python -c "import sys,json; print(json.loads(sys.stdin.read())['private_key'])")
```

---

## On-Chain Transaction Summary

8 transactions across 4 chains, all verified on-chain (status: 0x1):

| # | Chain | Type | TX Hash | Explorer |
|---|-------|------|---------|----------|
| 1 | Base | Escrow Lock | `0xd4e030...` | [BaseScan](https://basescan.org/tx/0xd4e0300d025eb1ecd86f82e7ba20839f22d72d0054b24a5e7e0e166002dba2e9) |
| 2 | Base | Release | `0xd2bab2...` | [BaseScan](https://basescan.org/tx/0xd2bab27cf0b1ce698b852be913d528391f067890eb90ba823e73314508a3d0ca) |
| 3 | Polygon | Escrow Lock | `0x781e08...` | [PolygonScan](https://polygonscan.com/tx/0x781e08f4b2ab1130416cb8ac2a1d8c9a4df338923d2ea2e1bb437ec87539a192) |
| 4 | Polygon | Release | `0xb93190...` | [PolygonScan](https://polygonscan.com/tx/0xb93190a576ad429b1a3051697e05cbfb4cbcb4e4c075b4f7b3acb2bdb7c36532) |
| 5 | Arbitrum | Escrow Lock | `0xfb471b...` | [Arbiscan](https://arbiscan.io/tx/0xfb471b4d807faa08d2c8c71feb5cad619b9b85798c827d13ab9d7083904e3e3c) |
| 6 | Arbitrum | Release | `0xeb7557...` | [Arbiscan](https://arbiscan.io/tx/0xeb7557d811f390c24a49567571779915dfe6e3ded5cabea5460e6d7424ccf52d) |
| 7 | Avalanche | Escrow Lock | `0xfae22b...` | [Snowtrace](https://snowtrace.io/tx/0xfae22be2707484bc1216fc7dcd97e4a05dc0de957cfcc3d91449827e54214b46) |
| 8 | Avalanche | Release | `0x07a4e9...` | [Snowtrace](https://snowtrace.io/tx/0x07a4e92d8f06f18a79f9f5bbee7843d57d92f22e3b451605a38751ef91066550) |

---

## Fee Math Verification

All 4 passing chains showed identical, correct fee splits:

| Chain | Lock ($) | Worker (87%) | Fee (13%) | Match |
|-------|----------|-------------|-----------|-------|
| Base | 0.100000 | 0.087000 | 0.013000 | YES |
| Polygon | 0.100000 | 0.087000 | 0.013000 | YES |
| Arbitrum | 0.100000 | 0.087000 | 0.013000 | YES |
| Avalanche | 0.100000 | 0.087000 | 0.013000 | YES |

The StaticFeeCalculator(1300 BPS) works correctly and identically on all chains.

---

## Invariants Verified

- [x] API healthy and returning all 8 networks as supported
- [x] Worker registration works (executor ID reused across chains)
- [x] Task creation with `payment_network=<chain>` works for all 7 chains
- [x] Escrow lock + release verified on-chain for Base, Polygon, Arbitrum, Avalanche
- [x] Fee calculator splits 87%/13% correctly on all 4 passing chains
- [x] Credit card model: agent pays bounty only, fee deducted on-chain at release
- [x] Agent -> Worker reputation recorded on-chain (Base)
- [ ] Monad escrow lock: blocked by SDK EIP-712 domain bug
- [ ] Celo escrow lock: blocked by SDK EIP-712 domain bug
- [ ] Optimism escrow lock: blocked by SDK missing chain registry entry
- [ ] Worker -> Agent reputation: needs `EM_WORKER_PRIVATE_KEY` (available in `em/test-worker` AWS SM)

---

## Action Items

### For BackTrack (x402r-SDK bugs)

1. **BUG-1**: `_sign_erc3009()` hardcodes `name="USD Coin"` — should read from chain or accept parameter. Affects Monad ("USDC") and Celo ("USDC").
2. **BUG-2**: Add Optimism (chain 10) to `ESCROW_CONTRACTS` registry with correct infrastructure addresses.

### For Us (workarounds, if needed before SDK fix)

1. **Optimism**: Pass explicit `contracts` dict to `AdvancedEscrowClient()` bypassing the chain_id registry lookup.
2. **Monad/Celo**: Monkey-patch `_sign_erc3009()` to use correct domain params from our NETWORK_CONFIG, or override at the `AdvancedEscrowClient` level.
3. **Worker reputation**: Source `EM_WORKER_PRIVATE_KEY` from AWS Secrets Manager `em/test-worker` for full bidirectional reputation testing.

---

## AWS Secrets Reference (for future Golden Flow runs)

| Secret | Key | Purpose |
|--------|-----|---------|
| `em/x402` | `PRIVATE_KEY` | Platform wallet (agent payments, escrow operations) |
| `em/x402` | `X402_RPC_URL` | QuikNode Base RPC (private, higher rate limits) |
| `em/test-worker` | `private_key` | Worker wallet private key (for on-chain reputation signing) |
| `em/test-worker` | `address` | Worker wallet address (`0x52E0...`) |
| `em/test-worker` | `keystore_password` | Keystore encryption password |

---

## Excluded Chains

| Chain | Reason | Status |
|-------|--------|--------|
| **Ethereum** | x402r-SDK factory label mismatch (StaticFeeCalculator/OrCondition swapped) | Pending Ali's fix |

---

## Appendix: USDC Domain Separator Audit (all 8 chains)

Queried on-chain `name()` and `version()` for USDC contracts on all networks:

| Chain | USDC Address | On-chain `name()` | On-chain `version()` |
|-------|-------------|-------------------|---------------------|
| Base | `0x8335...2913` | "USD Coin" | "2" |
| Polygon | `0x3c49...3359` | "USD Coin" | "2" |
| Arbitrum | `0xaf88...5831` | "USD Coin" | "2" |
| Avalanche | `0xB97E...48a6E` | "USD Coin" | "2" (note: Avalanche USDC is bridged, may use version="1" in some deployments) |
| Optimism | `0x0b2C...Ff85` | "USD Coin" | "2" |
| Monad | `0x7547...b603` | **"USDC"** | "2" |
| Celo | `0xcebA...18C` | **"USDC"** | "2" |
| Ethereum | `0xA0b8...eB48` | "USD Coin" | "2" |

**Pattern**: Circle's native USDC uses "USD Coin" on most EVM chains. Monad and Celo use the shorter "USDC" name. All use version "2".

Our `NETWORK_CONFIG` in `sdk_client.py` had incorrect values for Monad and Celo:
- Monad: had `name="USD Coin", version="1"` -> should be `name="USDC", version="2"`
- Celo: had `name="USD Coin", version="1"` -> should be `name="USDC", version="2"`

**Note**: While updating our NETWORK_CONFIG fixes the data for our reference, the actual signing happens in the SDK's `_sign_erc3009()` which ignores our config. The SDK fix is the real blocker.
