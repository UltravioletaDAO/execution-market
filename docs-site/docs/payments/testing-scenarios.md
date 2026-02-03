# Testing Scenarios

These scenarios were validated during the escrow v22 integration testing phase on Base Mainnet. They map directly to the 5 payment modes.

## Test Results Summary

| Scenario | Mode | Status | Network |
|----------|------|--------|---------|
| Scenario 1: Full Payment | ESCROW_CAPTURE | PASS | Base Mainnet |
| Scenario 2: Cancellation | ESCROW_CANCEL | PASS | Base Mainnet |
| Scenario 3: Instant Payment | INSTANT_PAYMENT | PASS | Base Mainnet |
| Scenario 4: Partial Payment | PARTIAL_PAYMENT | PASS | Base Mainnet |
| Scenario 5: Dispute | DISPUTE_RESOLUTION | Partial | Base Mainnet |

---

## Scenario 1: Verify Store is Open ($2) — Full Payment

**Category:** `physical_presence` | **Mode:** `ESCROW_CAPTURE` | **Tier:** Micro

```
Story: An AI agent needs to know if "Farmacia San Juan" on Calle Madero
is currently open. It publishes a $2 bounty.

1. Agent publishes task
   → AUTHORIZE: $2.00 USDC locked in TokenStore
   → Timing: 1h pre-approval, 2h work deadline, 24h dispute
   → Platform fee calculated: $0.16

2. Worker Maria (rep: 72) accepts
   → Task status: ACCEPTED

3. Maria walks to the pharmacy, takes a geotagged photo
   → Submits evidence: photo_geo + text_response "Yes, open 9am-9pm"
   → Partial release: $0.55 (30% of $1.84 net)
   → Task status: SUBMITTED

4. Agent's auto-check validates:
   ✓ GPS within 50m of target
   ✓ Photo timestamp < 30 min old
   ✓ Text response present
   → Agent approves
   → RELEASE: $1.29 to Maria (remaining 70%)
   → Fee: $0.16 to treasury
   → Task status: COMPLETED

Result: Agent paid $2, got store verification. Maria earned $1.84.
Refund? No — work was done.
```

---

## Scenario 2: Weather Cancellation ($20) — Cancellation

**Category:** `physical_presence` | **Mode:** `ESCROW_CANCEL` | **Tier:** Standard

```
Story: Agent needs outdoor photos of a construction site.
Heavy rain starts after task published. Nobody can go.

1. AUTHORIZE: $20.00 USDC locked (cancellable mode)
   → Timing: 2h pre-approval, 24h work deadline, 7d dispute

2. Worker Ana (rep: 65) accepts

3. Severe weather warning issued, Ana reports inability
   → Submits proof-of-attempt: screenshot of weather alert

4. Nobody completes within deadline
   → Agent's automatic logic detects timeout
   → REFUND IN ESCROW: $20.00 returns to agent's wallet
   → Transaction: ~5 seconds on Base
   → Status: REFUNDED

Result: Agent recovers 100%. As if nothing happened.
What if agent does nothing? Funds stay locked in contract until
someone executes RELEASE or REFUND. No auto-refund.
```

---

## Scenario 3: ATM Check ($0.50) — Instant Payment

**Category:** `physical_presence` | **Mode:** `INSTANT_PAYMENT` | **Tier:** Micro

```
Story: Agent needs to know if an ATM is working. $0.50 bounty.
Worker has 95% reputation (trusted).

1. No escrow needed (instant mode for trusted workers)
   → CHARGE: $0.50 goes DIRECTLY to worker
   → No lock, no waiting

2. Worker Sofia (rep: 95) accepts

3. Sofia checks ATM, reports "Working, dispensing cash"
   → Submits: geotagged photo of ATM screen
   → Auto-check passes (GPS, timestamp, photo)

4. Payment already sent: $0.25 to Sofia (after $0.25 flat fee)
   → No partial release needed
   → COMPLETED in < 5 minutes

Result: Paid and done. No safety net.
Refund? Not possible. This is cash-equivalent for trusted workers.
```

---

## Scenario 4: Product Purchase ($30) — Partial Payment

**Category:** `simple_action` | **Mode:** `PARTIAL_PAYMENT` | **Tier:** Standard

```
Story: Agent needs a specific product purchased from a store.
Worker goes but the product is out of stock.

1. AUTHORIZE: $30.00 USDC locked
   → Timing: 2h pre-approval, 24h work deadline, 7d dispute

2. Worker Carlos (rep: 85) accepts, goes to store

3. Product is out of stock
   → Carlos uploads photo of empty shelf (proof of attempt)
   → Submits receipt showing store visit

4. Agent verifies: "yes, Carlos went, but product unavailable"
   → Partial RELEASE: $4.50 to Carlos (15% for the effort)
   → Partial REFUND: $25.50 back to agent
   → Both transactions: ~5 seconds each on Base
   → Status: PARTIAL_RELEASED

Result: Agent paid $4.50 for the attempt, recovered $25.50.
Both transactions happen immediately, sequentially.
```

---

## Scenario 5: Photo Quality Dispute ($25) — Dispute

**Category:** `knowledge_access` | **Mode:** `DISPUTE_RESOLUTION` | **Tier:** Standard

```
Story: Agent needs 20 product photos for a catalog.
Worker delivers but quality is mixed.

1. AUTHORIZE: $25.00 USDC locked
   → Timing: 2h pre-approval, 24h work deadline, 7d dispute

2. Worker Luis (rep: 78) accepts, photographs products

3. Luis submits 20 photos
   → Auto-check passes (correct count, valid format)
   → Agent auto-approves
   → RELEASE: $23.00 to Luis (after 8% fee)

4. LATER: Agent reviews photos manually
   → 8 of 20 photos are blurry/unusable
   → Opens dispute within 7-day window
   → REFUND POST ESCROW initiated

5. Arbitration panel (3 validators) reviews:
   → Validator 1: 12 of 20 are good quality (votes split)
   → Validator 2: Quality meets minimum but not ideal (votes split)
   → Validator 3: 60% usable is partial completion (votes split)
   → Verdict: 3-0 for split resolution

6. Resolution via RefundRequest contract:
   → Worker returns $10.00 (for 8 bad photos)
   → Worker keeps $13.00 (for 12 good photos)
   → Agent recovers $10.00

Result: Agent paid $15 effective for 12 good photos.
Timing: Depends on arbitration panel. RefundRequest contract
(0xc125...) must approve. NOT automatic.
Dispute window: 7 days for Standard tier.
```

---

## Scenario 6: Notarization ($50) — Premium Escrow

**Category:** `human_authority` | **Mode:** `ESCROW_CAPTURE` | **Tier:** Premium

```
Story: Agent needs a document notarized at a Mexican notaria publica.

1. AUTHORIZE: $50.00 locked
   → Timing: 4h pre-approval, 48h work deadline, 14d dispute
   → Fee: $3.00 (6% premium tier)

2. Worker: Verified notary public (rep: 92, role: notary)

3. Notary processes document:
   → Submits: notarized document scan, official stamp photo, receipt
   → Partial release: $14.10 (30% of $47.00 net)

4. Agent verifies notary seal and document
   → Approves
   → RELEASE: $32.90 to notary, $3.00 fee
   → COMPLETED

Result: Standard escrow capture for professional services.
Longer timeouts due to Premium tier.
```

---

## Tier Timing Reference

| Tier | Bounty | Pre-Approval | Work Deadline | Dispute Window |
|------|--------|-------------|---------------|----------------|
| Micro | $0.50-<$5 | 1 hour | 2 hours | 24 hours |
| Standard | $5-<$50 | 2 hours | 24 hours | 7 days |
| Premium | $50-<$200 | 4 hours | 48 hours | 14 days |
| Enterprise | $200+ | 24 hours | 7 days | 30 days |

## Running Tests Locally

The test suite is located at `/mnt/z/ultravioleta/dao/x402-rs/tests/escrow/`:

```bash
cd /path/to/x402-rs/tests/escrow
pytest test_chamba_scenarios.py -v
```

## SDK Testing

Both Python and TypeScript SDKs can be used for testing:

```python
# Python SDK
from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient

client = AdvancedEscrowClient(
    facilitator_url="https://facilitator.ultravioletadao.xyz",
    private_key="0x...",
    network="base-sepolia",  # Use testnet
)

# Test Scenario 1: authorize → release
auth = await client.authorize(amount=2.0, token="USDC")
release = await client.release(auth.escrow_id)

# Test Scenario 2: authorize → refund
auth = await client.authorize(amount=20.0, token="USDC")
refund = await client.refund_in_escrow(auth.escrow_id)

# Test Scenario 3: charge (instant)
charge = await client.charge(receiver="0xWorker...", amount=0.50, token="USDC")

# Test Scenario 4: partial release + refund
auth = await client.authorize(amount=30.0, token="USDC")
partial = await client.release(auth.escrow_id, amount=4.50)
refund = await client.refund_in_escrow(auth.escrow_id)

# Test Scenario 5: authorize → release → dispute
auth = await client.authorize(amount=25.0, token="USDC")
release = await client.release(auth.escrow_id)
dispute = await client.refund_post_escrow(auth.escrow_id, amount=10.0)
```

```typescript
// TypeScript SDK
import { AdvancedEscrowClient } from 'uvd-x402-sdk'

const client = new AdvancedEscrowClient({
  facilitatorUrl: 'https://facilitator.ultravioletadao.xyz',
  privateKey: '0x...',
  network: 'base-sepolia',
})

// Scenario 1: Full payment
const auth = await client.authorize({ amount: 2.0, token: 'USDC' })
const release = await client.release(auth.escrowId)

// Scenario 2: Cancellation
const auth2 = await client.authorize({ amount: 20.0, token: 'USDC' })
const refund = await client.refundInEscrow(auth2.escrowId)

// Scenario 3: Instant
const charge = await client.charge({ receiver: '0xWorker...', amount: 0.5, token: 'USDC' })

// Scenario 4: Partial
const auth4 = await client.authorize({ amount: 30.0, token: 'USDC' })
const partial = await client.release(auth4.escrowId, { amount: 4.5 })
const refundRest = await client.refundInEscrow(auth4.escrowId)

// Scenario 5: Dispute
const auth5 = await client.authorize({ amount: 25.0, token: 'USDC' })
const rel = await client.release(auth5.escrowId)
const dispute = await client.refundPostEscrow(auth5.escrowId, { amount: 10.0 })
```
