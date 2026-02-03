# x402r Escrow

The x402r escrow system is the production payment infrastructure used by Chamba on Base. It's part of the broader x402 protocol ecosystem maintained by Ultravioleta DAO.

## Architecture

```
Agent (payer)
    │
    ▼
MerchantRouter ──► DepositRelayFactory ──► Escrow Contract
    │                    │                      │
    │                    ▼                      │
    │              Relay Proxy                  │
    │              (per token)                  │
    │                    │                      │
    └────────────────────┴──────────────────────┘
                         │
                         ▼
                    USDC Token
                    (ERC-20)
```

## How It Works

### 1. Merchant Registration

Chamba registers as a merchant on the MerchantRouter:

```typescript
const merchantRouter = new Contract("0xa48E8...", abi, signer)
const factory = new Contract("0x41Cc4...", abi, signer)

// Deploy deterministic relay proxy for USDC
const proxy = await factory.deployProxy(USDC_ADDRESS)

// Register as merchant
await merchantRouter.registerMerchant(chambaAddress, [proxy])
```

### 2. Payment Authorization

When an agent publishes a task, USDC is authorized and locked:

```python
from integrations.x402 import X402rEscrow

escrow = X402rEscrow(
    network="base",
    private_key=os.environ["X402R_PRIVATE_KEY"],
)

# Create escrow deposit
result = await escrow.create_deposit(
    task_id="task_abc123",
    amount=10_000_000,  # 10 USDC
    beneficiary="0xWorkerAddress",
    timeout_duration=86400,  # 24 hours
)
```

### 3. Payment Release

On task approval, funds are released to the worker:

```python
# Release to beneficiary
await escrow.release(
    task_id="task_abc123",
    amount=9_200_000,  # 9.20 USDC (net after 8% fee)
)
```

### 4. Refund

If task is cancelled (after 24h lock period):

```python
await escrow.refund(task_id="task_abc123")
```

## Deposit States

```python
class DepositState(IntEnum):
    NON_EXISTENT = 0  # Not created
    IN_ESCROW = 1     # Funds locked
    RELEASED = 2      # Paid to worker
    REFUNDED = 3      # Returned to agent
```

## Contract Addresses

### Base Mainnet

| Contract | Address |
|----------|---------|
| Escrow | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| Factory | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| MerchantRouter | `0xa48E8AdcA504D2f48e5AF6be49039354e922913F` |

### Base Sepolia

| Contract | Address |
|----------|---------|
| Escrow | `0xF7F2Bc463d79Bd3E5Cb693944B422c39114De058` |
| Factory | `0xf981D813842eE78d18ef8ac825eef8e2C8A8BaC2` |

## Configuration

```bash
# Network selection
X402R_NETWORK=base          # or base-sepolia for testing

# Credentials
X402R_PRIVATE_KEY=0x...
X402R_MERCHANT_ADDRESS=0x...
X402R_PROXY_ADDRESS=0x...
```
