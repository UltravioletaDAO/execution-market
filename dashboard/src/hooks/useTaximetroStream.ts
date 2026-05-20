/**
 * useTaximetroStream — consume the EM taxímetro SSE relay (Phase 5.3).
 *
 * Connects to `/api/v1/taximetro/{channelId}/stream`, which thin-proxies
 * pay.sh's native SSE plus a DB-mirrored replay window. The backend
 * emits named events that map 1:1 to migration 108's allowed types:
 *
 *   - `hello`               — initial frame (server says "we're live")
 *   - `session_open`        — pay.sh accepted the session
 *   - `voucher_accepted`    — one tick of the meter (cumulative_uusdc rises)
 *   - `session_close`       — channel was closed by user/robot
 *   - `settlement_complete` — on-chain settlement landed (tx_hash final)
 *   - `error`               — relay/pay.sh problem (recoverable)
 *
 * Auto-reconnect: EventSource has a built-in retry but with a fixed
 * browser-defined delay. The demo needs to survive flaky wifi at MoonPay
 * NYC, so we wrap it with an exponential backoff manager: 1s → 2s → 4s
 * → 8s → 16s → 30s cap, reset on the first successful frame. We tear
 * down the native EventSource on each retry to avoid two streams
 * fighting over the same channel.
 *
 * Terminal stop: `settlement_complete` is the only event that ends the
 * loop. After that, the caller is expected to remount with a fresh
 * channelId for the next task. `session_close` is *not* terminal — pay.sh
 * may emit a final settlement after close, so we keep the stream open.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const DEFAULT_API_BASE = 'https://api.execution.market'
const MIN_BACKOFF_MS = 1_000
const MAX_BACKOFF_MS = 30_000

export type TaximetroStatus =
  | 'idle'
  | 'connecting'
  | 'live'
  | 'closed'
  | 'settled'
  | 'error'

export interface TaximetroEvent {
  type: string
  data: Record<string, unknown>
  receivedAt: string
}

export interface UseTaximetroStreamOptions {
  enabled?: boolean
  /** Override the API base (defaults to VITE_API_URL or production). */
  apiBaseUrl?: string
  /** When true, server replays history before live events (default: true). */
  replay?: boolean
}

export interface UseTaximetroStreamReturn {
  cumulativeUsdc: number
  voucherCount: number
  status: TaximetroStatus
  settlementTxHash: string | null
  lastEvent: TaximetroEvent | null
  error: Error | null
  /** Force-close the stream and reset state. Useful between demo runs. */
  reset: () => void
}

function pickNumber(data: Record<string, unknown>, ...keys: string[]): number | null {
  for (const key of keys) {
    const v = data[key]
    if (typeof v === 'number' && Number.isFinite(v)) return v
    if (typeof v === 'string') {
      const parsed = Number(v)
      if (Number.isFinite(parsed)) return parsed
    }
  }
  return null
}

function pickString(data: Record<string, unknown>, ...keys: string[]): string | null {
  for (const key of keys) {
    const v = data[key]
    if (typeof v === 'string' && v.length > 0) return v
  }
  return null
}

export function useTaximetroStream(
  channelId: string | null | undefined,
  options: UseTaximetroStreamOptions = {},
): UseTaximetroStreamReturn {
  const { enabled = true, apiBaseUrl, replay = true } = options

  const [cumulativeUsdc, setCumulativeUsdc] = useState(0)
  const [voucherCount, setVoucherCount] = useState(0)
  const [status, setStatus] = useState<TaximetroStatus>('idle')
  const [settlementTxHash, setSettlementTxHash] = useState<string | null>(null)
  const [lastEvent, setLastEvent] = useState<TaximetroEvent | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const sourceRef = useRef<EventSource | null>(null)
  const backoffRef = useRef(MIN_BACKOFF_MS)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stoppedRef = useRef(false)
  const settledRef = useRef(false)

  const resolvedBase = useMemo(() => {
    if (apiBaseUrl) return apiBaseUrl.replace(/\/$/, '')
    const env = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
    return (env && env.length > 0 ? env : DEFAULT_API_BASE).replace(/\/$/, '')
  }, [apiBaseUrl])

  const teardown = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current)
      retryTimerRef.current = null
    }
    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }
  }, [])

  const reset = useCallback(() => {
    stoppedRef.current = true
    settledRef.current = false
    teardown()
    setCumulativeUsdc(0)
    setVoucherCount(0)
    setSettlementTxHash(null)
    setLastEvent(null)
    setError(null)
    setStatus('idle')
    backoffRef.current = MIN_BACKOFF_MS
  }, [teardown])

  useEffect(() => {
    stoppedRef.current = false
    settledRef.current = false

    if (!enabled || !channelId) {
      teardown()
      setStatus('idle')
      return
    }

    function connect() {
      if (stoppedRef.current || settledRef.current) return

      setStatus('connecting')
      const url = `${resolvedBase}/api/v1/taximetro/${encodeURIComponent(channelId!)}/stream?replay=${replay ? 'true' : 'false'}`
      const source = new EventSource(url)
      sourceRef.current = source

      function handle(eventType: string, raw: MessageEvent) {
        // Reset backoff on the first frame — connection is good.
        backoffRef.current = MIN_BACKOFF_MS

        let data: Record<string, unknown> = {}
        try {
          data = raw.data ? (JSON.parse(raw.data) as Record<string, unknown>) : {}
        } catch {
          // Non-JSON data is unexpected; surface as a generic frame
          // instead of dropping the event silently.
          data = { raw: raw.data }
        }

        setLastEvent({ type: eventType, data, receivedAt: new Date().toISOString() })

        if (eventType === 'hello' || eventType === 'session_open') {
          setStatus('live')
          return
        }

        if (eventType === 'voucher_accepted') {
          setStatus('live')
          const uusdc = pickNumber(data, 'cumulative_uusdc', 'cumulativeUusdc', 'cumulative')
          if (uusdc !== null) setCumulativeUsdc(uusdc / 1_000_000)
          setVoucherCount((c) => c + 1)
          return
        }

        if (eventType === 'session_close') {
          // Not terminal — pay.sh may still emit settlement_complete
          // after a close. Hold the channel open until settle or unmount.
          setStatus('closed')
          return
        }

        if (eventType === 'settlement_complete') {
          const tx = pickString(data, 'tx_hash', 'txHash', 'signature')
          if (tx) setSettlementTxHash(tx)
          // Final balance may arrive on this frame too.
          const uusdc = pickNumber(data, 'cumulative_uusdc', 'cumulativeUusdc', 'cumulative')
          if (uusdc !== null) setCumulativeUsdc(uusdc / 1_000_000)
          setStatus('settled')
          settledRef.current = true
          teardown()
          return
        }

        if (eventType === 'error') {
          const msg = pickString(data, 'error', 'message') ?? 'taximetro relay error'
          setError(new Error(msg))
          setStatus('error')
          // Don't tear down — relay errors are usually transient (pay.sh
          // reconnect). EventSource will surface a hard failure via
          // onerror if the relay itself is gone.
        }
      }

      // Named events from the backend's `_sse_format`.
      const namedTypes = [
        'hello',
        'session_open',
        'voucher_accepted',
        'session_close',
        'settlement_complete',
        'error',
      ]
      for (const type of namedTypes) {
        source.addEventListener(type, (e) => handle(type, e as MessageEvent))
      }
      // Fallback for any future event the server might add.
      source.onmessage = (e) => handle('message', e)

      source.onerror = () => {
        if (stoppedRef.current || settledRef.current) return
        // Browser auto-reconnect is unreliable for our case (it pauses
        // until tab regains focus on some browsers). Tear down and
        // schedule our own retry with exponential backoff.
        teardown()
        setStatus('error')
        const delay = backoffRef.current
        backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS)
        retryTimerRef.current = setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      stoppedRef.current = true
      teardown()
    }
  }, [enabled, channelId, replay, resolvedBase, teardown])

  return {
    cumulativeUsdc,
    voucherCount,
    status,
    settlementTxHash,
    lastEvent,
    error,
    reset,
  }
}
