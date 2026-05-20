/**
 * TaximetroLive — the cinematic centerpiece of the demo (Phase 5.2).
 *
 * One big monospace number ticking up as voucher frames land. Strict
 * black-and-white per the canonical brand (no emerald, no blue, no
 * accent colors — those are drift). Designed to be readable from 2m
 * away on a 4K camera capture: huge digits, high contrast, tabular
 * numerals so the columns don't shimmy as values change.
 *
 * Two animation tracks:
 *   1. Discrete tick on each `voucher_accepted` (hard step, cinematic).
 *   2. Optional smooth extrapolation between vouchers using `ratePerSec`
 *      — gives the meter a "running" feel between RPC frames so it
 *      doesn't sit dead during the ~400ms-1s gaps. Pure rAF, no deps.
 *
 * The component owns the stream subscription. Callers that already
 * have stream state can use the lower-level `useTaximetroStream` hook
 * directly and render their own UI.
 */

import { useEffect, useRef, useState } from 'react'
import { useTaximetroStream } from '../hooks/useTaximetroStream'

interface Props {
  channelId: string | null | undefined
  /** Upper bound (USDC) for the meter. Renders the cap below the live digit. */
  cap?: number
  /**
   * Optional fill-rate (USDC/sec) used for smooth extrapolation between
   * voucher frames. When unset, the meter only updates on real frames.
   */
  ratePerSec?: number
  /** When false, the stream is not opened. Useful for stage cue control. */
  enabled?: boolean
}

function formatUsdc(value: number): string {
  // Six-decimal USDC, but we cap display at 4 to keep the number readable.
  // Pad to a stable width so digits don't jump around as the meter ticks.
  return value.toFixed(4)
}

export function TaximetroLive({ channelId, cap, ratePerSec, enabled = true }: Props) {
  const { cumulativeUsdc, voucherCount, status, settlementTxHash, lastEvent } =
    useTaximetroStream(channelId, { enabled })

  // Smooth extrapolation: if a ratePerSec is provided, we tick the
  // displayed number forward between real frames so the meter feels
  // alive. We never display *more* than `cap` — overshoot would lie
  // about the cost ceiling.
  const [displayUsdc, setDisplayUsdc] = useState(cumulativeUsdc)
  const baseRef = useRef({ value: cumulativeUsdc, at: performance.now() })

  useEffect(() => {
    baseRef.current = { value: cumulativeUsdc, at: performance.now() }
    setDisplayUsdc(cumulativeUsdc)
  }, [cumulativeUsdc])

  useEffect(() => {
    if (!ratePerSec || ratePerSec <= 0) return
    if (status !== 'live') return
    let frame = 0
    function tick() {
      const elapsed = (performance.now() - baseRef.current.at) / 1000
      const extrapolated = baseRef.current.value + elapsed * (ratePerSec ?? 0)
      const ceil = typeof cap === 'number' ? Math.min(extrapolated, cap) : extrapolated
      setDisplayUsdc(ceil)
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [ratePerSec, status, cap])

  const capPct =
    typeof cap === 'number' && cap > 0
      ? Math.min(100, (displayUsdc / cap) * 100)
      : null

  return (
    <div className="rounded-lg border border-black bg-white p-8 font-mono text-black">
      <div className="mb-2 text-xs uppercase tracking-widest text-zinc-600">
        Taxímetro · channel {channelId ? channelId.slice(0, 8) + '…' : '—'}
      </div>

      <div
        className="text-7xl font-bold leading-none tabular-nums"
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        ${formatUsdc(displayUsdc)}
      </div>

      <div className="mt-2 flex items-baseline justify-between text-sm text-zinc-700">
        <span>
          {voucherCount} vouchers · status {status}
        </span>
        {ratePerSec ? (
          <span>${ratePerSec.toFixed(4)}/sec</span>
        ) : (
          <span className="text-zinc-400">no rate</span>
        )}
      </div>

      {capPct !== null && (
        <div className="mt-4">
          <div className="h-2 w-full overflow-hidden rounded bg-zinc-200">
            <div
              className="h-full bg-black transition-[width] duration-150 ease-linear"
              style={{ width: `${capPct}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-xs text-zinc-600">
            <span>${formatUsdc(displayUsdc)}</span>
            <span>cap ${cap?.toFixed(4)}</span>
          </div>
        </div>
      )}

      {status === 'settled' && settlementTxHash && (
        <div className="mt-4 border-t border-black pt-3 text-xs">
          <div className="font-semibold uppercase tracking-widest text-zinc-700">
            Settled
          </div>
          <div className="mt-1 break-all text-zinc-800">{settlementTxHash}</div>
        </div>
      )}

      {status === 'error' && lastEvent?.type === 'error' && (
        <div className="mt-4 border-t border-black pt-3 text-xs text-zinc-700">
          relay error · reconnecting
        </div>
      )}
    </div>
  )
}

export default TaximetroLive
