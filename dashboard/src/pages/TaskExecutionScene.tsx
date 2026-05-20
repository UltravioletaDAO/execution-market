/**
 * TaskExecutionScene — the 4K-capture stage layout (Phase 5.5).
 *
 * One page, four moving parts, choreographed by the taxímetro stream:
 *
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  TASK TITLE                                  ROBOT STATUS │
 *   ├──────────────────────────┬──────────────────────────────┤
 *   │                          │                              │
 *   │         BARCODE          │       TAXÍMETRO LIVE         │
 *   │         (huge QR)        │         (big digits)         │
 *   │                          │                              │
 *   ├──────────────────────────┴──────────────────────────────┤
 *   │  SETTLEMENT PANEL (only when stream.status === 'settled')│
 *   └─────────────────────────────────────────────────────────┘
 *
 * The robot status text is derived from `useTaximetroStream` — single
 * source of truth, no parallel state machine. When `settlement_complete`
 * lands, the SettlementAnimation overlays the lower row with the dramatic
 * 87/13 reveal (Phase 5.6).
 *
 * Optimized for 4K camera capture: text-9xl tabular-nums on the meter,
 * a 480px monochrome QR (printable + scannable from 2m), high-contrast
 * B&W per brand-canonical. No motion design beyond what serves the demo.
 *
 * This page is presentational — the caller (Phase 5.7 /demo/nyc) wires
 * the channelId + barcodeValue + totals. Mounting it directly with URL
 * params is fine for ad-hoc rehearsal but not the production path.
 */

import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { SettlementAnimation, type SettlementNetwork } from '../components/SettlementAnimation'
import { TaximetroLive } from '../components/TaximetroLive'
import { useTaximetroStream } from '../hooks/useTaximetroStream'

export interface TaskExecutionSceneProps {
  /** SSE channel to subscribe to (from pay.sh / EM session). */
  channelId: string | null | undefined
  /** Value to encode in the on-stage QR code (task ID, deep link, JSON, ...). */
  barcodeValue: string
  /** Optional headline at the top of the scene. */
  taskTitle?: string
  /** Hard cap (USDC) for the taxímetro. */
  cap?: number
  /** Fill-rate (USDC/sec) for between-frame extrapolation. */
  ratePerSec?: number
  /** Network for the explorer URL in settlement. */
  network?: SettlementNetwork
  /** Override the explorer base URL (Surfpool studio etc.). */
  explorerBaseUrl?: string
  /** Optional callback when the settlement animation finishes (Phase 5.7 hook). */
  onSettled?: () => void
}

type RobotPhase = 'awaiting' | 'connecting' | 'executing' | 'finalizing' | 'settled' | 'error'

function phaseFromStatus(status: ReturnType<typeof useTaximetroStream>['status']): RobotPhase {
  switch (status) {
    case 'idle':
      return 'awaiting'
    case 'connecting':
      return 'connecting'
    case 'live':
      return 'executing'
    case 'closed':
      return 'finalizing'
    case 'settled':
      return 'settled'
    case 'error':
      return 'error'
  }
}

const PHASE_COPY: Record<RobotPhase, { label: string; sub: string }> = {
  awaiting: { label: 'Awaiting scan', sub: 'Robot, point camera at the code' },
  connecting: { label: 'Opening session', sub: 'pay.sh negotiating channel' },
  executing: { label: 'Executing', sub: 'Voucher signatures landing on-chain' },
  finalizing: { label: 'Session closed', sub: 'Settling final cumulative on-chain' },
  settled: { label: 'Settled', sub: 'Payment split and refund complete' },
  error: { label: 'Relay error', sub: 'Reconnecting — value already escrowed' },
}

function useQrDataUrl(value: string, size = 480): string | null {
  const [dataUrl, setDataUrl] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    if (!value) {
      setDataUrl(null)
      return
    }
    QRCode.toDataURL(value, {
      width: size,
      margin: 1,
      // Strict B&W per brand-canonical. No accent color.
      color: { dark: '#000000', light: '#ffffff' },
      errorCorrectionLevel: 'M',
    })
      .then((url) => {
        if (!cancelled) setDataUrl(url)
      })
      .catch(() => {
        if (!cancelled) setDataUrl(null)
      })
    return () => {
      cancelled = true
    }
  }, [value, size])
  return dataUrl
}

export function TaskExecutionScene({
  channelId,
  barcodeValue,
  taskTitle,
  cap,
  ratePerSec,
  network = 'mainnet-beta',
  explorerBaseUrl,
  onSettled,
}: TaskExecutionSceneProps) {
  const stream = useTaximetroStream(channelId, { enabled: true })
  const phase = phaseFromStatus(stream.status)
  const phaseCopy = PHASE_COPY[phase]
  const qr = useQrDataUrl(barcodeValue, 480)

  // The settlement overlay needs the final total. Prefer the cumulative
  // off the stream — that's the on-chain truth — and fall back to the
  // cap only if the stream never produced a frame (degenerate demo case).
  const finalTotal =
    stream.cumulativeUsdc > 0 ? stream.cumulativeUsdc : typeof cap === 'number' ? cap : 0

  return (
    <div className="min-h-screen bg-white font-mono text-black">
      <header className="border-b-2 border-black px-10 py-6">
        <div className="flex items-baseline justify-between gap-8">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-zinc-600">
              Execution Market · Live
            </div>
            <h1 className="mt-1 text-3xl font-bold leading-tight md:text-4xl">
              {taskTitle ?? 'Robot Execution Scene'}
            </h1>
          </div>
          <div className="text-right">
            <div className="text-xs uppercase tracking-[0.3em] text-zinc-600">
              Robot status
            </div>
            <div className="mt-1 text-2xl font-bold uppercase tracking-wider md:text-3xl">
              {phaseCopy.label}
            </div>
            <div className="mt-1 text-sm text-zinc-600">{phaseCopy.sub}</div>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-1 gap-10 px-10 py-10 lg:grid-cols-2">
        <section className="flex flex-col items-center justify-center">
          <div className="mb-3 text-xs uppercase tracking-[0.3em] text-zinc-600">
            Scan code
          </div>
          <div className="rounded-lg border-2 border-black bg-white p-6">
            {qr ? (
              <img
                src={qr}
                alt="Task barcode"
                width={480}
                height={480}
                className="block h-[480px] w-[480px]"
              />
            ) : (
              <div className="flex h-[480px] w-[480px] items-center justify-center text-zinc-400">
                Encoding…
              </div>
            )}
          </div>
          <div className="mt-3 max-w-[480px] break-all text-center text-xs text-zinc-500">
            {barcodeValue}
          </div>
        </section>

        <section className="flex flex-col justify-center">
          <TaximetroLive
            channelId={channelId}
            cap={cap}
            ratePerSec={ratePerSec}
            enabled={true}
          />
          <div className="mt-6 border-t border-black pt-4 text-sm text-zinc-700">
            <div className="flex items-baseline justify-between">
              <span className="uppercase tracking-widest text-zinc-600">Channel</span>
              <span className="font-mono">{channelId ?? '—'}</span>
            </div>
            <div className="mt-1 flex items-baseline justify-between">
              <span className="uppercase tracking-widest text-zinc-600">Network</span>
              <span className="font-mono">{network}</span>
            </div>
          </div>
        </section>
      </main>

      {stream.status === 'settled' && stream.settlementTxHash && (
        <section className="border-t-2 border-black px-10 py-10">
          <SettlementAnimation
            txHash={stream.settlementTxHash}
            totalUsdc={finalTotal}
            network={network}
            explorerBaseUrl={explorerBaseUrl}
            onComplete={onSettled}
          />
        </section>
      )}
    </div>
  )
}

export default TaskExecutionScene
