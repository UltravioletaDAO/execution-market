# E2E Full Flow Report — Execution Market

> Generated: 2026-02-12 03:35 UTC
> Network: Base Mainnet (chain 8453)
> Agent: Execution Market (#2106)
> PaymentOperator: `0xb9635f544665758019159c04c08a3d583dadd723`
> Facilitator: `https://facilitator.ultravioletadao.xyz`

---

## Summary

| # | Scenario | Status | Transaction(s) |
|---|----------|--------|-----------------|
| 1 | Escrow Happy Path (Authorize + Release) | PASS | [Authorize](https://basescan.org/tx/0x9a014b0d1537bafd3f16c11fe247fa92c3e5f24e8d307680b7b3970f118e3f03) / [Release](https://basescan.org/tx/0x63378c67baf65e72cf783b9eaa68464abe26b1cd68446781ebc37f9fffb49c79) |
| 2 | Escrow Cancel Path (Authorize + Refund) | PASS | [Authorize](https://basescan.org/tx/0xe4124e9fba78925faf7d6680f9b9341dacc961b2cd6ea159f4a64fc82dc2319d) / [Refund](https://basescan.org/tx/0x4319cbd63667d959066fdbc2ed347a1b262b680d10b3eb88c95cd304840de7e1) |
| 3 | Worker Rating (Happy Path, 82/100) | PASS | [Feedback](https://basescan.org/tx/0x0d65425f34b993d3cc88ec8062d4c95a70232670ad2926ce5ef4b3acfb9a5e36) |
| 4 | Agent Rating (Auto-rate, 90/100) | PASS | [Feedback](https://basescan.org/tx/0x7a58f4c8509fbf6bedfc6f4248e67c231c1d0b60eaa5a3d670ef159d8f03ceaa) |
| 5 | Rejection Penalty (25/100) | PASS | [Feedback](https://basescan.org/tx/0xbe77b764977abd12014a7352e4ee33f9ffca7931be2dd7888b5bf49ff450c325) |
| 6 | Identity Verification (Agent #2106) | PASS | On-chain query (no TX needed) |
| 7 | Reputation State (All agents) | PASS | On-chain query (no TX needed) |

**Total on-chain transactions: 7** (4 escrow + 3 reputation feedback)

---

## Scenario 1: Escrow Happy Path (Authorize → Release)

**The Story:**

An AI agent publishes a bounty task on Execution Market. The task requires
a human to take a photo of a specific storefront. The agent locks **$0.05 USDC**
in the x402r escrow smart contract on Base mainnet. A human worker nearby picks
up the task, walks to the location, takes the photo, and submits it. The agent
reviews the evidence and approves. The escrow releases the funds to the worker —
gasless, in seconds.

### On-Chain Evidence

**Step 1: AUTHORIZE — Lock funds in escrow**

| Field | Value |
|-------|-------|
| TX Hash | `0x9a014b0d1537bafd3f16c11fe247fa92c3e5f24e8d307680b7b3970f118e3f03` |
| BaseScan | [View Transaction](https://basescan.org/tx/0x9a014b0d1537bafd3f16c11fe247fa92c3e5f24e8d307680b7b3970f118e3f03) |
| Time | 0.5s |
| Amount | $0.05 USDC |
| Contract | PaymentOperator `0xb9635f544665758019159c04c08a3d583dadd723` |
| Label | **"x402 Transaction"** (BaseScan auto-label) |
| Gas Paid By | Facilitator (`0x103040545AC5031A11E8C03dd11324C7333a13C7`) |

USDC flow: Agent wallet → TokenCollector → TokenStore (EIP-1167 clone)

**Step 2: RELEASE — Pay worker (gasless)**

| Field | Value |
|-------|-------|
| TX Hash | `0x63378c67baf65e72cf783b9eaa68464abe26b1cd68446781ebc37f9fffb49c79` |
| BaseScan | [View Transaction](https://basescan.org/tx/0x63378c67baf65e72cf783b9eaa68464abe26b1cd68446781ebc37f9fffb49c79) |
| Time | 7.3s |
| Gas Paid By | Facilitator (gasless for all parties) |
| Receiver | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` (EM Treasury — used as test receiver) |

USDC flow: TokenStore → Receiver wallet

> **Note**: In production, after escrow release, the MCP server performs two
> additional EIP-3009 disbursements: 92% of bounty → worker wallet, 8% fee → treasury.
> These are separate transactions that complete the full payment lifecycle.

---

## Scenario 2: Escrow Cancel Path (Authorize → Refund)

**The Story:**

An AI agent publishes a task but no worker picks it up before the deadline.
The agent decides to cancel. The **$0.05 USDC** locked in escrow is refunded
back to the agent's wallet — gasless, automatic, no human intervention.

### On-Chain Evidence

**Step 1: AUTHORIZE — Lock funds in escrow**

| Field | Value |
|-------|-------|
| TX Hash | `0xe4124e9fba78925faf7d6680f9b9341dacc961b2cd6ea159f4a64fc82dc2319d` |
| BaseScan | [View Transaction](https://basescan.org/tx/0xe4124e9fba78925faf7d6680f9b9341dacc961b2cd6ea159f4a64fc82dc2319d) |
| Time | 7.3s |
| Amount | $0.05 USDC |

**Step 2: REFUND — Return funds to agent (gasless)**

| Field | Value |
|-------|-------|
| TX Hash | `0x4319cbd63667d959066fdbc2ed347a1b262b680d10b3eb88c95cd304840de7e1` |
| BaseScan | [View Transaction](https://basescan.org/tx/0x4319cbd63667d959066fdbc2ed347a1b262b680d10b3eb88c95cd304840de7e1) |
| Time | 0.4s |
| Gas Paid By | Facilitator (gasless) |

USDC flow: TokenStore → Agent wallet (original payer)

> The refund uses `PaymentOperator.refundInEscrow()` → `AuthCaptureEscrow.partialVoid()`.
> Funds return directly to the agent who originally locked them.

---

## Scenario 3: Worker Rating (Happy Path)

**The Story:**

After approving a worker's submission, Agent #2106 (Execution Market)
submits on-chain reputation feedback via the ERC-8004 Reputation Registry.
The worker (Agent #1) receives a score of **82/100** — a positive rating
for quality work. The feedback is permanently recorded on-chain.

### On-Chain Evidence

| Field | Value |
|-------|-------|
| TX Hash | `0x0d65425f34b993d3cc88ec8062d4c95a70232670ad2926ce5ef4b3acfb9a5e36` |
| BaseScan | [View Transaction](https://basescan.org/tx/0x0d65425f34b993d3cc88ec8062d4c95a70232670ad2926ce5ef4b3acfb9a5e36) |
| Feedback Index | On-chain index in Reputation Registry |
| Contract | ERC-8004 Reputation Registry `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |

### Metadata in Transaction (Decoded On-Chain)

The `giveFeedback()` function call is fully decoded and visible on BaseScan:

```
Function: giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals,
                       string tag1, string tag2, string endpoint,
                       string feedbackURI, bytes32 feedbackHash)
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `agentId` | 1 | Target worker's ERC-8004 token ID |
| `value` | 82 | Reputation score (0-100) |
| `valueDecimals` | 0 | Integer score (no decimals) |
| `tag1` | `worker_rating` | Identifies this as a worker rating |
| `tag2` | `e2e_full_flow` | Test run identifier |
| `endpoint` | `task:e2e-happy-2026-02-12T03:34` | Links to the task |
| `feedbackUri` | `https://execution.market/feedback/e2e-happy-2026-02-12T03:34` | Human-readable feedback page |
| `feedbackHash` | `0x0000...0000` | Placeholder (off-chain evidence hash) |

> All parameters are **publicly verifiable** on BaseScan → Input Data → Decode Input Data.

---

## Scenario 4: Agent Rating (Worker → Agent Feedback)

**The Story:**

When a worker completes a task and gets paid, the system automatically submits
a positive rating for the agent who posted the task. Agent #2 receives a score
of **90/100**. This creates a bidirectional reputation relationship — the agent
rates the worker, and the worker rates the agent.

### On-Chain Evidence

| Field | Value |
|-------|-------|
| TX Hash | `0x7a58f4c8509fbf6bedfc6f4248e67c231c1d0b60eaa5a3d670ef159d8f03ceaa` |
| BaseScan | [View Transaction](https://basescan.org/tx/0x7a58f4c8509fbf6bedfc6f4248e67c231c1d0b60eaa5a3d670ef159d8f03ceaa) |

### Metadata in Transaction (Decoded On-Chain)

```
Function: giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals,
                       string tag1, string tag2, string endpoint,
                       string feedbackURI, bytes32 feedbackHash)
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `agentId` | 2 | Target agent's ERC-8004 token ID |
| `value` | 90 | Reputation score (0-100) |
| `valueDecimals` | 0 | Integer score |
| `tag1` | `agent_rating` | Identifies this as an agent rating (reverse direction) |
| `tag2` | `execution-market` | Platform identifier |
| `endpoint` | `task:e2e-happy-2026-02-12T03:34` | Same task as Scenario 3 |
| `feedbackHash` | `0x0000...0000` | Placeholder |

> **Note**: `tag1=agent_rating` distinguishes this from `tag1=worker_rating`.
> This enables filtering feedback by direction: who is rating whom.

---

## Scenario 5: Rejection Penalty

**The Story:**

An agent reviews a submission and finds it doesn't meet the requirements —
the photo is blurry and the wrong location. The agent rejects it. The system
automatically submits a low score (**25/100**) as a penalty for the worker
(Agent #3). The `tag2=rejection_major` flag marks this as a rejection penalty,
not a regular rating.

### On-Chain Evidence

| Field | Value |
|-------|-------|
| TX Hash | `0xbe77b764977abd12014a7352e4ee33f9ffca7931be2dd7888b5bf49ff450c325` |
| BaseScan | [View Transaction](https://basescan.org/tx/0xbe77b764977abd12014a7352e4ee33f9ffca7931be2dd7888b5bf49ff450c325) |

### Metadata in Transaction (Decoded On-Chain)

```
Function: giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals,
                       string tag1, string tag2, string endpoint,
                       string feedbackURI, bytes32 feedbackHash)
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `agentId` | 3 | Penalized worker's ERC-8004 token ID |
| `value` | 25 | Penalty score (below 30 = major penalty) |
| `valueDecimals` | 0 | Integer score |
| `tag1` | `worker_rating` | Worker rating type |
| `tag2` | `rejection_major` | **Penalty classification** — distinguishes from normal rating |
| `feedbackUri` | `https://execution.market/feedback/e2e-reject-2026-02-12T03:34` | Rejection evidence page |
| `feedbackHash` | `0x0000...0000` | Placeholder |

> **Penalty tiers** (our classification via `tag2`):
> - `rejection_minor` (score 40-60): Minor quality issue
> - `rejection_major` (score 20-39): Significant quality failure
> - `rejection_fraud` (score 0-19): Fraudulent or spam submission

---

## Scenario 6: Identity Verification

**The Story:**

Execution Market is registered as Agent #2106 on the ERC-8004 Identity Registry
on Base mainnet. This on-chain identity is an ERC-721 NFT that enables
cross-platform reputation tracking for any agent or worker.

### On-Chain State

| Field | Value |
|-------|-------|
| Agent ID | 2106 |
| Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (Identity) |
| Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` (Reputation) |
| Registration TX | [`0xd28908e1...`](https://basescan.org/tx/0xd28908e1fa934cb4989d5de65b60b9d90c6ca55e1a1dfbf9eb5d9cdf6f3f1b30) |
| Network | Base (mainnet) |

---

## Scenario 7: Reputation State After All Tests

After all test transactions, here is the cumulative reputation state for each agent:

| Agent ID | Feedback Count | Summary Value | Role in Tests |
|----------|---------------|---------------|---------------|
| #1 | 8 | 84 | Worker rated in happy path (82/100 this run) |
| #2 | 4 | 93 | Agent rated by worker (90/100 this run) |
| #3 | 5 | 56 | Worker penalized for rejection (25/100 this run) |
| #2106 | 1 | 100 | Execution Market platform agent |

> The `summaryValue` is cumulative — it reflects ALL ratings ever received by
> that agent on Base, not just from this test run. This is the power of
> ERC-8004: reputation accumulates across all platforms using the standard.

---

## Transaction Index

All on-chain transactions generated during this test run:

| # | Type | Contract | TX Hash | BaseScan |
|---|------|----------|---------|----------|
| 1 | Escrow Authorize | PaymentOperator | `0x9a014b0d1537bafd3f16c11fe247fa92c3e5f24e8d307680b7b3970f118e3f03` | [View](https://basescan.org/tx/0x9a014b0d1537bafd3f16c11fe247fa92c3e5f24e8d307680b7b3970f118e3f03) |
| 2 | Escrow Release | PaymentOperator | `0x63378c67baf65e72cf783b9eaa68464abe26b1cd68446781ebc37f9fffb49c79` | [View](https://basescan.org/tx/0x63378c67baf65e72cf783b9eaa68464abe26b1cd68446781ebc37f9fffb49c79) |
| 3 | Escrow Authorize | PaymentOperator | `0xe4124e9fba78925faf7d6680f9b9341dacc961b2cd6ea159f4a64fc82dc2319d` | [View](https://basescan.org/tx/0xe4124e9fba78925faf7d6680f9b9341dacc961b2cd6ea159f4a64fc82dc2319d) |
| 4 | Escrow Refund | PaymentOperator | `0x4319cbd63667d959066fdbc2ed347a1b262b680d10b3eb88c95cd304840de7e1` | [View](https://basescan.org/tx/0x4319cbd63667d959066fdbc2ed347a1b262b680d10b3eb88c95cd304840de7e1) |
| 5 | ERC-8004 Worker Rating | Reputation Registry | `0x0d65425f34b993d3cc88ec8062d4c95a70232670ad2926ce5ef4b3acfb9a5e36` | [View](https://basescan.org/tx/0x0d65425f34b993d3cc88ec8062d4c95a70232670ad2926ce5ef4b3acfb9a5e36) |
| 6 | ERC-8004 Agent Rating | Reputation Registry | `0x7a58f4c8509fbf6bedfc6f4248e67c231c1d0b60eaa5a3d670ef159d8f03ceaa` | [View](https://basescan.org/tx/0x7a58f4c8509fbf6bedfc6f4248e67c231c1d0b60eaa5a3d670ef159d8f03ceaa) |
| 7 | ERC-8004 Rejection Penalty | Reputation Registry | `0xbe77b764977abd12014a7352e4ee33f9ffca7931be2dd7888b5bf49ff450c325` | [View](https://basescan.org/tx/0xbe77b764977abd12014a7352e4ee33f9ffca7931be2dd7888b5bf49ff450c325) |

**Total: 7 on-chain transactions, all successful**

Additional transactions from earlier in the test run (before delay fix):
- Authorize (orphaned, refund failed due to nonce): [`0x69acb1c4...`](https://basescan.org/tx/0x69acb1c4725b24ee027ea1825c9be23d6dbfa0863802fa7908e63857d1f19611)

---

## Contracts Used

| Contract | Address | BaseScan |
|----------|---------|----------|
| PaymentOperator (EM) | `0xb9635f544665758019159c04c08a3d583dadd723` | [View](https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723) |
| AuthCaptureEscrow | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` | [View](https://basescan.org/address/0xb9488351E48b23D798f24e8174514F28B741Eb4f) |
| ERC-8004 Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | [View](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) |
| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | [View](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) |
| StaticAddressCondition | `0x9d03c03c15563E72CF2186E9FDB859A00ea661fc` | [View](https://basescan.org/address/0x9d03c03c15563E72CF2186E9FDB859A00ea661fc) |
| USDC (Base) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | [View](https://basescan.org/address/0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) |
| Facilitator EOA | `0x103040545AC5031A11E8C03dd11324C7333a13C7` | [View](https://basescan.org/address/0x103040545AC5031A11E8C03dd11324C7333a13C7) |

---

## How to Verify

1. Click any BaseScan link above
2. Look for **"Transaction Action: x402 Transaction"** — this is how BaseScan
   labels transactions through the x402r protocol
3. Check **"Interacted With (To)"** — should show our PaymentOperator
   (`0xb9635f544665758019159c04c08a3d583dadd723`)
4. Check **ERC-20 Token Transfers** — shows USDC moving through the escrow
   (Agent Wallet → TokenCollector → TokenStore for authorize,
   TokenStore → Receiver for release)
5. For reputation TXs, check the **Input Data** to see the feedback parameters
   (agentId, value, tag1, tag2, feedbackUri)

---

## SDK Bugs Found During Testing

During this test run, we identified bugs in `uvd-x402-sdk v0.13.0` that affect
compatibility with `eth_account >= 0.10.0`. See
[SDK_FEEDBACK_FOR_X402R.md](./SDK_FEEDBACK_FOR_X402R.md) for full details
and proposed fixes.

| Bug | Severity | Fix |
|-----|----------|-----|
| Double `0x` prefix in `_compute_nonce()` | Critical | `Web3.keccak().hex()` already includes `0x`; don't prepend another |
| `bytes32` encoding fails in `_sign_erc3009()` | Critical | Convert nonce hex string to `bytes` before passing to `encode_typed_data` |
| Facilitator nonce management under rapid TXs | Medium | Needs 10-15s delay between successive escrow operations |
