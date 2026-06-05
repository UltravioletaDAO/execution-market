/**
 * MoonPayFrame — opens the MoonPay Headless overlay (Phase 4.8).
 *
 * Takes a pre-signed onramp payload from the backend
 * (`/api/v1/moonpay/sign-url` or a 402 INSUFFICIENT_FUNDS body) and hands
 * it to `@moonpay/moonpay-js` with `variant: "overlay"`. The signature is
 * applied via `widget.updateSignature()` so MoonPay's server can verify
 * the URL was issued by our backend.
 *
 * Mobile path: when the viewport is below the `sm:` Tailwind breakpoint,
 * fall back to `window.open(url, '_blank')` because the overlay variant
 * does not render reliably on small screens (iOS Safari clips it).
 *
 * The SDK is loaded via dynamic import so a missing dep does not crash the
 * bundle — the component renders an install hint instead.
 */

import { useEffect, useRef, useState } from 'react'
import type { OnrampPayload } from '../services/moonpay'

const MOBILE_BREAKPOINT_PX = 640

interface Props {
  onramp: OnrampPayload
  /** Optional handler for lifecycle events (transaction.*, overlay.*, fallback.*). */
  onEvent?: (kind: string, payload: unknown) => void
  /** Called when the overlay cannot be opened (SDK load failure, MoonPay error). */
  onError?: (err: unknown) => void
  /** Called when the user closes the overlay. */
  onClose?: () => void
}

type MoonPayHandlers = {
  onTransactionCreated?: (payload: unknown) => void | Promise<void>
  onTransactionCompleted?: (payload: unknown) => void | Promise<void>
  onTransactionFailed?: (payload: unknown) => void | Promise<void>
  onCloseOverlay?: () => void
}

type MoonPayWidget = {
  show?: () => Promise<void> | void
  close?: () => Promise<void> | void
  updateSignature?: (signature: string) => void
}

type MoonPayFactory = (cfg: {
  flow: 'buy' | 'sell' | 'ramp'
  environment: 'sandbox' | 'production'
  variant: 'overlay' | 'embedded' | 'newTab' | 'newWindow'
  params: Record<string, unknown>
  handlers?: MoonPayHandlers
}) => MoonPayWidget | null | undefined

type SdkModule = {
  loadMoonPay: (version?: string | null) => Promise<MoonPayFactory | undefined>
}

async function loadSdk(): Promise<SdkModule> {
  const mod = (await import(/* @vite-ignore */ '@moonpay/moonpay-js')) as unknown as SdkModule
  if (!mod?.loadMoonPay) {
    throw new Error('@moonpay/moonpay-js loaded but loadMoonPay is missing')
  }
  return mod
}

function isMobileViewport(): boolean {
  if (typeof window === 'undefined') return false
  return window.innerWidth < MOBILE_BREAKPOINT_PX
}

interface ParsedMoonPayUrl {
  environment: 'sandbox' | 'production'
  params: Record<string, string>
}

function parseMoonPayUrl(url: string): ParsedMoonPayUrl {
  const parsed = new URL(url)
  const params: Record<string, string> = {}
  parsed.searchParams.forEach((value, key) => {
    // Drop the signature from params — the SDK reapplies it via
    // updateSignature() so MoonPay's server can verify the payload.
    if (key === 'signature') return
    params[key] = value
  })
  const environment: 'sandbox' | 'production' = parsed.host.includes('sandbox')
    ? 'sandbox'
    : 'production'
  return { environment, params }
}

type Phase = 'loading' | 'opening' | 'opened' | 'closed' | 'fallback' | 'error'

export function MoonPayFrame({ onramp, onEvent, onError, onClose }: Props) {
  const widgetRef = useRef<MoonPayWidget | null>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Hold the handler props in refs so the open effect can depend only on the
  // onramp payload. Callers pass inline arrows that change identity on every
  // render (balance ticks, stage changes); if those were effect deps the
  // widget would tear down (close) and reopen mid-buy (F-04). transaction.*
  // events never close the overlay — only onCloseOverlay does.
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent
  const onErrorRef = useRef(onError)
  onErrorRef.current = onError
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    let cancelled = false

    async function open() {
      // Mobile fallback — overlay variant on iOS Safari has clipping bugs
      // and Apple Pay handoff is more reliable via a new tab.
      if (isMobileViewport()) {
        const opened = window.open(onramp.url, '_blank', 'noopener,noreferrer')
        if (cancelled) return
        if (opened) {
          onEventRef.current?.('fallback.newTab', { url: onramp.url })
          setPhase('fallback')
        } else {
          // Popup blocker swallowed it — surface as an error so the
          // failure-mode UI (Phase 4.10) can offer a manual link.
          const err = new Error('popup blocked')
          setErrorMsg(err.message)
          setPhase('error')
          onErrorRef.current?.(err)
        }
        return
      }

      try {
        const sdk = await loadSdk()
        const moonPay = await sdk.loadMoonPay()
        if (cancelled) return
        if (!moonPay) {
          throw new Error('loadMoonPay() returned undefined')
        }

        const { environment, params } = parseMoonPayUrl(onramp.url)

        const widget = moonPay({
          flow: 'buy',
          environment,
          variant: 'overlay',
          params,
          handlers: {
            onTransactionCreated: (payload) =>
              onEventRef.current?.('transaction.created', payload),
            onTransactionCompleted: (payload) =>
              onEventRef.current?.('transaction.completed', payload),
            onTransactionFailed: (payload) =>
              onEventRef.current?.('transaction.failed', payload),
            onCloseOverlay: () => {
              if (cancelled) return
              onEventRef.current?.('overlay.closed', null)
              setPhase('closed')
              onCloseRef.current?.()
            },
          },
        })

        if (!widget) {
          throw new Error('moonPay() returned undefined widget')
        }
        widgetRef.current = widget

        // Apply backend HMAC so MoonPay's server validates the URL.
        if (typeof widget.updateSignature === 'function' && onramp.signature) {
          widget.updateSignature(onramp.signature)
        }

        if (cancelled) return
        setPhase('opening')

        await widget.show?.()

        if (!cancelled) setPhase('opened')
      } catch (err) {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : String(err)
        setErrorMsg(msg)
        setPhase('error')
        onErrorRef.current?.(err)
      }
    }

    open()

    return () => {
      cancelled = true
      const w = widgetRef.current
      if (w?.close) {
        Promise.resolve(w.close()).catch(() => undefined)
      }
      widgetRef.current = null
    }
  }, [onramp.url, onramp.signature])

  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between text-xs text-zinc-500">
        <span className="font-mono">variant=overlay</span>
        <span>phase: {phase}</span>
      </div>
      <p className="text-sm text-zinc-700">
        {phase === 'loading' && 'Loading MoonPay overlay…'}
        {phase === 'opening' && 'Opening MoonPay overlay…'}
        {phase === 'opened' && 'MoonPay overlay is open in the foreground.'}
        {phase === 'fallback' &&
          'Opened MoonPay in a new tab (mobile fallback). Return to this page once the buy completes.'}
        {phase === 'closed' && 'MoonPay overlay closed.'}
      </p>
      {phase === 'error' && (
        <div className="mt-3 rounded bg-red-50 p-3 text-sm text-red-700">
          <p className="font-semibold">MoonPay overlay failed to open</p>
          <pre className="mt-1 whitespace-pre-wrap break-all text-xs">{errorMsg}</pre>
          {errorMsg?.includes('@moonpay/moonpay-js') && (
            <p className="mt-2 text-xs">
              Install the SDK first:{' '}
              <code className="rounded bg-zinc-900 px-1 py-0.5 text-white">
                npm install @moonpay/moonpay-js
              </code>{' '}
              inside <code>dashboard/</code>.
            </p>
          )}
          {errorMsg === 'popup blocked' && (
            <p className="mt-2 text-xs">
              The browser blocked the popup. Open the URL manually:{' '}
              <a
                href={onramp.url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                buy USDC on MoonPay
              </a>
              .
            </p>
          )}
        </div>
      )}
    </div>
  )
}
