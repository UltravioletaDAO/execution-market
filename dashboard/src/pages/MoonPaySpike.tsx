/**
 * MoonPaySpike — smoke page at /spike/moonpay for the Headless overlay.
 *
 * Phase 4.8: the page exercises the new URL-signing flow. It calls
 * `requestMoonPaySignedUrl()` on the backend, then hands the resulting
 * onramp payload to `<MoonPayFrame>` which opens the overlay via
 * `@moonpay/moonpay-js`. No auth guard, no executor lookup — just the
 * round-trip.
 *
 * Gated by `VITE_MOONPAY_ENABLED=true` at build time and `EM_MOONPAY_ENABLED`
 * on the backend. Both must be on for the page and the API route to exist.
 */

import { useEffect, useMemo, useState } from 'react'
import { MoonPayFrame } from '../components/MoonPayFrame'
import {
  getMoonPayHealth,
  requestMoonPaySignedUrl,
  MoonPayError,
  type MoonPayHealth,
  type OnrampPayload,
} from '../services/moonpay'

interface EventLogEntry {
  ts: string
  kind: string
  payload: unknown
}

export function MoonPaySpike() {
  const [externalId, setExternalId] = useState('')
  const [walletAddress, setWalletAddress] = useState('')
  const [fiatAmount, setFiatAmount] = useState(20)
  const [fiatCurrency, setFiatCurrency] = useState('usd')
  const [cryptoCurrency, setCryptoCurrency] = useState('usdc_sol')

  const [onramp, setOnramp] = useState<OnrampPayload | null>(null)
  const [health, setHealth] = useState<MoonPayHealth | null>(null)
  const [signing, setSigning] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [events, setEvents] = useState<EventLogEntry[]>([])

  useEffect(() => {
    getMoonPayHealth()
      .then(setHealth)
      .catch((err) => {
        const msg = err instanceof Error ? err.message : String(err)
        setPageError(`Health probe failed: ${msg}`)
      })
  }, [])

  const canSign = useMemo(
    () => Boolean(walletAddress && fiatAmount >= 20),
    [walletAddress, fiatAmount],
  )

  async function handleSignUrl() {
    setSigning(true)
    setPageError(null)
    setEvents([])
    setOnramp(null)
    try {
      const result = await requestMoonPaySignedUrl({
        walletAddress,
        baseCurrencyAmount: fiatAmount,
        baseCurrencyCode: fiatCurrency,
        currencyCode: cryptoCurrency,
        externalCustomerId: externalId || undefined,
      })
      setOnramp(result)
    } catch (err) {
      if (err instanceof MoonPayError) {
        setPageError(`Sign-URL failed (${err.status}): ${err.message}`)
      } else {
        setPageError(err instanceof Error ? err.message : String(err))
      }
    } finally {
      setSigning(false)
    }
  }

  function logEvent(kind: string, payload: unknown) {
    setEvents((prev) => [
      { ts: new Date().toISOString(), kind, payload },
      ...prev.slice(0, 49),
    ])
  }

  const backendEnabled = health?.enabled === true
  const backendReady =
    health?.secret_key_configured && health?.public_key_configured

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-zinc-900">
          MoonPay Headless Onramp — Overlay smoke
        </h1>
        <p className="mt-1 text-sm text-zinc-600">
          Calls <code>POST /api/v1/moonpay/sign-url</code>, then opens the
          <code> @moonpay/moonpay-js</code> overlay with the pre-signed URL.
        </p>
      </header>

      <section className="mb-6 rounded-md border border-zinc-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-semibold text-zinc-800">Backend health</h2>
        {health == null ? (
          <p className="text-sm text-zinc-500">
            {pageError ? pageError : 'Probing /api/v1/moonpay/health…'}
          </p>
        ) : (
          <ul className="space-y-1 text-xs font-mono">
            <li>enabled: {String(health.enabled)}</li>
            <li>secret_key_configured: {String(health.secret_key_configured)}</li>
            <li>public_key_configured: {String(health.public_key_configured)}</li>
            <li>webhook_secret_configured: {String(health.webhook_secret_configured)}</li>
            <li>api_base_url: {health.api_base_url}</li>
          </ul>
        )}
        {!backendEnabled && health != null && (
          <p className="mt-2 text-xs text-amber-700">
            EM_MOONPAY_ENABLED is false on the backend. Flip it on and restart.
          </p>
        )}
        {backendEnabled && !backendReady && (
          <p className="mt-2 text-xs text-amber-700">
            One or more MoonPay secrets missing — sign-url will 503.
          </p>
        )}
      </section>

      <section className="mb-6 rounded-md border border-zinc-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-zinc-800">1. Sign URL</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="col-span-1 md:col-span-2 text-xs text-zinc-600">
            wallet address (Solana base58)
            <input
              className="mt-1 w-full rounded border border-zinc-300 px-2 py-1 text-sm font-mono"
              value={walletAddress}
              onChange={(e) => setWalletAddress(e.target.value)}
              placeholder="e.g. So1ana...wallet"
            />
          </label>
          <label className="text-xs text-zinc-600">
            fiat amount (min $20)
            <input
              type="number"
              min={20}
              className="mt-1 w-full rounded border border-zinc-300 px-2 py-1 text-sm"
              value={fiatAmount}
              onChange={(e) => setFiatAmount(Number(e.target.value))}
            />
          </label>
          <label className="text-xs text-zinc-600">
            fiat currency
            <input
              className="mt-1 w-full rounded border border-zinc-300 px-2 py-1 text-sm font-mono"
              value={fiatCurrency}
              onChange={(e) => setFiatCurrency(e.target.value)}
            />
          </label>
          <label className="text-xs text-zinc-600">
            crypto currency
            <input
              className="mt-1 w-full rounded border border-zinc-300 px-2 py-1 text-sm font-mono"
              value={cryptoCurrency}
              onChange={(e) => setCryptoCurrency(e.target.value)}
            />
          </label>
          <label className="text-xs text-zinc-600">
            externalCustomerId (optional)
            <input
              className="mt-1 w-full rounded border border-zinc-300 px-2 py-1 text-sm font-mono"
              value={externalId}
              onChange={(e) => setExternalId(e.target.value)}
              placeholder="executor UUID"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={handleSignUrl}
          disabled={signing || !canSign}
          className="mt-3 rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:bg-zinc-400"
        >
          {signing ? 'Signing…' : 'Sign URL'}
        </button>
        {onramp && (
          <pre className="mt-3 overflow-x-auto rounded bg-zinc-100 p-2 text-xs">
            {JSON.stringify(
              {
                url: onramp.url.slice(0, 64) + '…',
                signature: onramp.signature.slice(0, 12) + '…',
                qty_needed: onramp.qty_needed,
                currency: onramp.currency,
              },
              null,
              2,
            )}
          </pre>
        )}
        {pageError && <p className="mt-3 text-xs text-red-700">{pageError}</p>}
      </section>

      <section className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-zinc-800">2. Overlay</h2>
        {onramp ? (
          <MoonPayFrame
            onramp={onramp}
            onEvent={logEvent}
            onError={(err) => {
              const msg = err instanceof Error ? err.message : String(err)
              setPageError(msg)
            }}
            onClose={() => logEvent('overlay.user_closed', null)}
          />
        ) : (
          <div className="rounded-md border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500">
            Sign a URL first to open the overlay.
          </div>
        )}
      </section>

      <section className="rounded-md border border-zinc-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-zinc-800">Event log</h2>
        {events.length === 0 ? (
          <p className="text-xs text-zinc-500">No events yet.</p>
        ) : (
          <ul className="space-y-2">
            {events.map((evt, i) => (
              <li key={i} className="border-l-2 border-zinc-300 pl-2 text-xs">
                <div className="font-mono text-zinc-600">
                  {evt.ts} · {evt.kind}
                </div>
                <pre className="mt-1 overflow-x-auto text-[10px] text-zinc-700">
                  {JSON.stringify(evt.payload, null, 2)}
                </pre>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export default MoonPaySpike
