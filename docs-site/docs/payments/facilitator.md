# x402 Facilitator

The **x402 Facilitator** is the payment routing infrastructure that enables gasless, cross-chain cryptocurrency payments for Chamba.

## What is the Facilitator?

The facilitator is a server operated by Ultravioleta DAO that:

1. **Receives payment authorizations** from AI agents
2. **Routes payments** to the correct blockchain network
3. **Handles gas fees** so users don't need native tokens
4. **Verifies settlements** and confirms payment completion
5. **Supports EIP-3009** for gasless USDC transfers

## Endpoints

| Environment | URL |
|-------------|-----|
| Production | `https://facilitator.ultravioletadao.xyz` |
| SDK Default | `https://x402.ultravioleta.xyz` |

## How Payments Flow Through the Facilitator

```
AI Agent                    Facilitator                   Blockchain
   │                            │                            │
   │  1. POST /authorize        │                            │
   │  {amount, token, network}  │                            │
   │ ─────────────────────────► │                            │
   │                            │  2. Create EIP-3009 sig    │
   │                            │ ──────────────────────────►│
   │                            │                            │
   │                            │  3. Submit transaction      │
   │                            │ ──────────────────────────►│
   │                            │                            │
   │                            │  4. Confirm settlement      │
   │  5. 200 OK {tx_hash}      │ ◄──────────────────────────│
   │ ◄───────────────────────── │                            │
```

## Integration with Chamba

Chamba uses the facilitator at two levels:

### SDK Client (Recommended)

```python
from uvd_x402_sdk import X402Client

client = X402Client(
    facilitator_url="https://facilitator.ultravioletadao.xyz",
    private_key=os.environ["X402_PRIVATE_KEY"],
)

# Authorize payment
result = await client.authorize(
    amount=10.00,
    token="USDC",
    network="base",
    recipient="0xWorkerAddress...",
)
```

### Raw HTTP Client

```python
from chamba.integrations.x402 import X402Client

client = X402Client(
    rpc_url="https://mainnet.base.org",
    private_key="0x...",
    facilitator_url="https://facilitator.ultravioletadao.xyz",
)

# Create escrow deposit
tx = await client.create_deposit(
    amount=10_000_000,  # 10 USDC (6 decimals)
    token="USDC",
    recipient="0xWorker...",
)
```

## Gasless Payments (EIP-3009)

The facilitator implements EIP-3009 (`transferWithAuthorization`) which allows USDC transfers without the sender needing ETH for gas:

1. Agent signs an off-chain authorization message
2. Facilitator submits the transaction on-chain
3. Facilitator pays the gas fee
4. USDC transfers directly from agent to escrow

This means:
- **Agents don't need ETH/native tokens**
- **Workers don't need gas to receive payments**
- **Sub-cent transaction costs** on L2s like Base

## Merchant Registration

Chamba registers as a merchant on the x402 MerchantRouter to receive payments:

```typescript
// From scripts/register_x402r_merchant.ts
const merchantRouter = "0xa48E8AdcA504D2f48e5AF6be49039354e922913F"
const depositFactory = "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814"

// Deploy deterministic proxy for USDC
const proxy = await factory.deployProxy(USDC_ADDRESS)

// Register on merchant router
await router.registerMerchant(chambaAddress, [proxy])
```

## Supported by the Facilitator

| Feature | Status |
|---------|--------|
| Multi-network routing | 17+ mainnets |
| Gasless EIP-3009 | USDC, EURC |
| Payment verification | Real-time |
| Settlement confirmation | < 30 seconds on L2 |
| Multi-token | USDC, EURC, DAI, USDT |
| Escrow integration | x402r contracts |
