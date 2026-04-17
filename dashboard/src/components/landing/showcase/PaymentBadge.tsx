/**
 * PaymentBadge — price anchor displayed on every Proof Wall card.
 *
 * Roboto Mono, monochrome. Format `$0.25` (no cents, no sats). Subtitle
 * `USDC · BASE · 2h ago` in 10px uppercase. Optional price-reveal animation
 * on first render (digit-roll), gated by reduced-motion.
 */

import { memo, useEffect, useState } from 'react'

interface PaymentBadgeProps {
  amountUsd: number
  token: string | null
  network: string | null
  paidAt: string
  animate?: boolean
}

function formatPrice(amount: number): string {
  if (!Number.isFinite(amount)) return '$0'
  // Show up to 2 decimals but drop trailing zeros — $0.25, $1.1, $12.
  return `$${amount.toFixed(2).replace(/\.?0+$/, '')}`
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (!Number.isFinite(then)) return ''
  const diffMs = Date.now() - then
  const diffSec = Math.max(0, Math.round(diffMs / 1000))
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = Math.round(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.round(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  const diffD = Math.round(diffH / 24)
  if (diffD < 30) return `${diffD}d ago`
  const diffMo = Math.round(diffD / 30)
  return `${diffMo}mo ago`
}

export const PaymentBadge = memo(function PaymentBadge({
  amountUsd,
  token,
  network,
  paidAt,
  animate = false,
}: PaymentBadgeProps) {
  const target = formatPrice(amountUsd)
  const [display, setDisplay] = useState<string>(animate ? '$0' : target)

  useEffect(() => {
    if (!animate) {
      setDisplay(target)
      return
    }
    // Digit-roll count-up over ~400ms, 24fps (~10 frames).
    const startAt = performance.now()
    const durationMs = 400
    let raf = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - startAt) / durationMs)
      const eased = 1 - Math.pow(1 - t, 3) // easeOutCubic
      const value = amountUsd * eased
      setDisplay(formatPrice(value))
      if (t < 1) raf = requestAnimationFrame(tick)
      else setDisplay(target)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [amountUsd, animate, target])

  const subtitle = [token, network?.toUpperCase(), formatRelativeTime(paidAt)]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="flex flex-col" data-testid="payment-badge">
      <span
        className="font-mono text-3xl sm:text-4xl font-semibold tracking-tight text-slate-900 dark:text-white tabular-nums"
        aria-label={`Paid ${target}`}
      >
        {display}
      </span>
      {subtitle && (
        <span className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-slate-500 dark:text-slate-400">
          {subtitle}
        </span>
      )}
    </div>
  )
})
