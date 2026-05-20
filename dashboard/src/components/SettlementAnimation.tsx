/**
 * SettlementAnimation — the dramatic close (Phase 5.6).
 *
 * Renders for ~3s after `settlement_complete` lands. Three beats:
 *
 *   beat 1 (0.0–0.6s)  total amount counts up from 0 → final
 *   beat 2 (0.6–1.6s)  split bar fills, worker (87%) and treasury (13%)
 *                      numbers count up to their share
 *   beat 3 (1.6–3.0s)  txHash reveals with link to the Solana explorer
 *
 * The canonical fee split is 13% (treasury) / 87% (worker), per
 * CLAUDE.md "credit card convention". Numbers are derived live from
 * the totalUsdc prop so the animation can't drift from the on-chain
 * truth.
 *
 * Strict B&W. No green confetti, no accent colors — the demo is
 * monochrome cinematic on purpose (per brand-canonical memory).
 *
 * `network` picks the explorer URL: mainnet-beta, devnet, or a local
 * Surfpool node (which mounts the official Solana explorer locally,
 * usually on port 8899). Caller is expected to pass the env it ran in.
 */

import { useEffect, useState } from 'react'

export type SettlementNetwork = 'mainnet-beta' | 'devnet' | 'surfpool'

interface Props {
  txHash: string
  /** Total settled amount in USDC (human units). Split 87/13 internally. */
  totalUsdc: number
  network?: SettlementNetwork
  /** Override the explorer base URL (useful for Surfpool dashboards). */
  explorerBaseUrl?: string
  /** Fired ~3s after mount, when the animation has finished its three beats. */
  onComplete?: () => void
}

const WORKER_BPS = 8700
const TREASURY_BPS = 1300

function explorerUrlFor(
  txHash: string,
  network: SettlementNetwork,
  override?: string,
): string {
  if (override) {
    const base = override.replace(/\/$/, '')
    return `${base}/tx/${txHash}`
  }
  if (network === 'surfpool') {
    // Surfpool ships its own studio on localhost. Default to the
    // canonical local URL but expect callers to override in CI.
    return `http://localhost:8899/tx/${txHash}`
  }
  const cluster = network === 'devnet' ? '?cluster=devnet' : ''
  return `https://explorer.solana.com/tx/${txHash}${cluster}`
}

function useCountUp(target: number, durationMs: number, delayMs: number): number {
  const [value, setValue] = useState(0)
  useEffect(() => {
    let raf = 0
    let timeout: ReturnType<typeof setTimeout> | null = null
    function run() {
      const start = performance.now()
      function tick(now: number) {
        const elapsed = now - start
        const ratio = Math.min(1, elapsed / durationMs)
        // ease-out cubic — fast start, soft landing on the final digit.
        const eased = 1 - Math.pow(1 - ratio, 3)
        setValue(target * eased)
        if (ratio < 1) raf = requestAnimationFrame(tick)
      }
      raf = requestAnimationFrame(tick)
    }
    timeout = setTimeout(run, delayMs)
    return () => {
      if (timeout) clearTimeout(timeout)
      cancelAnimationFrame(raf)
    }
  }, [target, durationMs, delayMs])
  return value
}

export function SettlementAnimation({
  txHash,
  totalUsdc,
  network = 'mainnet-beta',
  explorerBaseUrl,
  onComplete,
}: Props) {
  const workerShare = totalUsdc * (WORKER_BPS / 10_000)
  const treasuryShare = totalUsdc * (TREASURY_BPS / 10_000)

  const totalValue = useCountUp(totalUsdc, 600, 0)
  const workerValue = useCountUp(workerShare, 1_000, 600)
  const treasuryValue = useCountUp(treasuryShare, 1_000, 600)
  const [splitVisible, setSplitVisible] = useState(false)
  const [txVisible, setTxVisible] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setSplitVisible(true), 600)
    const t2 = setTimeout(() => setTxVisible(true), 1_600)
    const t3 = setTimeout(() => onComplete?.(), 3_000)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
    }
  }, [onComplete])

  const explorerUrl = explorerUrlFor(txHash, network, explorerBaseUrl)

  return (
    <div className="rounded-lg border-2 border-black bg-white p-8 font-mono text-black">
      <div className="text-xs uppercase tracking-widest text-zinc-600">
        Settlement complete
      </div>

      <div
        className="mt-2 text-6xl font-bold leading-none tabular-nums"
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        ${totalValue.toFixed(4)}
      </div>

      <div
        className="mt-6 grid grid-cols-2 gap-4 transition-opacity duration-500"
        style={{ opacity: splitVisible ? 1 : 0 }}
      >
        <div className="border-l-4 border-black pl-3">
          <div className="text-xs uppercase tracking-widest text-zinc-600">
            Worker · 87%
          </div>
          <div
            className="mt-1 text-3xl font-bold tabular-nums"
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            ${workerValue.toFixed(4)}
          </div>
        </div>
        <div className="border-l-4 border-zinc-400 pl-3">
          <div className="text-xs uppercase tracking-widest text-zinc-600">
            Treasury · 13%
          </div>
          <div
            className="mt-1 text-3xl font-bold tabular-nums"
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            ${treasuryValue.toFixed(4)}
          </div>
        </div>
      </div>

      <div
        className="mt-6 border-t border-black pt-3 transition-opacity duration-500"
        style={{ opacity: txVisible ? 1 : 0 }}
      >
        <div className="text-xs uppercase tracking-widest text-zinc-600">
          Transaction
        </div>
        <a
          href={explorerUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 block break-all text-sm text-black underline decoration-2 underline-offset-4 hover:bg-black hover:text-white"
        >
          {txHash}
        </a>
        <div className="mt-1 text-xs text-zinc-500">network · {network}</div>
      </div>
    </div>
  )
}

export default SettlementAnimation
