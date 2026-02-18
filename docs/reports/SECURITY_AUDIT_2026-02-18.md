# SECURITY AUDIT REPORT — Execution Market

**Date**: 2026-02-18
**Auditor**: Claude Code (4-agent parallel audit)
**Scope**: Full application — Backend, Frontend, Payments/Blockchain, Infrastructure
**Classification**: CONFIDENTIAL

---

## EXECUTIVE SUMMARY

| Severity | Count | Areas |
|----------|-------|-------|
| **CRITICAL** | 9 | Payments (6), Backend (3) |
| **HIGH** | 14 | Payments (7), Backend (4), Frontend (2), Infra (1) |
| **MEDIUM** | 21 | Infra (11), Frontend (5), Backend (4), Payments (7 — counted in detail below) |
| **LOW** | 13 | Frontend (6), Payments (5), Backend (2) |

**Verdict**: The application has **strong fundamentals** (proper auth model, RLS, no XSS, good CI/CD security) but the **payment layer has critical fund-safety vulnerabilities** that must be resolved before any production deployment with real funds above $1.

### Top 5 Urgent Fixes

1. **Double-spend on approval** — approval endpoint can settle payment twice (C-PAY-02)
2. **Non-atomic settlement** — worker paid but fee collection can silently fail (C-PAY-01)
3. **No EIP-3009 replay protection** — nonces are random and never tracked (C-PAY-03)
4. **SQL injection via `.ilike()`** — admin search endpoint (C-BE-03)
5. **Facilitator MITM** — no cert pinning, fake tx hashes accepted (C-PAY-04)

---

## FINDING INDEX

### CRITICAL (9)

| ID | Domain | Title | File | Line |
|----|--------|-------|------|------|
| C-PAY-01 | Payments | Non-atomic settlement (worker paid, fee lost) | `api/routers/_helpers.py` | 1115-1323 |
| C-PAY-02 | Payments | Double-spend via repeated approval | `api/routers/submissions.py` | 150-212 |
| C-PAY-03 | Payments | No EIP-3009 replay protection | `integrations/x402/sdk_client.py` | 804-865 |
| C-PAY-04 | Payments | Facilitator MITM / domain hijack | `integrations/x402/sdk_client.py` | 76-78 |
| C-PAY-05 | Payments | Private key exposure in tracebacks | `integrations/x402/payment_dispatcher.py` | 287-301 |
| C-PAY-06 | Payments | Fee calculation integer underflow | `integrations/x402/payment_dispatcher.py` | 242-281 |
| C-BE-01 | Backend | Hardcoded wallet addresses (2 different treasury addrs!) | `api/h2a.py:55`, `sdk_client.py:81` | — |
| C-BE-02 | Backend | Admin auth via query param (key in URL/logs) | `api/admin.py` | 42-106 |
| C-BE-03 | Backend | SQL injection via `.ilike()` search | `api/admin.py` | 649 |

### HIGH (14)

| ID | Domain | Title | File |
|----|--------|-------|------|
| H-PAY-01 | Payments | Idempotency relies on potentially corrupted DB | `api/routers/_helpers.py:1102` |
| H-PAY-02 | Payments | No guard against worker=agent self-payment at assignment | `api/routers/_helpers.py:1163` |
| H-PAY-03 | Payments | Facilitator response not validated (fake tx hashes accepted) | `sdk_client.py:925-950` |
| H-PAY-04 | Payments | Platform wallet address exposed in logs | `payment_dispatcher.py:284-301` |
| H-PAY-05 | Payments | Escrow state machine allows invalid transitions | `api/routers/tasks.py:537-595` |
| H-PAY-06 | Payments | Decimal precision loss in token amounts | `sdk_client.py:828-829` |
| H-PAY-07 | Payments | A2A approval bypasses PaymentDispatcher | `a2a/task_manager.py:540` |
| H-BE-01 | Backend | Case-sensitive wallet comparison in auth | `api/auth.py:373-425` |
| H-BE-02 | Backend | Missing status validation on task approval | `api/routers/submissions.py:150` |
| H-BE-03 | Backend | Unvalidated payment auth headers (replay risk) | `api/routers/submissions.py:165` |
| H-BE-04 | Backend | PII exposure in admin API (wallet + name + earnings) | `api/admin.py:1095` |
| H-FE-01 | Frontend | Auth tokens in localStorage (XSS-vulnerable) | `context/AuthContext.tsx:131` |
| H-FE-02 | Frontend | VITE_API_KEY baked into production bundle | `services/submissions.ts:21` |
| H-INFRA-01 | Infra | Hardcoded secrets in docker-compose.yml | `docker-compose.yml:123,156,185` |

### MEDIUM (21)

| ID | Domain | Title |
|----|--------|-------|
| M-PAY-01 | Payments | Balance check is advisory (non-blocking) |
| M-PAY-02 | Payments | Protocol fee cache serves stale data (5min TTL) |
| M-PAY-03 | Payments | No on-chain tx confirmation wait |
| M-PAY-04 | Payments | Worker address not validated at application time |
| M-PAY-05 | Payments | Fee collection is explicitly "non-blocking" |
| M-PAY-06 | Payments | Idempotency only checks payment table (not on-chain) |
| M-PAY-07 | Payments | No rate limiting on approve endpoint |
| M-BE-01 | Backend | API key cache TTL too long (5min), in-memory only |
| M-BE-02 | Backend | Missing rate limiting on critical endpoints |
| M-BE-03 | Backend | Insufficient input validation (agent_id, bounty float) |
| M-BE-04 | Backend | Inadequate security event logging |
| M-FE-01 | Frontend | Logout debounce race condition on wallet switch |
| M-FE-02 | Frontend | Task instructions rendered without sanitization |
| M-FE-03 | Frontend | No Content Security Policy headers |
| M-FE-04 | Frontend | Missing infinite scroll protection (no max page size) |
| M-FE-05 | Frontend | CORS configuration needs verification |
| M-INFRA-01 | Infra | Dashboard Dockerfile no explicit USER directive |
| M-INFRA-02 | Infra | npm --legacy-peer-deps bypasses vulnerability checks |
| M-INFRA-03 | Infra | deploy.yml uses static AWS credentials (not OIDC) |
| M-INFRA-04 | Infra | WebSocket auth/connection limits not verified |
| M-INFRA-05 | Infra | RLS policies incomplete (PII tables) |
| M-INFRA-06 | Infra | Migration 031 naming conflict (duplicate) |
| M-INFRA-07 | Infra | File upload size limits not enforced on frontend |
| M-INFRA-08 | Infra | Database security group access not verified |

---

## DETAILED FINDINGS

---

### C-PAY-01: Non-Atomic Settlement

**Severity**: CRITICAL
**File**: `mcp_server/api/routers/_helpers.py:1115-1323`

**Problem**: Payment settlement is not atomic. Worker disbursement (line 1166-1173) executes first. If it succeeds but fee collection fails (line 1185-1190), the code logs a warning and **returns success**. Worker gets full bounty, platform loses 13% fee.

**Impact**: Estimated 13% revenue loss per failed fee TX. No alert to admin.

**Fix**:
1. Sign both EIP-3009 auths before ANY settlement
2. Verify both tx hashes before marking task complete
3. If fee fails → refund worker and abort (or retry both atomically)

---

### C-PAY-02: Double-Spend via Repeated Approval

**Severity**: CRITICAL
**File**: `mcp_server/api/routers/submissions.py:150-212`

**Problem**: Approval endpoint generates a **new random nonce** (`secrets.token_hex(32)` at `sdk_client.py:831`) on every call. The idempotency check at line 186-191 calls `_settle_submission_payment()` AGAIN for already-approved submissions. If the payment DB record is missing or corrupted, a second settlement proceeds with a fresh nonce.

**Attack**: Agent calls `/approve` twice → two separate EIP-3009 signatures → facilitator settles both → worker paid 2X.

**Fix**:
1. Add idempotency token (UUID) created at task creation time
2. Store token in `payments` table
3. Return `409 Conflict` on duplicate approval attempts
4. Never generate a new nonce for already-approved submissions

---

### C-PAY-03: No EIP-3009 Replay Protection

**Severity**: CRITICAL
**File**: `mcp_server/integrations/x402/sdk_client.py:804-865`

**Problem**: Nonces are random (`secrets.token_hex(32)`) but **never stored or tracked**. `validAfter` is hardcoded to `0` (line 837). Any intercepted auth header can be replayed before `validBefore` expires.

**Attack**: Attacker intercepts signed auth from HTTP headers → resubmits same auth → facilitator settles again (no nonce DB to check).

**Fix**:
1. Create `used_nonces` table: `(task_id, nonce, settled_at)`
2. Check nonce uniqueness before settlement
3. Set `validAfter` to current timestamp (not 0)

---

### C-PAY-04: Facilitator MITM / Domain Hijack

**Severity**: CRITICAL
**File**: `mcp_server/integrations/x402/sdk_client.py:76-78`

**Problem**: Facilitator URL loaded from env var with no certificate pinning. DNS hijack → attacker's server returns fake tx hashes → code trusts `data.get("success", bool(tx_hash))` → task marked complete with no on-chain settlement.

**Fix**:
1. Certificate pinning for facilitator endpoint
2. Validate tx hash on-chain (RPC `eth_getTransactionReceipt`) before trusting
3. Implement challenge-response health check

---

### C-PAY-05: Private Key Exposure in Tracebacks

**Severity**: CRITICAL
**File**: `mcp_server/integrations/x402/payment_dispatcher.py:287-301`, `sdk_client.py:799-802`

**Problem**: If `Account.from_key(pk)` throws (invalid key format), Python's traceback includes local variable `pk`. This appears in server logs, CloudWatch, Sentry.

**Fix**:
1. Wrap key operations in try/except with explicit `del pk`
2. Add traceback sanitization middleware
3. Use AWS KMS instead of raw key in memory

---

### C-PAY-06: Fee Calculation Integer Underflow

**Severity**: CRITICAL
**File**: `mcp_server/integrations/x402/payment_dispatcher.py:242-281`

**Problem**: If on-chain fee rate exceeds platform fee, `treasury_amount` goes negative → silently set to `Decimal("0")` (line 275). Fee is lost with only a warning log.

**Fix**: Fail-hard on negative treasury:
```python
if treasury_amount < Decimal("0"):
    raise ValueError(f"Treasury underflow: {treasury_amount}")
```

---

### C-BE-01: Hardcoded Wallet Addresses (Inconsistent)

**Severity**: CRITICAL
**File**: `mcp_server/api/h2a.py:55`, `mcp_server/integrations/x402/sdk_client.py:81-83`

**Problem**: Two DIFFERENT treasury addresses hardcoded as fallback defaults:
- `h2a.py:55`: `0xae07B067934975cF3DA0aa1D09cF373b0FED3661`
- `sdk_client.py:81`: `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad`

Fund routing bug waiting to happen.

**Fix**: Remove all hardcoded addresses. Require `EM_TREASURY_ADDRESS` env var (no fallback).

---

### C-BE-02: Admin Auth via Query Parameter

**Severity**: CRITICAL
**File**: `mcp_server/api/admin.py:42-106`

**Problem**: Admin key accepted from URL query param (line 79-82). Keys in URLs appear in server logs, proxy logs, browser history, Referer headers.

**Fix**: Remove query parameter auth entirely. Accept only `X-Admin-Key` header.

---

### C-BE-03: SQL Injection via `.ilike()`

**Severity**: CRITICAL
**File**: `mcp_server/api/admin.py:649`

**Problem**: User-supplied `search` parameter interpolated directly into `.ilike()` pattern:
```python
query = query.or_(f"title.ilike.%{search}%,instructions.ilike.%{search}%")
```

**Fix**: Escape special chars with `re.escape(search)` + add `max_length=100` to parameter.

---

## POSITIVE FINDINGS (What's Done Right)

| Area | Finding |
|------|---------|
| **Frontend XSS** | No `dangerouslySetInnerHTML` found anywhere. All dynamic content via React JSX. |
| **Supabase Keys** | Only anon key in frontend. Service key correctly backend-only. |
| **Wallet Keys** | No private keys in frontend code. Signing via Dynamic.xyz iframe. |
| **CI/CD** | CodeQL + Gitleaks + TruffleHog secret scanning. Dependency review on PRs. |
| **Production Deploy** | OIDC role assumption (deploy-prod.yml). Rollback on health check failure. |
| **CORS** | Properly allowlisted origins. No wildcard `*`. |
| **Rate Limiting** | Tiered rate limiting implemented (60-10K req/min by tier). |
| **Docker** | MCP server runs as non-root user `em`. Multi-stage builds. |
| **Auth Model** | Dual auth (API Key + ERC-8128 signature). Constant-time comparison. |
| **Dependencies** | No known CVEs in current package versions. |

---

## REMEDIATION PLAN

### Phase 0 — IMMEDIATE (before any real-money traffic)

| Task | Finding | Effort |
|------|---------|--------|
| Add nonce tracking table + validation | C-PAY-02, C-PAY-03 | 4h |
| Make settlement atomic (fail-hard on fee failure) | C-PAY-01 | 3h |
| On-chain tx verification after facilitator response | C-PAY-04, H-PAY-03 | 4h |
| Remove query param admin auth | C-BE-02 | 1h |
| Escape `.ilike()` search input | C-BE-03 | 30min |
| Fix hardcoded treasury address mismatch | C-BE-01 | 30min |
| Sanitize private key from tracebacks | C-PAY-05 | 2h |
| Fail-hard on negative treasury | C-PAY-06 | 30min |
| Add self-assignment guard at assignment time | H-PAY-02 | 2h |

**Total Phase 0: ~17.5 hours**

### Phase 1 — HIGH priority (within 1 sprint)

| Task | Finding | Effort |
|------|---------|--------|
| Add status validation on approval (task + submission + escrow) | H-BE-02 | 3h |
| Normalize wallet addresses (lowercase) in auth | H-BE-01 | 2h |
| Route A2A settlements through PaymentDispatcher | H-PAY-07 | 4h |
| Add Content Security Policy headers | M-FE-03 | 1h |
| Sanitize task instructions (DOMPurify) | M-FE-02 | 2h |
| Add escrow state machine constraints | H-PAY-05 | 4h |
| Use ROUND_CEILING for all payment amounts | H-PAY-06 | 2h |
| Remove hardcoded secrets from docker-compose | H-INFRA-01 | 1h |
| Reduce API key cache TTL + add max size | M-BE-01 | 2h |

**Total Phase 1: ~21 hours**

### Phase 2 — MEDIUM priority (within 2 sprints)

| Task | Finding | Effort |
|------|---------|--------|
| Migrate deploy.yml to OIDC | M-INFRA-03 | 2h |
| Complete RLS audit on all PII tables | M-INFRA-05, H-BE-04 | 4h |
| Add WebSocket auth + connection limits | M-INFRA-04 | 3h |
| Fix migration 031 naming conflict | M-INFRA-06 | 30min |
| Add rate limiting on approve/registration | M-PAY-07, M-BE-02 | 3h |
| Use Decimal instead of float for bounty | M-BE-03 | 2h |
| Add structured security event logging | M-BE-04 | 4h |
| Frontend: conditional console logging | M-FE misc | 1h |
| Frontend: disable source maps in prod | M-FE misc | 15min |
| Add file upload size validation | M-INFRA-07 | 1h |
| Certificate pinning for facilitator | C-PAY-04 (hardening) | 3h |

**Total Phase 2: ~24 hours**

---

## ARCHITECTURE RECOMMENDATIONS

### 1. Payment Settlement Redesign
Current flow: `sign auth → settle worker → settle fee (non-blocking)`.
Recommended: `validate state → sign both auths → settle both atomically → verify on-chain → mark complete`.

### 2. Nonce Management
Create `used_nonces` table with unique constraint on `(nonce, chain_id)`. Check before every settlement. This eliminates replay attacks entirely.

### 3. Facilitator Trust Boundary
Never trust facilitator responses blindly. Always verify tx on-chain via RPC before updating task status. Treat facilitator as untrusted relay, not authority.

### 4. Admin Auth Overhaul
Replace API key auth with short-lived JWT tokens issued after SIWE login. Implement role-based permissions (viewer, operator, admin). Remove query param auth.

---

## COMPARISON WITH PREVIOUS AUDIT (2026-02-18 H2A/A2A)

| Previous Finding | Status |
|------------------|--------|
| Settlement not atomic (h2a.py:643) | **STILL OPEN** → C-PAY-01 |
| No status validation on approve (h2a.py:567) | **STILL OPEN** → H-BE-02 |
| A2A approve bypasses PaymentDispatcher (task_manager.py:540) | **STILL OPEN** → H-PAY-07 |
| A2A cancel no refund (task_manager.py:448) | **STILL OPEN** |
| H2A payment flow incomplete (placeholder sigs) | **STILL OPEN** |
| Missing RLS on human_wallet | **STILL OPEN** → M-INFRA-05 |
| Migration 031 naming conflict | **STILL OPEN** → M-INFRA-06 |

All 5 P0 bugs from the previous audit remain unresolved.

---

**END OF REPORT**

*Generated by Claude Code parallel security audit (4 agents: backend, frontend, payments, infrastructure)*
*Next recommended review: 2026-03-18 or after Phase 0 fixes are deployed*
