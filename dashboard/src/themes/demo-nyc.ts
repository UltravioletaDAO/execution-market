/**
 * demo-nyc theme tokens (Phase 5.8).
 *
 * The demo at MoonPay NYC needs a stricter visual envelope than the rest
 * of the app: pure brand-canonical (black, white, zinc grays), a single
 * monospace family, oversized typography sized for 4K capture from 2m,
 * and an EM + MoonPay co-branded header. This module exports those
 * tokens as plain constants so they compose with the existing Tailwind
 * classes already used in `NycDemoPage` and `TaskExecutionScene` — no
 * theme provider, no context, no runtime swap. The override is opt-in:
 * pages that want the demo look import from here, everything else keeps
 * its current styling.
 *
 * Sign-off scope (Saul, post-2026-06-01 internal review):
 *   - the actual MoonPay logo asset (path placeholder until reviewed)
 *   - the exact co-branding ratio (EM left / divider / MoonPay right)
 *
 * Out of scope:
 *   - color drift (anything that isn't black/white/zinc — see memory
 *     `brand-canonical`). The palette is frozen; do not extend it.
 *   - alternate fonts. Monospace only.
 */

export const DEMO_NYC_PALETTE = {
  background: '#ffffff',
  foreground: '#000000',
  rule: '#000000',
  muted: '#71717a', // zinc-500
  subtle: '#a1a1aa', // zinc-400
  faint: '#e4e4e7', // zinc-200
} as const

/**
 * Typography scale tuned for the 4K capture. Sizes increase past what
 * the regular dashboard uses because the camera frames the monitor at
 * roughly 1:1 pixel ratio from ~2m — anything below text-7xl on the
 * meter shimmers when re-encoded for the cut.
 */
export const DEMO_NYC_TYPOGRAPHY = {
  fontFamily: 'font-mono',
  meter: 'text-9xl font-bold leading-none tabular-nums',
  meterSub: 'text-lg uppercase tracking-widest text-zinc-600',
  titleXL: 'text-4xl font-bold md:text-5xl',
  title: 'text-3xl font-bold md:text-4xl',
  body: 'text-base text-zinc-700',
  caption: 'text-xs uppercase tracking-[0.3em] text-zinc-600',
} as const

export const DEMO_NYC_LAYOUT = {
  page: 'min-h-screen bg-white font-mono text-black',
  pageHeader: 'border-b-2 border-black px-10 py-6',
  pageSection: 'px-10 py-10',
  card: 'rounded-lg border-2 border-black bg-white p-8',
} as const

/**
 * Co-branded header asset map. Logos live in `dashboard/public/brand/`
 * to keep them out of the bundle and lazy-loadable from CDN. The
 * MoonPay mark is a placeholder until Saul confirms the file with
 * MoonPay BD post-2026-06-01 (per master plan task 5.8). The EM
 * wordmark is the existing canonical asset.
 *
 * If the MoonPay logo is not yet committed at the placeholder path,
 * the header should fall back to a text label "× MoonPay" so the
 * demo never ships a broken image.
 */
export const DEMO_NYC_BRAND = {
  emLogoPath: '/brand/em-wordmark.svg',
  moonpayLogoPath: '/brand/moonpay-wordmark.svg',
  divider: '×',
  fallback: {
    emLabel: 'Execution Market',
    moonpayLabel: 'MoonPay',
  },
} as const

/**
 * Composed class helpers — keep all the cinematic-mode strings in one
 * place so a future tweak doesn't drift across `NycDemoPage` and
 * `TaskExecutionScene`.
 */
export const demoNycClasses = {
  meterContainer: `${DEMO_NYC_LAYOUT.card} ${DEMO_NYC_TYPOGRAPHY.fontFamily}`,
  meterDigits: DEMO_NYC_TYPOGRAPHY.meter,
  meterCaption: DEMO_NYC_TYPOGRAPHY.meterSub,
  pageRoot: DEMO_NYC_LAYOUT.page,
  pageHeader: DEMO_NYC_LAYOUT.pageHeader,
  pageHeading: DEMO_NYC_TYPOGRAPHY.titleXL,
  pageCaption: DEMO_NYC_TYPOGRAPHY.caption,
} as const

export type DemoNycPalette = typeof DEMO_NYC_PALETTE
export type DemoNycTypography = typeof DEMO_NYC_TYPOGRAPHY
export type DemoNycLayout = typeof DEMO_NYC_LAYOUT
export type DemoNycBrand = typeof DEMO_NYC_BRAND
