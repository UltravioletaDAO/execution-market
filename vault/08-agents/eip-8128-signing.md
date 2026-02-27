---
date: 2026-02-26
tags:
  - domain/agents
  - security/authentication
  - protocol/eip-8128
status: active
aliases:
  - EIP-8128 Signing
  - Wallet-Based Auth
related-files:
  - scripts/kk/lib/eip8128-signer.ts
  - mcp_server/api/agent_auth.py
---

# EIP-8128 Signing

Agents authenticate HTTP requests by signing them with their wallet private keys. This replaces API keys with cryptographic proof of identity tied to on-chain ERC-8004 NFTs.

## How It Works

1. Agent constructs the HTTP request (method, URL, body, timestamp)
2. Agent creates a canonical message from request components
3. Agent signs the message with their wallet private key (same key that owns the ERC-8004 NFT)
4. Signature is included in the `Authorization` header
5. Server verifies signature, recovers signer address, checks NFT ownership

## Implementation

### TypeScript (Agent Side)

Library: `scripts/kk/lib/eip8128-signer.ts`

```typescript
const signature = await signRequest({
  method: "POST",
  url: "/api/v1/tasks",
  body: JSON.stringify(taskPayload),
  privateKey: agentWalletKey,
  timestamp: Math.floor(Date.now() / 1000),
});
```

### Python (Server Side)

Module: `mcp_server/api/agent_auth.py`

The server extracts the signature from the Authorization header, recovers the signer address using `eth_account`, then verifies that the recovered address owns an ERC-8004 NFT via the identity registry.

## Advantages Over API Keys

| Feature | API Keys | EIP-8128 |
|---------|----------|----------|
| Rotation needed | Yes | No (tied to wallet) |
| Revocable | Manual | Transfer NFT |
| On-chain identity | No | Yes |
| Per-request auth | No | Yes (replay-safe) |
| Multi-agent | Separate keys | One mnemonic |

## Security Considerations

- Timestamp must be within acceptable window (prevents replay attacks)
- Body hash included in signature (prevents tampering)
- Server must verify NFT ownership on every request (not just signature validity)

## Related

- [[erc-8128-auth]] -- Protocol specification
- [[karma-kadabra-v2]] -- Primary users of this auth method
- [[authentication]] -- All authentication methods
- [[kk-agent-fleet]] -- Agents using EIP-8128
