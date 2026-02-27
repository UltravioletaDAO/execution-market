---
date: 2026-02-26
tags:
  - domain/security
  - core/auth
  - protocol/erc-8128
status: active
aliases:
  - Auth Methods
  - Authentication
related-files:
  - mcp_server/api/agent_auth.py
  - dashboard/src/context/AuthContext.tsx
  - mcp_server/api/routes.py
---

# Authentication

Four authentication methods serving different actors on the Execution Market platform. Each method maps to a specific user type and access pattern.

## Methods

| # | Method | Actor | Source |
|---|--------|-------|--------|
| 1 | Supabase Anonymous Auth | Workers (dashboard) | `AuthContext.tsx` |
| 2 | ERC-8128 Wallet Signing | AI Agents (MCP) | `agent_auth.py` |
| 3 | OAuth (Google/GitHub) | Workers (social login) | Supabase config |
| 4 | X-Admin-Key header | Admin dashboard | Env var |
| 5 | API Keys (deprecated) | Legacy -- scheduled for removal | -- |

## 1. Supabase Auth (Workers)

Anonymous sessions on first visit. Wallet linked via `link_wallet_to_session()` RPC. JWT verified with ES256 (JWKS). **Known issue**: submissions INSERT fails silently if executor not linked to session. `submitWork()` handles this.

## 2. ERC-8128 Wallet Signing (Agents)

Agent signs HTTP request with wallet key. Server recovers address, checks ERC-8004 NFT ownership. No API keys, no rotation. See [[eip-8128-signing]].

## 3. OAuth / 4. Admin / 5. API Keys

OAuth supplements anonymous auth (Google/GitHub). Admin uses `X-Admin-Key` header. API keys are deprecated, being replaced by ERC-8128.

## JWT Verification

ES256 via JWKS (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`). Audience validation disabled for Supabase compatibility.

## Related

- [[erc-8128-auth]] -- Protocol specification for wallet signing
- [[rls-policies]] -- How auth maps to database access
- [[h2a-marketplace]] -- Where auth methods intersect
- [[eip-8128-signing]] -- Implementation details
