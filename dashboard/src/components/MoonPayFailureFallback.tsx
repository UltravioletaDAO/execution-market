/**
 * MoonPayFailureFallback — escape hatch for the MoonPay on-ramp flow.
 *
 * Phase 4.10 of MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO. Surfaces when the
 * happy-path watcher (Phase 4.9) gets stuck and the demo needs a way
 * out. Two failure modes we've seen in dry-runs and that we expect on
 * stage:
 *
 *   1. Card declined / KYC stuck — MoonPay never delivers USDC. The
 *      overlay closes silently, no webhook arrives, balance stays flat.
 *   2. Webhook lag — funds *did* arrive on-chain but our backend hasn't
 *      seen the `transaction.completed` callback yet, so the publish
 *      flow won't move forward.
 *
 * In both cases the user clicks "I already have USDC, skip on-ramp".
 * We query the chain directly (via the same hook that powers Phase 4.9
 * but with `enabled: false` so it doesn't poll on mount) and:
 *
 *   - balance >= targetUsdc → fire `onSkip(balance)`; the caller decides
 *     what that means (resume publish_task, dismiss the overlay, etc).
 *   - balance < targetUsdc  → show the shortfall and offer `onRetry()`,
 *     which the caller wires to re-open MoonPay.
 *
 * Like the hook, this component is observation-only. It never decides
 * "the user is good to publish" — that's the caller's job.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { readSolanaUsdcBalance, resolveSolanaRpc } from '../services/solana-balance'

interface Props {
  walletAddress: string
  /** USDC threshold (human units). Component compares `balance >= targetUsdc`. */
  targetUsdc: number
  /** Override the Solana RPC. Same env fallback as `useMoonPayOnramp`. */
  rpcUrl?: string
  /** One-line context for why the fallback surfaced (e.g. "Overlay closed"). */
  reason?: string
  /** Fired when balance check passes — caller resumes the original flow. */
  onSkip?: (balance: number) => void
  /** Fired when the user wants to re-open MoonPay. */
  onRetry?: () => void
}

type CheckState = 'idle' | 'checking' | 'sufficient' | 'insufficient' | 'error'

export function MoonPayFailureFallback({
  walletAddress,
  targetUsdc,
  rpcUrl,
  reason,
  onSkip,
  onRetry,
}: Props) {
  const { t } = useTranslation()
  const [state, setState] = useState<CheckState>('idle')
  const [balance, setBalance] = useState(0)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  async function handleSkip() {
    setState('checking')
    setErrorMsg(null)
    try {
      const latest = await readSolanaUsdcBalance(walletAddress, resolveSolanaRpc(rpcUrl))
      setBalance(latest)
      if (latest >= targetUsdc) {
        setState('sufficient')
        onSkip?.(latest)
      } else {
        setState('insufficient')
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err))
      setState('error')
    }
  }

  const shortfall = Math.max(0, targetUsdc - balance)

  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-4">
      <div className="mb-2 flex items-start justify-between">
        <h3 className="text-sm font-semibold text-amber-900">
          {t('moonpayFallback.title', 'MoonPay not working?')}
        </h3>
        {reason && (
          <span className="ml-2 rounded bg-amber-200 px-2 py-0.5 text-[10px] font-mono text-amber-900">
            {reason}
          </span>
        )}
      </div>

      <p className="text-xs text-amber-800">
        {t('moonpayFallback.body', "If you already have USDC on Solana in this wallet, skip the on-ramp. We'll check the chain directly.")}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={handleSkip}
          disabled={state === 'checking'}
          className="rounded bg-zinc-900 px-3 py-1.5 text-xs text-white disabled:bg-zinc-400"
        >
          {state === 'checking'
            ? t('moonpayFallback.checking', 'Checking balance…')
            : t('moonpayFallback.skip', 'I already have USDC, skip on-ramp')}
        </button>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="rounded border border-zinc-400 bg-white px-3 py-1.5 text-xs text-zinc-800"
          >
            {t('moonpayFallback.retry', 'Open MoonPay again')}
          </button>
        )}
      </div>

      {state === 'sufficient' && (
        <p className="mt-3 text-xs text-emerald-800">
          {t('moonpayFallback.balanceOk', 'Balance OK ({{balance}} USDC ≥ {{target}} USDC). Resuming…', { balance: balance.toFixed(2), target: targetUsdc.toFixed(2) })}
        </p>
      )}

      {state === 'insufficient' && (
        <p className="mt-3 text-xs text-red-700">
          {t('moonpayFallback.shortBy', 'Short by {{shortfall}} USDC. Wallet has {{balance}} USDC; need {{target}} USDC. Re-open MoonPay or top up another way.', { shortfall: shortfall.toFixed(2), balance: balance.toFixed(2), target: targetUsdc.toFixed(2) })}
        </p>
      )}

      {state === 'error' && (
        <p className="mt-3 text-xs text-red-700">
          {t('moonpayFallback.readError', "Couldn't read on-chain balance:")}{' '}
          <code className="font-mono">{errorMsg ?? 'unknown error'}</code>
        </p>
      )}

      <p className="mt-3 break-all font-mono text-[10px] text-zinc-500">
        wallet: {walletAddress}
      </p>
    </div>
  )
}

export default MoonPayFailureFallback
