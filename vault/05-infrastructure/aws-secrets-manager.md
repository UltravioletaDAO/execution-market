---
date: 2026-02-26
tags:
  - domain/infrastructure
  - aws
  - secrets
  - security
status: active
aliases:
  - AWS SM
  - Secrets Manager
related-files:
  - mcp_server/.env
  - .env.local
---

# AWS Secrets Manager

Centralized secret storage for Execution Market production credentials.

## Secret Paths

| Secret ID | Keys | Purpose |
|-----------|------|---------|
| `em/supabase-jwt` | `SUPABASE_JWT_SECRET` | H2A publisher auth (JWT verification) |
| `em/x402` | `PRIVATE_KEY` | Platform wallet key (settlement) |
| `em/x402` | `X402_RPC_URL` | QuikNode private Base RPC |
| `em/test-worker` | `private_key` | Test worker wallet for E2E reputation |
| `em/test-worker` | `address` | `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` |
| `kk/swarm-seed` | (mnemonic) | HD wallet seed for 24 KK agents |

## Access Pattern

```bash
# Read a secret (NEVER show output in stream)
MSYS_NO_PATHCONV=1 aws secretsmanager get-secret-value \
  --secret-id em/x402 \
  --query SecretString --output text --region us-east-2
```

## ECS Integration

ECS task definitions reference secrets via ARN:
```json
{
  "name": "PRIVATE_KEY",
  "valueFrom": "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/x402:PRIVATE_KEY::"
}
```

**NEVER put secrets as plaintext `value` in task definitions.** Always use `valueFrom` with Secrets Manager ARN.

## Security Rules

- **NEVER show private keys in logs** (user is always streaming)
- **NEVER skip tests** because "key not set" -- check AWS SM first
- Use `echo "KEY is ${VAR:+set}"` to verify existence without revealing value
- Rotate immediately if accidentally exposed

## Related

- [[wallet-roles]] -- which wallets use which secrets
- [[rpc-policy-quiknode]] -- RPC URLs stored here
- [[aws-account]] -- account context
