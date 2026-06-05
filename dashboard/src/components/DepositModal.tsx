/**
 * DepositModal — the reusable on-ramp loop for the human-hires-human flow.
 *
 * Flow: request a signed MoonPay Widget URL for USDC on Base (buying exactly
 * depositAmountUsdc) → open the headless overlay → watch the wallet's Base
 * USDC balance (useMoonPayOnramp, chain:'base') → fire onFunded when balance
 * reaches targetBalanceUsdc.
 *
 * IMPORTANT: "amount to buy" and "balance to reach" are two different numbers
 * (F-03). depositAmountUsdc is what MoonPay charges the card; targetBalanceUsdc
 * is the wallet balance the watcher waits for. A "Depositar +$20" button buys
 * 20 while targeting currentBalance+20; task funding buys max(5, shortfall)
 * while targeting the full required balance.
 *
 * Reused by the publisher Dashboard ("Depositar"), CreateRequest (fund CTA),
 * the services catalog, and the approval flow (fund-before-sign). EM never
 * touches fiat — MoonPay is the money transmitter of record; the backend only
 * HMAC-signs the Widget URL (/api/v1/moonpay/sign-url).
 *
 * Gated by the backend EM_MOONPAY_ENABLED flag: requestMoonPaySignedUrl 404s
 * when MoonPay is off, surfaced here as a clear error rather than a crash.
 */
import { useEffect, useRef, useState } from 'react'
import {
  requestMoonPaySignedUrl,
  MoonPayError,
  type OnrampPayload,
} from '../services/moonpay'
import { MoonPayFrame } from './MoonPayFrame'
import { useMoonPayOnramp } from '../hooks/useMoonPayOnramp'

interface Props {
  open: boolean
  walletAddress: string
  /** Wallet USDC balance the watcher waits for before firing onFunded. */
  targetBalanceUsdc: number
  /** USDC to buy on MoonPay (card charge). Floored to MoonPay's $5 min. */
  depositAmountUsdc: number
  /** Current wallet balance, for display before the live watcher reads it. */
  currentBalanceUsdc?: number
  /** EM executor.id for MoonPay Customer Connection reuse (optional). */
  externalCustomerId?: string
  onClose: () => void
  /** Fired once the wallet balance reaches targetBalanceUsdc. */
  onFunded?: (balance: number) => void
}

type Stage = 'idle' | 'requesting' | 'overlay' | 'watching' | 'funded' | 'error'

export function DepositModal({
  open,
  walletAddress,
  targetBalanceUsdc,
  depositAmountUsdc,
  currentBalanceUsdc,
  externalCustomerId,
  onClose,
  onFunded,
}: Props) {
  const [stage, setStage] = useState<Stage>('idle')
  const [onramp, setOnramp] = useState<OnrampPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const requestedRef = useRef(false)

  // Watch the Base balance while the overlay is up. The hook is observation
  // only — it never decides the deposit succeeded on its own. It watches the
  // *target balance*, not the amount being bought (F-03).
  const { balance, phase } = useMoonPayOnramp(walletAddress, {
    enabled: open && (stage === 'overlay' || stage === 'watching'),
    chain: 'base',
    targetUsdc: targetBalanceUsdc,
    onComplete: (r) => {
      if (r.phase === 'arrived') {
        setStage('funded')
        onFunded?.(r.balance)
      }
    },
  })

  // The watcher's balance is 0 until it polls (overlay/watching stage). Until
  // then, show the caller-provided current balance so the user sees a real
  // number, not $0.00.
  const displayBalance = balance > 0 ? balance : (currentBalanceUsdc ?? 0)

  // Request the signed Widget URL once, when the modal opens.
  useEffect(() => {
    if (!open) {
      requestedRef.current = false
      setStage('idle')
      setOnramp(null)
      setError(null)
      return
    }
    if (requestedRef.current || !walletAddress) return
    requestedRef.current = true
    setStage('requesting')
    requestMoonPaySignedUrl({
      walletAddress,
      baseCurrencyAmount: Math.max(5, Number(depositAmountUsdc.toFixed(2))),
      currencyCode: 'usdc_base',
      externalCustomerId,
      theme: 'dark',
    })
      .then((p) => {
        setOnramp(p)
        setStage('overlay')
      })
      .catch((e) => {
        setError(
          e instanceof MoonPayError
            ? e.message
            : 'No se pudo iniciar el depósito. Intenta de nuevo.',
        )
        setStage('error')
      })
  }, [open, walletAddress, depositAmountUsdc, externalCustomerId])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-3">
          <h3 className="font-mono text-sm font-bold text-zinc-900">
            Depositar USDC (Base)
          </h3>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-900"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4 p-5">
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">Necesitas</span>
              <span className="font-medium text-zinc-900">
                ${targetBalanceUsdc.toFixed(2)} USDC
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Comprarás</span>
              <span className="font-medium text-zinc-900">
                ${Math.max(5, Number(depositAmountUsdc.toFixed(2))).toFixed(2)} USDC
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Saldo actual</span>
              <span className="font-medium text-zinc-900">
                ${displayBalance.toFixed(2)} USDC
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Red</span>
              <span className="font-medium text-zinc-900">Base</span>
            </div>
          </div>

          {stage === 'requesting' && (
            <p className="text-sm text-zinc-500">Preparando el depósito…</p>
          )}

          {(stage === 'overlay' || stage === 'watching') && onramp && (
            <>
              <MoonPayFrame
                onramp={onramp}
                onEvent={() => setStage('watching')}
                onError={(e) => {
                  setError(String(e))
                  setStage('error')
                }}
                onClose={onClose}
              />
              <p className="text-xs text-zinc-500">
                {phase === 'watching'
                  ? 'Esperando que el USDC llegue a tu wallet en Base…'
                  : 'Completa el pago en la ventana de MoonPay.'}
              </p>
            </>
          )}

          {stage === 'funded' && (
            <div className="rounded-lg bg-zinc-900 p-3 text-center text-sm text-white">
              ✅ Fondos recibidos — ${balance.toFixed(2)} USDC en Base. Ya puedes
              continuar.
            </div>
          )}

          {stage === 'error' && (
            <div className="rounded-lg border border-zinc-300 bg-zinc-100 p-3 text-sm text-zinc-900">
              ⚠️ {error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-zinc-200 px-5 py-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-100"
          >
            {stage === 'funded' ? 'Listo' : 'Cancelar'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default DepositModal
