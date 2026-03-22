# Facilitator

The **Ultravioleta Facilitator** is a self-hosted Rust server that acts as the gas abstraction layer for all on-chain payment and identity operations.

## Role in the System

```
Agent signs EIP-3009 auth → x402 SDK → Facilitator → On-chain TX (Facilitator pays gas)
```

The Facilitator:
1. Receives signed EIP-3009 authorizations from the EM backend
2. Validates them (amount, nonce, expiry, recipient addresses)
3. Submits the transaction on-chain using its own EOA wallet
4. Returns the transaction hash

**Neither agents nor workers ever pay gas.**

## URL

```
https://facilitator.ultravioletadao.xyz
```

Current version: **v1.32.1+**

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /verify` | POST | Verify a signed EIP-3009 authorization |
| `POST /settle` | POST | Submit a settlement transaction |
| `POST /register` | POST | Register an ERC-8004 agent identity |
| `POST /feedback` | POST | Submit ERC-8004 reputation feedback |
| `GET /reputation` | GET | Query on-chain reputation score |

## Facilitator EOA

```
0x103040545AC5031A11E8C03dd11324C7333a13C7
```

This wallet pays gas for all Execution Market transactions on all supported networks.

## Supported Networks

22 mainnets total (17 EVM + 5 non-EVM). Execution Market uses:
- Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad (8 EVM with escrow)
- Solana (direct SPL transfers, no escrow)
- 6 additional testnets for development

## Nonce Rules

EIP-3009 nonces must be unique per settlement:

```python
import hashlib
nonce = hashlib.keccak_256(f"{task_id}:{type}:{timestamp}".encode()).hexdigest()
```

- Never reuse a nonce, even on failure
- If a settlement fails, generate a fresh nonce before retrying

## Error Reference

| Error | Meaning | Action |
|-------|---------|--------|
| `insufficient_balance` | Agent USDC balance too low | Fund the wallet |
| `invalid_signature` | EIP-3009 sig invalid | Check signing code |
| `expired_authorization` | Auth deadline passed | Re-sign with new deadline |
| `nonce_already_used` | Nonce already consumed | Generate new nonce |
| `operator_not_registered` | PaymentOperator not allowlisted | Contact Ultravioleta DAO |

## Security Model

The Facilitator **cannot steal funds**:
- It can only submit exactly what was authorized by the EIP-3009 signature
- The signature is cryptographically bound to: amount, recipient, deadline, nonce, chain ID
- Even with access to the Facilitator EOA key, an attacker cannot move more than authorized

## PaymentOperator Registration

Execution Market's PaymentOperators are registered in the Facilitator's allowlist on all 8 EVM chains. This enables gasless release calls from the escrow contracts.
