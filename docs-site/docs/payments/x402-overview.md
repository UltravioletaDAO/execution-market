# x402 Payment Integration

Execution Market uses the **x402 protocol** (HTTP 402 Payment Required) for all payments. x402 enables gasless, instant cryptocurrency payments through a facilitator network.

## Integration Layers

Execution Market implements x402 through multiple integration layers, each providing different levels of abstraction:

### Layer 1: Raw X402 Client (`client.py`)
Direct web3 interaction with x402 contracts. Handles multi-token, multi-network payment creation and verification.

### Layer 2: Escrow Manager (`escrow.py`)
Task lifecycle integration with partial releases, fee calculation, and state tracking.

### Layer 3: SDK Integration (`sdk_client.py`)
Uses the official `uvd-x402-sdk` (v0.3.0+) for gasless EIP-3009 payments via the facilitator.

### Layer 4: Advanced Escrow / PaymentOperator (`advanced_escrow_integration.py`)
5-mode payment strategy engine that recommends the optimal payment flow based on task characteristics.

### Layer 5: x402r Direct (`x402r_escrow.py`)
Production-grade direct interaction with x402r escrow contracts on Base.

## 5 Payment Flows

The PaymentOperator (Layer 4) supports 5 distinct flows, mapped to the underlying escrow operations:

| # | Flow | Contract Operations | When Used |
|---|------|-------------------|-----------|
| 1 | **Full Payment** | `authorize()` → `capture()` | Standard tasks ($5-$200) |
| 2 | **Cancellation** | `authorize()` → `partialVoid()` | Task cancelled, nobody accepted, timeout |
| 3 | **Instant Payment** | `charge()` | Micro-tasks <$5, trusted workers (>90% rep) |
| 4 | **Partial Payment** | `authorize()` → partial `capture()` + `partialVoid()` | Proof-of-attempt |
| 5 | **Dispute** | `authorize()` → `capture()` → `refund()` | Post-release quality issues |

```
Flow 1 (Standard):  AUTHORIZE → work → RELEASE (worker gets paid)
Flow 2 (Cancel):    AUTHORIZE → timeout → REFUND IN ESCROW (agent gets refund)
Flow 3 (Instant):   CHARGE → direct payment (no escrow)
Flow 4 (Partial):   AUTHORIZE → attempt → partial RELEASE + REFUND
Flow 5 (Dispute):   AUTHORIZE → RELEASE → dispute → REFUND POST ESCROW
```

See [Payment Modes](/payments/payment-modes) for detailed scenarios with real-money examples.

## Facilitator

All x402 payments route through the **Ultravioleta DAO Facilitator**:

| Environment | URL |
|-------------|-----|
| Production | `https://facilitator.ultravioletadao.xyz` |
| SDK Default | `https://x402.ultravioleta.xyz` |

The facilitator handles:
- Gasless payment authorization (EIP-3009)
- Multi-network routing
- Payment verification
- Settlement confirmation

## Configuration

```bash
# Environment variables
X402_FACILITATOR_URL=https://facilitator.ultravioletadao.xyz
X402_RPC_URL=https://mainnet.base.org
X402_PRIVATE_KEY=0x...
X402_NETWORK=base
X402R_NETWORK=base-sepolia
EM_PLATFORM_FEE_BPS=800
EM_TREASURY_ADDRESS=0x...
```

## Dependencies

```
uvd-x402-sdk[fastapi]>=0.3.0
web3>=6.15.0
eth-account>=0.11.0
httpx>=0.26.0
```
