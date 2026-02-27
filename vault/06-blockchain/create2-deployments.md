---
date: 2026-02-26
tags:
  - domain/blockchain
  - concept/deployment
  - concept/create2
status: active
aliases:
  - CREATE2
  - Deterministic Deployment
  - Same-Address Deployment
related-files:
  - scripts/deploy-payment-operator.ts
---

# CREATE2 Deployments

**CREATE2** is an EVM opcode that enables deterministic contract
deployment -- the same bytecode + salt always produces the same address
regardless of which chain it is deployed on.

## How CREATE2 Works

```
address = keccak256(0xff ++ deployer ++ salt ++ keccak256(bytecode))
```

The resulting address depends only on:
1. The deployer contract address (factory)
2. The salt (arbitrary bytes32)
3. The contract bytecode (init code)

Since none of these depend on chain state, the same address is produced
on every EVM chain.

## CREATE2 Contracts in Execution Market

| Contract | Address (All Mainnets) |
|----------|----------------------|
| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| ERC-8004 Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| ERC-8004 Identity (Testnets) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| AuthCaptureEscrow (Arb/Avax/Celo/Monad/Opt) | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| PaymentOperator (Arb/Avax/Celo/Opt) | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

## Benefits

- **Cross-chain consistency**: Same address on every chain simplifies
  SDK configuration and contract lookups
- **Predictability**: Address known before deployment, enabling
  pre-configuration of dependent systems
- **Verification**: Easy to confirm a contract is authentic by checking
  the address matches the expected CREATE2 output

## Non-CREATE2 Contracts

Some contracts have chain-specific addresses due to different constructor
arguments or deployment timing:
- Base PaymentOperator: `0x271f...` (deployed separately)
- Ethereum PaymentOperator: `0x69B6...`
- Monad PaymentOperator: `0x9620...`

## Related

- [[contract-addresses]] -- full address table
- [[erc-8004]] -- identity registry using CREATE2
