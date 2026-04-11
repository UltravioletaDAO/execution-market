---
date: 2026-04-11
tags:
  - type/plan
  - domain/payments
  - domain/agents
  - domain/operations
  - priority/p0
status: active
related-files:
  - mcp_server/integrations/x402/payment_dispatcher.py
  - mcp_server/api/routers/tasks.py
  - mcp_server/api/reputation.py
  - mcp_server/verification/background_runner.py
  - mcp_server/verification/pipeline.py
  - dashboard/src/components/evidence/EvidenceUpload.tsx
  - dashboard/public/skill.md
---

# Master Plan: E2E Testing Bugs (2026-04-11)

## Origin

Full E2E test session: Claude agent (OWS wallet `0xe56D...`, Agent #41690 Base / #423 SKALE) → publish task on SKALE → worker applies → escrow lock → worker submits photo evidence → approve → release. Multiple failures discovered at every stage of the pipeline.

## Bug Summary

| # | Bug | Severity | Category |
|---|-----|----------|----------|
| B1 | SDK operator mismatch — SKALE defaults to wrong address | **P0** | Payment |
| B2 | SDK operator mismatch — Base defaults to legacy address | **P0** | Payment |
| B3 | Frontend doesn't extract EXIF GPS from gallery uploads | **P0** | Evidence |
| B4 | Ring 1 (PHOTINT) doesn't run for `arbiter_mode=manual` | **P1** | Verification |
| B5 | Ring 2 (Arbiter) doesn't run for `arbiter_mode=manual` | **P1** | Verification |
| B6 | Cancel API returns 409 for expired tasks with locked escrow | **P1** | Payment |
| B7 | No way to update payment_info after task is submitted | **P1** | Payment |
| B8 | Skill doesn't set `arbiter_mode` — defaults to manual | **P1** | Skill |
| B9 | Rating reverts on SKALE (self-feedback guard) | **P2** | Reputation |
| B10 | OWS shim ignores wallet_name (multi-wallet bug) | **P0** | SDK |

---

## Phase 1 — SDK Operator Fix (P0, blocks all SKALE+Base E2E)

### Task 1.1 — Fix SKALE default operator in SDK
- **File**: `z:/ultravioleta/dao/uvd-x402-sdk-python/src/uvd_x402_sdk/advanced_escrow.py:589`
- **Bug**: B1 — Hardcoded `0x28c23AE8f55aDe5Ea10a5353FC40418D0c1B3d33` (stale)
- **Fix**: Change to `0x43E46d4587fCCc382285C52012227555ed78D183` (production, matches CLAUDE.md + sdk_client.py + skill.md)
- **Validation**: `pytest -k "skale"` + manual authorize→release on SKALE testnet

### Task 1.2 — Fix Base default operator in SDK
- **File**: `z:/ultravioleta/dao/uvd-x402-sdk-python/src/uvd_x402_sdk/advanced_escrow.py:218`
- **Bug**: B2 — `BASE_MAINNET_CONTRACTS["operator"]` = `0xa06958D93135BEd7e43893897C0d9fA931EF051C` (legacy)
- **Fix**: Change to `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` (production Fase 5 operator)
- **Validation**: Golden Flow on Base

### Task 1.3 — Bump SDK version and publish
- **File**: `z:/ultravioleta/dao/uvd-x402-sdk-python/pyproject.toml`
- **Fix**: Bump to 0.23.0 (MINOR — breaking change for users relying on wrong defaults). Add changelog entry.
- **Validation**: `pip install -e . && python -c "from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient"`

### Task 1.4 — Fix OWS shim wallet_name bug
- **File**: `dashboard/public/scripts/ows_shim.py` (`OWSWallet.address` property)
- **Bug**: B10 — Returns first EVM address from `ows wallet list`, ignores `self.name`
- **Fix**: Parse output by Name: block, filter by `self.name` (patch already written in handoff, just apply)
- **Validation**: Test with 3 wallets in vault, verify each resolves to correct address

---

## Phase 2 — EXIF GPS Extraction (P0, evidence pipeline broken)

### Task 2.1 — Add client-side EXIF extraction for gallery uploads
- **File**: `dashboard/src/components/evidence/EvidenceUpload.tsx:220-287`
- **Bug**: B3 — Gallery handler reads file but never extracts EXIF GPS. Only manual GPSCapture used.
- **Fix**: Use `exif-js` or `exifr` library to extract GPS from gallery images BEFORE upload. If EXIF GPS found, auto-populate `currentGps`. If not, fall back to GPSCapture prompt.
- **Validation**: Upload iPhone gallery photo → GPS auto-extracted → backend receives coords → GPS check = 100%

### Task 2.2 — Add EXIF extraction fallback on backend
- **File**: `mcp_server/verification/pipeline.py:239-349` (`_run_gps_check`)
- **Bug**: B3 (defense-in-depth) — If frontend fails to extract EXIF, backend should download the image and try `exif_extractor.py`
- **Fix**: In Phase A `_run_gps_check`, if no GPS in evidence metadata AND evidence has a `fileUrl`, download image and run `extract_gps_from_image()` from `exif_extractor.py`
- **Validation**: Submit photo WITHOUT client-side GPS → backend extracts from EXIF → GPS check > 0%

### Task 2.3 — Install EXIF library in dashboard
- **File**: `dashboard/package.json`
- **Fix**: `npm install exifr` (lightweight, modern, TypeScript, ~15KB gzipped)
- **Validation**: `npm run build` passes

---

## Phase 3 — Ring 1/Ring 2 Activation (P1, verification invisible)

### Task 3.1 — Decouple Phase B from arbiter_mode
- **File**: `mcp_server/api/routers/workers.py:730-736`
- **Bug**: B4 — Phase B (which includes Ring 1 PHOTINT) only runs when `arbiter_enabled=True`
- **Fix**: ALWAYS launch Phase B for `physical_presence`, `location_based`, `verification` categories regardless of `arbiter_mode`. Ring 2 can remain gated by `arbiter_mode != manual`.
- **Validation**: Create task with default arbiter_mode → submit evidence → `ai_verification_result` is NOT null

### Task 3.2 — Ring 2 gating: keep but document
- **File**: `mcp_server/verification/background_runner.py:231`
- **Bug**: B5 — Ring 2 blocked for `arbiter_mode=manual`. This is BY DESIGN but poorly documented.
- **Fix**: No code change needed. Add clear comments explaining the gating logic. Ensure dashboard shows "Ring 2: Not requested (arbiter_mode=manual)" instead of empty.
- **Validation**: Dashboard shows explicit "not requested" message instead of null

### Task 3.3 — Dashboard: show Ring 1/Ring 2 status explicitly
- **File**: `dashboard/src/` — evidence review components (find specific file)
- **Bug**: B4/B5 — Dashboard shows nothing when Ring 1/2 didn't run. User sees blanks.
- **Fix**: Show explicit status messages:
  - Ring 1: "Running..." / "Complete: [results]" / "Not available (Phase B disabled)"
  - Ring 2: "Running..." / "Verdict: [pass/fail/inconclusive]" / "Not requested (arbiter_mode=manual)"
- **Validation**: Submit evidence on manual mode → dashboard shows "Ring 1: [result], Ring 2: Not requested"

### Task 3.4 — Skill: default to `arbiter_mode: "auto"` for physical tasks
- **File**: `dashboard/public/skill.md` — Step 2b task creation code
- **Bug**: B8 — Skill never sets `arbiter_mode`. Default `manual` means Ring 1+2 never run.
- **Fix**: In Step 2b example code, add `"arbiter_mode": "auto"` for `physical_presence` category. Add note: "For physical tasks, always set arbiter_mode to 'auto' or 'hybrid' to enable PHOTINT verification."
- **Validation**: Agent follows skill → task has `arbiter_mode=auto` → Ring 1+2 run

---

## Phase 4 — Payment Recovery (P1, funds stuck)

### Task 4.1 — Add "expired" to cancellable_statuses
- **File**: `mcp_server/api/routers/tasks.py:2473-2484`
- **Bug**: B6 — `cancellable_statuses = {"published"}` + conditional `"accepted"`. Missing `"expired"`.
- **Fix**: Add `"expired"` to `cancellable_statuses` when escrow exists. Cancel triggers refund via `refund_trustless_escrow()`.
- **Validation**: Create task → lock escrow → let it expire → `POST /tasks/{id}/cancel` → 200 + refund TX

### Task 4.2 — Add PATCH endpoint for escrow metadata
- **File**: `mcp_server/api/routers/tasks.py` (new endpoint)
- **Bug**: B7 — No way to update payment_info after task is submitted
- **Fix**: Add `PATCH /api/v1/tasks/{id}/escrow` (agent-only, ERC-8128 auth). Allows updating `payment_info` in `escrows.metadata` JSONB. Gated by: (1) caller is task owner, (2) escrow status is `deposited` or `authorized` (not released/refunded).
- **Validation**: Lock with wrong operator → worker submits → PATCH payment_info → approve → release succeeds

### Task 4.3 — Background job: retry failed refunds
- **File**: `mcp_server/jobs/task_expiration.py:50-90`
- **Bug**: B6 (defense) — If `_process_expired_task` fails to refund (wrong operator, facilitator down), it silently drops the task
- **Fix**: Add retry with exponential backoff (3 attempts). Log failures to `payment_events` table with `event_type="refund_failed"`. Add CloudWatch alarm for consecutive failures.
- **Validation**: Kill facilitator mock → task expires → retry 3x → logs failure → alert fires

---

## Phase 5 — Reputation Fix (P2)

### Task 5.1 — Make self-feedback preflight blocking
- **File**: `mcp_server/integrations/erc8004/direct_reputation.py:209-217`
- **Bug**: B9 — Preflight `ownerOf(agent_id)` check catches self-feedback but exception is non-blocking, so TX proceeds and reverts on-chain (wastes gas on non-SKALE chains)
- **Fix**: Make the self-feedback check BLOCKING. If `sender == ownerOf(worker_agent_id)`, return clear error: "Cannot rate: sender owns the worker's agent NFT (self-feedback)"
- **Validation**: Try to rate yourself → get clear error message → no on-chain revert

### Task 5.2 — Fix SKALE agent ID resolution in rating
- **File**: `mcp_server/api/reputation.py:806-819`
- **Bug**: B9 — Worker agent ID lookup only uses cached `erc8004_agent_id` for Base. For SKALE, on-chain lookup may return wrong owner.
- **Fix**: Add explicit wallet-level check: `if rater_wallet.lower() == worker_wallet.lower(): raise 403`. This catches self-feedback regardless of agent ID resolution.
- **Validation**: Rate worker on SKALE with different wallet → success. Rate self → 403.

---

## Phase 6 — Skill + Documentation Sync

### Task 6.1 — Skill: add `arbiter_mode: "auto"` to examples
- **File**: `dashboard/public/skill.md` — Step 2b
- **Fix**: All `physical_presence`, `location_based`, `verification` task examples include `"arbiter_mode": "auto"`. Add explanation.
- **Validation**: Diff check

### Task 6.2 — Skill: add operator override guidance
- **File**: `dashboard/public/skill.md` — Step 3
- **Fix**: After SDK fix (Phase 1), add note: "If you're using an older SDK version, explicitly pass operator address from the Contract Addresses table above."
- **Validation**: Diff check

### Task 6.3 — Bump skill version
- **File**: `dashboard/public/skill.md` frontmatter + changelog
- **Fix**: Bump to next MINOR (9.2.0 or next). Changelog: "arbiter_mode defaults, operator override guidance, EXIF extraction improvements"
- **Validation**: `head -3 dashboard/public/skill.md` shows new version

### Task 6.4 — Sync skill to backend
- **File**: `mcp_server/skills/SKILL.md`
- **Fix**: `cp dashboard/public/skill.md mcp_server/skills/SKILL.md`
- **Validation**: `diff dashboard/public/skill.md mcp_server/skills/SKILL.md` returns empty

---

## Execution Order

```
Phase 1 (P0, ~30 min) → SDK operator fix + OWS shim
  ↓
Phase 2 (P0, ~1 hr)   → EXIF GPS extraction (frontend + backend fallback)
  ↓
Phase 3 (P1, ~1 hr)   → Ring 1/2 activation + dashboard visibility
  ↓
Phase 4 (P1, ~1 hr)   → Payment recovery (cancel expired, PATCH escrow, retry)
  ↓
Phase 5 (P2, ~30 min) → Reputation self-feedback fix
  ↓
Phase 6 (P2, ~15 min) → Skill + docs sync
```

## Validation: Full E2E Re-test

After all phases: repeat the exact test from 2026-04-11:
1. Publish physical_presence task on SKALE (with `arbiter_mode: "auto"`)
2. Worker applies + agent assigns (correct operator auto-resolved by SDK)
3. Worker submits gallery photo → EXIF GPS extracted → GPS check passes
4. Ring 1 (PHOTINT) runs → `ai_verification_result` populated
5. Ring 2 (Arbiter) runs → `arbiter_grade` + `arbiter_summary` populated
6. Dashboard shows full verification pipeline
7. Agent approves → escrow releases → worker gets 87%
8. Agent rates worker → on-chain reputation recorded
9. If task expires before submission → cancel works → refund returned

**All 9 steps must pass. Zero silent failures.**
