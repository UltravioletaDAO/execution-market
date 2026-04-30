/**
 * VeryAI Palm Verification Component
 *
 * OAuth2/OIDC redirect flow against api.very.org. State machine:
 *
 *   idle ─click─▶ loading_url ─fetch─▶ redirecting ──▶ (browser leaves the page)
 *                                                          │
 *                                                          ▼
 *   ┌──────────────────────  back from callback with ?veryai=… ──┐
 *   │ success → polling ──▶ verified=true ──▶ success            │
 *   │ error   → error                                            │
 *   │ incomplete → error("not_palm_verified")                    │
 *   └────────────────────────────────────────────────────────────┘
 *
 * The backend `/api/v1/very-id/callback` redirects the user back to
 * `{EM_DASHBOARD_URL}/profile?veryai={status}[&reason=…]`. We parse those
 * query params on mount and drive the polling loop.
 *
 * Mirrors WorldIdVerification's idiom (state enum, error UI shape) but
 * does NOT use a modal widget — VeryAI is a full-page OAuth handoff.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { VeryAiBadge } from './VeryAiBadge'

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 30_000

type VerifyState =
  | 'idle'
  | 'loading_url'
  | 'redirecting'
  | 'polling'
  | 'success'
  | 'error'

interface OAuthUrlResponse {
  url: string
  state: string
}

interface StatusResponse {
  verified: boolean
  level: string | null
  verified_at: string | null
}

interface VeryAiVerificationProps {
  onVerified?: (level: string) => void
  className?: string
}

export function VeryAiVerification({
  onVerified,
  className = '',
}: VeryAiVerificationProps) {
  const { t } = useTranslation()
  const { executor, refreshExecutor } = useAuth()

  const [state, setState] = useState<VerifyState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [resultLevel, setResultLevel] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const isVerified = executor?.veryai_verified === true
  const currentLevel = executor?.veryai_level ?? null

  // -------------------------------------------------------------------------
  // OAuth start: fetch authorize URL and redirect.
  // -------------------------------------------------------------------------
  const startVerification = useCallback(async () => {
    if (!executor) return
    setState('loading_url')
    setError(null)

    try {
      const url = `${API_BASE}/api/v1/very-id/oauth-url?executor_id=${encodeURIComponent(
        executor.id
      )}`
      const resp = await fetch(url)
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `Failed to start VeryAI flow: ${resp.status}`)
      }

      const data: OAuthUrlResponse = await resp.json()
      if (!data.url) {
        throw new Error('VeryAI returned an empty authorize URL')
      }

      setState('redirecting')
      window.location.assign(data.url)
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Failed to start verification')
    }
  }, [executor])

  // -------------------------------------------------------------------------
  // On mount: detect the ?veryai=… callback query param and drive polling.
  // -------------------------------------------------------------------------
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const status = params.get('veryai')
    const reason = params.get('reason') ?? undefined
    if (!status) return

    // Strip the params so a manual reload doesn't re-trigger the flow.
    const cleanUrl = window.location.pathname + window.location.hash
    window.history.replaceState({}, '', cleanUrl)

    if (status === 'error') {
      setState('error')
      setError(reason || 'verification_failed')
      return
    }
    if (status === 'incomplete') {
      setState('error')
      setError(reason || 'not_palm_verified')
      return
    }
    if (status !== 'success') return

    // Success path — begin polling /status until verified flips on.
    if (!executor) return
    setState('polling')
    setError(null)

    const startedAt = Date.now()

    const tick = async () => {
      try {
        const resp = await fetch(
          `${API_BASE}/api/v1/very-id/status?executor_id=${encodeURIComponent(
            executor.id
          )}`
        )
        if (!resp.ok) {
          throw new Error(`status lookup failed: ${resp.status}`)
        }
        const data: StatusResponse = await resp.json()
        if (data.verified) {
          if (pollRef.current) {
            clearInterval(pollRef.current)
            pollRef.current = null
          }
          setResultLevel(data.level)
          setState('success')
          await refreshExecutor()
          if (onVerified && data.level) {
            onVerified(data.level)
          }
          return
        }
        if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
          if (pollRef.current) {
            clearInterval(pollRef.current)
            pollRef.current = null
          }
          setState('error')
          setError('poll_timeout')
        }
      } catch (err) {
        if (pollRef.current) {
          clearInterval(pollRef.current)
          pollRef.current = null
        }
        setState('error')
        setError(err instanceof Error ? err.message : 'status_lookup_failed')
      }
    }

    // Kick off immediately, then on interval.
    void tick()
    pollRef.current = setInterval(tick, POLL_INTERVAL_MS)

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [executor, refreshExecutor, onVerified])

  // -------------------------------------------------------------------------
  // Already verified — render the badge and a one-line confirmation.
  // -------------------------------------------------------------------------
  if (isVerified) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <VeryAiBadge level={currentLevel || 'palm_single'} size="md" />
        <span className="text-sm text-gray-600">
          {currentLevel === 'palm_dual'
            ? t('veryai.palmDualVerified', 'Palm Dual Verified')
            : t('veryai.palmVerified', 'Palm Verified')}
        </span>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // Verification flow UI
  // -------------------------------------------------------------------------
  return (
    <div className={`space-y-3 ${className}`}>
      {state === 'idle' && (
        <button
          type="button"
          onClick={startVerification}
          disabled={!executor}
          className="flex items-center gap-2 px-4 py-2.5 bg-black text-white rounded-xl hover:bg-gray-800 transition-colors font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="veryai-start-button"
        >
          <VeryAiBadge level="palm_single" size="md" />
          {t('veryai.verifyButton', 'Verify with VeryAI palm')}
        </button>
      )}

      {state === 'loading_url' && (
        <div
          className="flex items-center gap-2 text-sm text-gray-500"
          data-testid="veryai-loading"
        >
          <div className="w-4 h-4 border-2 border-gray-300 border-t-black rounded-full animate-spin" />
          {t('veryai.preparing', 'Preparing verification...')}
        </div>
      )}

      {state === 'redirecting' && (
        <div
          className="flex items-center gap-2 text-sm text-gray-500"
          data-testid="veryai-redirecting"
        >
          <div className="w-4 h-4 border-2 border-gray-300 border-t-black rounded-full animate-spin" />
          {t('veryai.redirecting', 'Redirecting to VeryAI...')}
        </div>
      )}

      {state === 'polling' && (
        <div
          className="flex items-center gap-2 text-sm text-gray-500"
          data-testid="veryai-polling"
        >
          <div className="w-4 h-4 border-2 border-gray-300 border-t-black rounded-full animate-spin" />
          {t('veryai.confirming', 'Confirming verification...')}
        </div>
      )}

      {state === 'success' && (
        <div
          className="p-3 bg-gray-50 border border-gray-200 rounded-lg flex items-center gap-2"
          data-testid="veryai-success"
        >
          <VeryAiBadge level={resultLevel || 'palm_single'} size="md" />
          <p className="text-sm text-black font-medium">
            {t(
              'veryai.success',
              'Verification successful! Your palm-print signature is now linked to your executor.'
            )}
          </p>
        </div>
      )}

      {state === 'error' && error && (
        <div
          className="p-3 bg-red-50 border border-red-200 rounded-lg"
          data-testid="veryai-error"
        >
          <p className="text-sm text-red-700">
            {t(`veryai.error.${error}`, error)}
          </p>
          <button
            type="button"
            onClick={() => {
              setError(null)
              setState('idle')
            }}
            className="mt-1 text-sm text-red-600 hover:text-red-800 underline"
          >
            {t('veryai.tryAgain', 'Try again')}
          </button>
        </div>
      )}

      {state === 'idle' && (
        <p className="text-xs text-gray-400">
          {t(
            'veryai.explainer',
            'VeryAI verifies your palm-print as a unique human via Veros. Required for tasks above $50.'
          )}
        </p>
      )}
    </div>
  )
}

export default VeryAiVerification
