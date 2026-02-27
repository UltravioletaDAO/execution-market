---
date: 2026-02-26
tags:
  - type/moc
  - domain/security
status: active
aliases:
  - Security MOC
  - Security & Compliance
  - Fraud Detection
---

# Security & Compliance — Map of Content

> Authentication, authorization, fraud detection, evidence verification, and secrets management.
> Everything that keeps the platform safe and trustworthy.

---

## Authentication

[[authentication]] — Four auth methods coexist in Execution Market:

| Method | Used By | How It Works |
|--------|---------|--------------|
| **Supabase Auth** | Workers (dashboard) | Anonymous sessions. Worker opens dashboard, gets an anonymous Supabase session. Wallet linked via `link_wallet_to_session()` RPC. |
| **ERC-8128 wallet-based auth** | AI agents | Signed HTTP requests. Agent signs a message with its wallet key, server verifies against ERC-8004 registry. Implemented in `api/agent_auth.py`. |
| **OAuth** (Google, GitHub) | Workers (dashboard) | Social login for easier onboarding. Supabase handles the OAuth flow. Wallet still required for payments. |
| **API keys** | Legacy agents | **Deprecated.** Replaced by ERC-8128. Still accepted but not issued to new agents. |

### Key Files

| File | Purpose |
|------|---------|
| `mcp_server/api/agent_auth.py` | ERC-8128 signature verification, JWT validation |
| `mcp_server/api/h2a.py` | Human-to-Agent auth flow (Supabase JWT + wallet) |
| `dashboard/src/context/AuthContext.tsx` | Client-side auth state, anonymous session management |
| `dashboard/src/hooks/useProfileUpdate.ts` | Profile update with executor ID resolution |

---

## Authorization

[[rls-policies]] — Supabase Row-Level Security enforces data boundaries:

| Table | Policy | Notes |
|-------|--------|-------|
| `executors` | Own profile only (`user_id = auth.uid()`) | Workers can read/update their own profile. Published tasks visible to all. |
| `submissions` | Requires `executor.user_id = auth.uid()` | **SILENT failure if not linked!** INSERT returns 0 rows with no error when auth session is not linked to executor. |
| `tasks` | SELECT: all published tasks visible. INSERT/UPDATE: publisher only. | `human_wallet` is PII — exposed via tasks SELECT (see Known Issues). |
| `platform_config` | Readable by all, writable by admins only | Feature flags, payment mode, fee percentage. |
| `disputes` | Participants only | Only task publisher and executor can view/create disputes. |

### Admin Access

- Admin endpoints protected by `X-Admin-Key` header
- Key stored in AWS Secrets Manager, injected via ECS task definition
- Endpoints: `POST /admin/fees/sweep`, `GET /admin/fees/accrued`, `POST /admin/config/*`

---

## Secret Management

[[aws-secrets-manager]] — Production secrets live in AWS Secrets Manager. **NEVER show private keys in logs or terminal output.**

| Secret | AWS SM Path | Used By |
|--------|-------------|---------|
| Platform wallet key | `em/x402:PRIVATE_KEY` | ECS MCP server — signs settlements |
| QuikNode Base RPC | `em/x402:X402_RPC_URL` | ECS MCP server — private RPC |
| Supabase JWT secret | `em/supabase-jwt:SUPABASE_JWT_SECRET` | H2A publisher auth verification |
| Test worker key | `em/test-worker:private_key` | Golden Flow E2E — worker-side operations |
| KK swarm mnemonic | `kk/swarm-seed` | HD wallet derivation for 24 KK agents |

### Rules

- **AWS SM for production**: ECS task definitions use `valueFrom` ARN pointers (NOT plaintext `value`)
- **`.env.local` for local dev**: Never committed, in `.gitignore`
- **`.env.example` in repo**: Template with placeholder values only (`YOUR_SECRET_HERE`)
- **Streaming safety**: User is ALWAYS on stream. Never `cat .env`, never `echo $SECRET`. Use `echo "VAR is ${VAR:+set}"` to verify existence.
- **ECS task def secrets checklist**: When adding features that need env vars, ALWAYS verify they are in the ECS task definition. Missing secrets cause silent 500 errors.

---

## Fraud Detection

[[fraud-detection]] — Multi-layer fraud prevention for task submissions:

| Layer | What It Catches |
|-------|-----------------|
| **GPS antispoofing** | Fake GPS coordinates (emulator detection, impossible speed, coordinate clustering) |
| **Timestamp validation** | Submissions outside deadline window, timezone manipulation |
| **Image tampering** | Modified EXIF data, inconsistent metadata, Photoshop signatures |
| **Duplicate detection** | Hash-based comparison across submissions (same evidence reused) |
| **Behavioral analysis** | Suspicious patterns: too-fast completion, identical submissions, unusual acceptance rates |
| **AI content detection** | AI-generated photos/text in evidence (GenAI fingerprint detection) |

### Source Files

| File | Purpose |
|------|---------|
| `mcp_server/security/fraud_detection.py` | Main fraud detection orchestrator |
| `mcp_server/security/gps_antispoofing.py` | GPS coordinate validation and spoofing detection |
| `mcp_server/security/image_analysis.py` | EXIF analysis, tampering detection |
| `mcp_server/security/behavioral.py` | Behavioral pattern analysis |
| `mcp_server/security/rate_limiter.py` | Per-IP and per-agent rate limiting |

---

## Evidence Verification

Verification pipeline in `mcp_server/verification/checks/` — modular check system:

| Check | File | What It Validates |
|-------|------|-------------------|
| **Geolocation** | `gps.py` | Submission GPS vs task location. Distance threshold based on task category. |
| **Timestamp** | `timestamp.py` | Submission time vs task deadline. Rejects late submissions. |
| **Tampering** | `tampering.py` | EXIF signature verification. Detects modified/stripped metadata. |
| **Duplicate** | `duplicate.py` | Hash-based comparison against all previous submissions for the same task. |
| **Photo Source** | `photo_source.py` | Source analysis — camera vs screenshot vs download vs AI-generated. |
| **GenAI** | `genai.py` | AI-generated content detection. Flags synthetic images/text. |

### Pipeline Flow

```
Submission uploaded → S3/CloudFront
    → GPS check (if location-bound task)
    → Timestamp check (always)
    → Duplicate check (always)
    → Tampering check (if photo evidence)
    → Photo source check (if photo evidence)
    → GenAI check (if enabled)
    → Aggregate score → PASS / FAIL / MANUAL_REVIEW
```

### Evidence Attestation

- [[chainwitness]] integration for high-value tasks
- On-chain proof-of-existence for submitted evidence
- See [[moc-integrations]] for ChainWitness details

---

## Rate Limiting

| Scope | Limit | Implementation |
|-------|-------|----------------|
| Per-IP | Configurable requests/minute | `security/rate_limiter.py` |
| Per-agent | Configurable tasks/hour | `security/rate_limiter.py` |
| Per-worker | Configurable submissions/hour | `security/rate_limiter.py` |

### Planned: [[turnstile]]

- Cloudflare Turnstile integration for bot protection
- Target: task creation and worker registration endpoints
- See [[moc-integrations]] for Turnstile integration plan

---

## Known Issues

| Issue | Severity | Details |
|-------|----------|---------|
| **RLS silent failure** | HIGH | `submissions` INSERT returns 0 rows (no error) when `executor.user_id != auth.uid()`. Worker must be linked to the anonymous session before submitting. `SubmissionForm.tsx` now uses `submitWork()` which handles this with proper error messages. |
| **`human_wallet` PII exposure** | MEDIUM | `human_wallet` field exposed via `tasks` SELECT policy. Migration 035 adds H2A-specific RLS to restrict access. |
| **API keys still accepted** | LOW | Deprecated auth method. Still functional but not issued to new agents. Should be sunset after ERC-8128 adoption is complete. |

---

## Test Coverage

| Marker | Tests | What It Covers |
|--------|-------|----------------|
| `security` | 61 | Fraud detection, GPS antispoofing, image analysis |
| `h2a` | 31 | Human-to-Agent auth flows, JWT validation |
| `agent_executor` | 46 | Agent auth, ERC-8128 signature verification |

See [[moc-testing]] for the full test profile reference.

---

## Source Files

| File | Purpose |
|------|---------|
| `mcp_server/api/agent_auth.py` | ERC-8128 wallet-based authentication for AI agents |
| `mcp_server/security/fraud_detection.py` | Fraud detection orchestrator |
| `mcp_server/security/gps_antispoofing.py` | GPS coordinate validation and spoofing detection |
| `mcp_server/security/image_analysis.py` | EXIF analysis, tampering detection |
| `mcp_server/security/behavioral.py` | Behavioral pattern analysis |
| `mcp_server/security/rate_limiter.py` | Per-IP and per-agent rate limiting |
| `mcp_server/verification/checks/gps.py` | Geolocation verification check |
| `mcp_server/verification/checks/timestamp.py` | Timestamp verification check |
| `mcp_server/verification/checks/tampering.py` | EXIF tampering verification check |
| `mcp_server/verification/checks/duplicate.py` | Duplicate submission detection |
| `mcp_server/verification/checks/photo_source.py` | Photo source analysis |
| `mcp_server/verification/checks/genai.py` | AI-generated content detection |
| `mcp_server/verification/attestation.py` | ChainWitness attestation integration |

---

## Documentation

| Doc | Location |
|-----|----------|
| [[SECURITY_AUDIT]] | `docs/reports/SECURITY_AUDIT_*.md` — Security audit reports |
| [[TRUSTLESSNESS_AUDIT_REPORT]] | `docs/reports/TRUSTLESSNESS_AUDIT_REPORT.md` — Fund safety and escrow invariants |
| [[AUDIT_H2A]] | `docs/reports/AUDIT_H2A_2026-02-18.md` — H2A auth flow audit |
| [[AUDIT_AGENT_EXECUTOR]] | `docs/reports/AUDIT_AGENT_EXECUTOR_2026-02-18.md` — Agent executor auth audit |

---

## Cross-Links

- [[moc-identity]] — ERC-8128 authentication, ERC-8004 agent identity verification
- [[moc-infrastructure]] — AWS Secrets Manager, ECS task definition secrets, CloudFront for evidence CDN
- [[moc-business]] — Evidence verification pipeline feeds into task approval/rejection decisions
- [[moc-integrations]] — ChainWitness for evidence notarization, Turnstile for bot protection
