---
date: 2026-03-27
tags:
  - type/plan
  - domain/payments
  - domain/infrastructure
status: active
---

# Master Plan: Multichain Hardcode Audit — Remove "base" Defaults

**Created:** 2026-03-27
**Priority:** P0-P2 mix
**Context:** SKALE integration (10th network) exposed systemic hardcoded "base" defaults throughout the codebase. Explorer links, payment status, reputation TXs all break on non-Base networks.

## Already Fixed (2026-03-27)

- [x] `useTaskPayment.ts` — `buildFromTaskFallback()` now reads `task.payment_network`
- [x] `useTaskPayment.ts` — `normalizeNetwork()` maps all 9 EVM chain IDs
- [x] `PaymentStatus.tsx` — "BaseScan" tooltip is now dynamic

## P0 — User-Facing Bugs

- [ ] **em-mobile `task/[id].tsx` lines 899, 941** — Reputation TX links hardcoded to `"base"`. Should use `task.payment_network`.
- [ ] **dashboard `FeedbackPage.tsx` line 70** — Explorers map missing monad + skale. Falls back to Base.
- [ ] **dashboard `blockchain.ts` NetworkId type** — Missing `'skale'` in union type.

## P1 — Data Integrity

- [ ] **`mcp_server/main.py` lines 1024-1043** — `/api/v1/x402/networks` endpoint missing "skale" in mainnets list.
- [ ] **`mcp_server/jobs/fee_sweep.py` lines 24-33** — `SWEEP_NETWORKS` missing "skale". Platform fees on SKALE won't be collected.
- [ ] **dashboard `TaskFeedCard.tsx`** — ~4 instances of `|| 'base'` fallback.
- [ ] **dashboard `TaskLifecycleTimeline.tsx` lines 311, 320** — `|| 'base'` fallback.
- [ ] **dashboard `TaskDetailModal.tsx` lines 163, 208, 252** — `|| 'base'` fallback.
- [ ] **dashboard `TransactionTimeline.tsx` line 146** — `|| 'base'` fallback.
- [ ] **dashboard `TaskDetailPanel.tsx` line 261** — `|| 'base'` fallback.
- [ ] **dashboard `EarningsPage.tsx` line 49** — `|| 'base'` fallback.
- [ ] **dashboard `reputation.ts` line 291** — `|| 'base'` fallback.
- [ ] **dashboard `RatingsHistory.tsx` line 247** — Hardcoded `network="base"` for `TxLink`.

## P2 — Config/Cosmetic

- [ ] **em-mobile `wagmi.ts` line 16** — `supportedChains` missing SKALE chain definition.
- [ ] **docs-site** — Multiple files say "15 networks", "9 networks", "8 EVM" — update all to "10 mainnets + 6 testnets".
- [ ] **landing `styles.css` line 356** — Comment says "17 mainnets" — outdated.

## Fix Strategy

The pattern `task.payment_network || 'base'` is the root cause. The correct fix for most of these is NOT to change the fallback to 'skale' — it's to ensure `payment_network` is always populated from the task data. The `|| 'base'` is a safety net for old tasks that predate multichain.

For new code: never use `|| 'base'` — require the network to be explicitly set.
