# ChambaEscrow Contract — DEPRECATED

> **This contract has been deprecated and archived.** All payment operations now use the **x402 Facilitator** (gasless, EIP-3009 based).

## Replacement

| Old | New |
|-----|-----|
| ChambaEscrow.sol | x402 Facilitator (`uvd-x402-sdk`) |
| Direct contract calls | SDK + Facilitator (gasless) |
| Custom escrow per-network | AuthCaptureEscrow on 9 networks |

## Migration

All task payments now flow through:

```
Agent signs EIP-3009 auth → SDK → Facilitator → On-chain TX (Facilitator pays gas)
```

See [x402 Payment Architecture](/contracts/addresses) for current contract addresses.

## Historical Deployments (Read-Only)

| Network | Address | Status |
|---------|---------|--------|
| Ethereum | `0x6c320efaC433690899725B3a7C84635430Acf722` | v1.0, pre-audit, no active funds |
| Avalanche | `0xedA98AF95B76293a17399Af41A499C193A8DB51A` | v2, verified, no active funds |

Source code archived at `_archive/contracts/ChambaEscrow.sol`.
