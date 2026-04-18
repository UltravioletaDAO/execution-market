---
date: 2026-04-17
tags:
  - type/adr
  - domain/agents
  - domain/security
  - domain/infrastructure
status: active
aliases:
  - ADR Auth Discovery
  - OAuth Non-Implementation
related-files:
  - dashboard/public/.well-known/oauth-protected-resource
  - dashboard/public/skill.md
  - mcp_server/api/auth.py
---

# ADR: Agent Auth Discovery — why we do not publish OAuth/OIDC metadata

**Status:** accepted
**Date:** 2026-04-17
**Deciders:** Ultravioleta DAO
**Scanner reference:** `isitagentready.com` scan on 2026-04-17 flagged
`/.well-known/openid-configuration` and
`/.well-known/oauth-authorization-server` as missing (failure AR-05).

## Context

Agent-readiness scanners check for OAuth 2.0 and OpenID Connect discovery
documents under `/.well-known/`. The assumption baked into those specs is
that any protected resource has a central **authorization server** that issues
bearer tokens, and that agents need to discover the token endpoint to obtain
one.

Execution Market does **not** have an authorization server. The MCP server
and REST API authenticate requests in two ways:

1. **ERC-8128 request signatures (production path).** Each request is signed
   by the caller's wallet. The server verifies the signature against the
   agent's on-chain identity (ERC-8004 Identity Registry). There is no token,
   no session, no intermediary issuer — the wallet is the identity.
2. **API key (internal testing only).** Guarded behind the
   `EM_API_KEYS_ENABLED` flag (default `false` in production). Never enabled
   for external callers.

## Decision

We do **not** publish the OAuth/OIDC discovery documents the scanner expects:

- No `/.well-known/openid-configuration`
- No `/.well-known/oauth-authorization-server`

We **do** publish `/.well-known/oauth-protected-resource` (RFC 9728) with:

- `resource` pointing at `https://api.execution.market`
- `authorization_servers: []` (explicitly empty — required by RFC 9728 even
  when zero servers apply)
- A non-standard `x-authentication-schemes` array surfacing ERC-8128 and the
  disabled-by-default API key scheme
- An `x-note` field making the design decision explicit to any agent that
  parses the document

## Rationale

### Publishing a stub would be misleading

The scanner grades based on presence, not semantic truth. We could score
higher by serving a fake `/.well-known/openid-configuration` pointing at an
unused `authorization_endpoint`. An agent that trusts that document would
then try to initiate an OAuth flow we cannot fulfil, and fail with a
confusing error far from the root cause.

A scanner failure against `AR-05` is the correct signal — it reflects that
we genuinely do not speak OAuth. Agents that check the scanner's criteria
literally will then consult our `oauth-protected-resource` document, read
the `x-authentication-schemes` hint, and discover ERC-8128. That is the
behavior we want.

### ERC-8128 is strictly more trust-minimized than OAuth

OAuth pushes identity through a central authorization server. Trust-wise,
that's a counterparty who can revoke, rotate, or front-run the relationship
between caller and resource. ERC-8128 has no such counterparty — the wallet's
on-chain identity is the authorization. This aligns with the platform's
broader "settlement layer cannot hold funds" architecture (ADR-001) where
every component is either trustless or provably minimizable.

Downgrading the auth path to OAuth just to satisfy the scanner would
introduce the exact trust surface the rest of the system is designed to
eliminate.

### Alternatives considered

1. **Publish OIDC stub with `authorization_endpoint` pointing at a dashboard
   page that explains the actual scheme.** Rejected: still triggers OAuth
   flows in clients that parse the document literally. The explanation page
   is never reached by non-humans.
2. **Wait for an agent-native auth discovery spec (draft form today).**
   Deferred: we'll adopt one when it matures. Until then, the
   `x-authentication-schemes` extension on our protected-resource document
   is the lowest-misinformation option.
3. **Implement a minimal OAuth 2.0 endpoint backed by ERC-8128.** Plausible
   as a bridge but costs a full server-side OAuth implementation with no
   current consumer asking for it. Re-evaluate if an integration partner
   requires OAuth.

## Consequences

**Positive**
- Scanner failures accurately reflect platform reality.
- No misleading stubs in the discovery surface.
- Path for agents to discover ERC-8128: Link header → api-catalog →
  oauth-protected-resource → `x-authentication-schemes` → `skill.md`
  authentication section.

**Negative**
- Agent-readiness score caps around 85 instead of 95 while the scanner
  continues treating OAuth/OIDC as mandatory. Tradeoff accepted.
- Any agent built on the assumption "every site has OAuth discovery" will
  fail on our surface. Mitigation: the skill.md authentication section
  documents ERC-8128 explicitly.

## Revisit triggers

- An agent-native auth discovery RFC reaches stable status.
- A major integration partner requires OAuth; we evaluate whether to bridge
  ERC-8128 behind an OAuth facade or wait for them to add ERC-8128 support.
- The scanner adds a first-class rule for wallet-based auth schemes (e.g.
  reads `x-authentication-schemes` or the upcoming EIP-4361 "Sign-In with
  Ethereum" discovery extension).

## References

- RFC 9728 — OAuth 2.0 Protected Resource Metadata
- RFC 8414 — OAuth 2.0 Authorization Server Metadata (not implemented,
  see decision above)
- OpenID Connect Discovery 1.0 (not implemented)
- ERC-8128 — Agent Request Signatures
- ERC-8004 — Trustless Agent Identity Registry (Base mainnet, agent #2106)
- [[MARKDOWN_NEGOTIATION]] — sibling ADR for Phase 2 of the agent readiness
  plan
- `.unused/cloudflare-agentic-site-improvement.txt` — original scanner
  recommendations that triggered this Master Plan
