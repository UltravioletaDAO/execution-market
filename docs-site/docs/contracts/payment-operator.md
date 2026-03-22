# PaymentOperator

The **PaymentOperator** is Execution Market's per-configuration contract that sits between the Facilitator and the AuthCaptureEscrow. It defines the fee split logic and access control for all payment operations.

## Role

```
Facilitator → PaymentOperator → AuthCaptureEscrow
                    ↓
            StaticFeeCalculator
         (splits worker 87% / operator 13%)
```

## Deployed Addresses

| Network | Address |
|---------|---------|
| Base | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` |
| Ethereum | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` |
| Polygon | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` |
| Arbitrum, Avalanche, Celo, Optimism | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Monad | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` |

## Key Components

### StaticFeeCalculator

Plugged into the PaymentOperator. Calculates the fee split:
- Input: gross bounty amount
- Output: `(workerAmount, operatorAmount)`
- Rate: **1300 BPS = 13%**
- Worker gets: 87%

The calculator is read-only and stateless — no risk of manipulation.

### StaticAddressCondition

Access control condition that only allows the **Facilitator EOA** (`0x103040545AC5031A11E8C03dd11324C7333a13C7`) to authorize, release, or refund. This prevents unauthorized payment operations.

### distributeFees()

After fee accumulation in the operator, this function sweeps to treasury:

```bash
# Manual sweep via admin API
curl -X POST https://api.execution.market/api/v1/admin/fees/sweep \
  -H "X-Admin-Key: your_admin_key"
```

This is also called automatically (best-effort) after each task completion.

## Deployment

PaymentOperators are deployed via `scripts/deploy-payment-operator.ts`:

```bash
cd scripts
npx tsx deploy-payment-operator.ts --network base
```

After deployment, the operator must be registered in the Facilitator's allowlist.

## Upgrade Policy

PaymentOperators are immutable once deployed. To change fee rates or conditions, a new operator must be deployed and registered. The old operator remains valid for existing escrows until they are released or expire.

## Fee Accumulation

Fees accumulate in the PaymentOperator contract as USDC. The treasury wallet receives them via `distributeFees()`. The platform wallet never holds operational funds.

## Source Code

See `contracts/` directory and `scripts/deploy-payment-operator.ts` in the repository.

BackTrack's x402r-contracts repository contains the base `PaymentOperator` implementation:
[github.com/BackTrackCo/x402r-contracts](https://github.com/BackTrackCo/x402r-contracts)
