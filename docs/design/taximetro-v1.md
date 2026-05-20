---
date: 2026-05-20
tags:
  - type/design
  - domain/dashboard
  - status/active
status: active
aliases:
  - Taxímetro v1 design spec
  - Taxi meter cinematic spec
related-files:
  - dashboard/src/components/TaximetroLive.tsx
  - dashboard/src/components/SettlementAnimation.tsx
  - dashboard/src/pages/TaskExecutionScene.tsx
  - dashboard/src/themes/demo-nyc.ts
---

# Taxímetro v1 — Design Spec (Phase 5.1)

> **Note**: this doc is the ASCII/text equivalent of the Figma mockup
> requested by master plan task 5.1. The components (5.2, 5.3, 5.5,
> 5.6) shipped first; this spec was written post-implementation to
> capture the design intent before Saul's visual review for the NYC
> demo. Treat it as the canonical visual reference — if the rendered
> component diverges from this spec, fix the component, not the spec.

## Goal

A monospace number ticking up as voucher frames land on the pay.sh
session — the cinematic centerpiece of the MoonPay NYC capture. Built
to be readable from 2m on a 4K monitor and unmistakable on B-roll
when reduced to 1080p for social cuts.

## Brand canonical

Strict black/white/zinc only per [[brand-canonical]]. No accent
colors. Anything blue, emerald, or yellow is a regression — stop
the capture, file a bug.

## Layout (ASCII reference)

```
+----------------------------------------------------------------+
|  Taxímetro · channel a3f9b21d…                  [ tick muted ] |
|                                                                |
|  $0.0875                                                       |
|                                                                |
|  17 vouchers · status live                       $0.0050/sec   |
|                                                                |
|  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ |
|  $0.0875                                            cap $0.20  |
+----------------------------------------------------------------+
```

When the session closes and settles:

```
+----------------------------------------------------------------+
|  Taxímetro · channel a3f9b21d…                  [ tick muted ] |
|                                                                |
|  $0.1734                                                       |
|                                                                |
|  342 vouchers · status settled                   $0.0050/sec   |
|                                                                |
|  █████████████████████████████████████████████████████████░░░ |
|  $0.1734                                            cap $0.20  |
|----------------------------------------------------------------|
|  SETTLED                                                        |
|  5tF9...a3c2 ← clickable to Solana Explorer / Surfpool Studio   |
+----------------------------------------------------------------+
```

## Typography scale

| Element | Class | Why |
|---------|-------|-----|
| Meter digits | `text-7xl font-bold tabular-nums` | Readable from 2m; tabular keeps columns stable as digits change |
| Sub-line ("vouchers · status …") | `text-sm text-zinc-700` | Tertiary info, never competes with the digits |
| Caption ("Taxímetro · channel …") | `text-xs uppercase tracking-widest text-zinc-600` | Identifies the meter without stealing focus |
| Cap label | `text-xs text-zinc-600` | Same weight as caption — both are metadata |
| Settlement label "SETTLED" | `font-semibold uppercase tracking-widest` | Cue moment — make it obvious without being loud |

The demo-day theme override at `dashboard/src/themes/demo-nyc.ts`
bumps the meter to `text-9xl` and tightens the sub-line for the 4K
capture — see that file for the full token set.

## Color tokens

```ts
background: '#ffffff'   // page + meter card
foreground: '#000000'   // digits + rule
muted:      '#71717a'   // zinc-500 (caption, sub-line)
subtle:     '#a1a1aa'   // zinc-400 (placeholder states)
faint:      '#e4e4e7'   // zinc-200 (progress bar track)
```

## Motion

Two tracks, choreographed by `useTaximetroStream`:

1. **Hard step on every voucher_accepted** — `cumulativeUsdc` jumps
   to the on-chain truth. No tween, no interpolation. The discrete
   tick is the dramatic beat we want on camera.
2. **Smooth extrapolation between vouchers** — when `ratePerSec > 0`,
   a rAF loop interpolates the displayed value forward from the last
   real frame at the declared rate. Bounded by `cap` so it never
   overshoots the ceiling. This kills dead air between SSE frames so
   the meter feels alive in the 400ms-1s gaps.

The progress bar transitions on `width` with `duration-150 ease-linear`
so it visibly slides with the meter rather than snapping.

## Audio cue (Phase 5.4 — wired)

A subtle `voucher-tick.mp3` plays on each voucher delta. Muted by
default; the toggle is the small `[ tick muted ] / [ tick on ]`
button in the upper-right of the meter card. Asset path:
`dashboard/public/audio/voucher-tick.mp3` — placeholder until the
sound designer ships the final file.

## Settlement reveal (Phase 5.6 — wired)

Lives below the meter inside `TaskExecutionScene`, owned by
`SettlementAnimation`. Animates the 87/13 split with a `txHash`
clickable to Solana Explorer (or Surfpool Studio in dev). The reveal
runs ~3s; the camera should hold for 6s to give the editor headroom.

## What this spec does **not** cover

- **`/demo/nyc` page composition** — see `dashboard/src/pages/NycDemoPage.tsx`
- **SSE event protocol** — see `dashboard/src/hooks/useTaximetroStream.ts`
- **Camera framing / shot list** — see [[nyc-demo-filming]]

## Visual review status

- Initial implementation: [[MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO]] phases 5.2 / 5.3 / 5.5 / 5.6 / 5.7 (committed)
- Brand-canonical compliance: enforced in code (`border-black bg-white text-black` in `TaskExecutionScene.tsx`)
- Saul sign-off: pending (HITL — post-2026-06-01 internal review with running build at `/demo/nyc`)
