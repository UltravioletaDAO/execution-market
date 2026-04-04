/**
 * World ID 4.0 Verification Component
 *
 * Handles the full verification flow:
 * 1. Fetch RP signature from backend
 * 2. Open IDKitRequestWidget (v4 API)
 * 3. Send proof to backend for verification
 * 4. Show result
 *
 * Uses @worldcoin/idkit v4 API:
 * - IDKitRequestWidget (controlled open/onOpenChange)
 * - orbLegacy preset for orb-level proof of humanity
 * - IDKitResult with responses[] containing proof[], nullifier, identifier
 */

import { useState, useCallback } from 'react'
import {
  IDKitRequestWidget,
  type IDKitResult,
} from '@worldcoin/idkit'
import { orbLegacy, type RpContext, type ResponseItemV3, type ResponseItemV4 } from '@worldcoin/idkit-core'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

interface WorldIdVerificationProps {
  onVerified?: (level: string) => void
  className?: string
}

interface RPSignatureData {
  nonce: string
  created_at: number
  expires_at: number
  action: string
  signature: string
  rp_id: string
  app_id: string
}

type VerifyState = 'idle' | 'loading_rp' | 'widget_open' | 'verifying' | 'success' | 'error'

export function WorldIdVerification({ onVerified, className = '' }: WorldIdVerificationProps) {
  const { t } = useTranslation()
  const { executor, walletAddress, refreshExecutor } = useAuth()

  const [state, setState] = useState<VerifyState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [rpData, setRPData] = useState<RPSignatureData | null>(null)
  const [widgetOpen, setWidgetOpen] = useState(false)

  // Already verified?
  const isVerified = executor?.world_id_verified === true
  const currentLevel = executor?.world_id_level ?? null

  // Fetch RP signature from backend, then open widget
  const startVerification = useCallback(async () => {
    setState('loading_rp')
    setError(null)

    try {
      const resp = await fetch(`${API_BASE}/api/v1/world-id/rp-signature?action=verify-worker`)
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `Failed to get RP signature: ${resp.status}`)
      }

      const data: RPSignatureData = await resp.json()
      setRPData(data)
      setState('widget_open')
      setWidgetOpen(true)
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Failed to start verification')
    }
  }, [])

  // Handle successful IDKit v4 verification result
  const handleSuccess = useCallback(async (result: IDKitResult) => {
    if (!executor) return

    setState('verifying')
    setWidgetOpen(false)
    setError(null)

    try {
      // Extract the first response (orb proof).
      // We use orbLegacy preset so responses are always V3 or V4 (never Session).
      const rawResponse = result.responses?.[0]
      if (!rawResponse) {
        throw new Error('No proof response received from World ID')
      }

      // Narrow to V3 | V4 (both have `nullifier`, Session has `session_nullifier`)
      const response = rawResponse as ResponseItemV3 | ResponseItemV4

      // Both v3 and v4 responses have `identifier` and `nullifier` fields.
      // v3: proof is a single hex string + has merkle_root
      // v4: proof is string[] (compressed Groth16 + merkle root)
      const verificationLevel = response.identifier === 'proof_of_human' ? 'orb' : 'device'

      // Build payload for backend verification
      // Send the raw IDKit responses array so the backend can forward it to
      // the v4 Cloud API (which requires the responses[] format).
      const payload: Record<string, unknown> = {
        executor_id: executor.id,
        protocol_version: result.protocol_version,
        nonce: result.nonce,
        action: 'action' in result ? result.action : undefined,
        signal: walletAddress || '',
        verification_level: verificationLevel,
        nullifier_hash: response.nullifier,
        // Raw IDKit responses array for v4 Cloud API forwarding
        responses: result.responses,
      }

      // Also include individual fields for DB storage
      if ('merkle_root' in response) {
        payload.merkle_root = (response as ResponseItemV3).merkle_root
      }
      payload.proof = typeof response.proof === 'string' ? response.proof : JSON.stringify(response.proof)

      const resp = await fetch(`${API_BASE}/api/v1/world-id/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }))
        throw new Error(data.detail || `Verification failed: ${resp.status}`)
      }

      setState('success')

      // Refresh executor to pick up new world_id_verified flag
      await refreshExecutor()

      if (onVerified) {
        onVerified(verificationLevel)
      }
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Verification failed')
    }
  }, [executor, walletAddress, refreshExecutor, onVerified])

  // Handle widget open/close state
  const handleOpenChange = useCallback((open: boolean) => {
    setWidgetOpen(open)
    if (!open && state === 'widget_open') {
      // User closed widget without completing
      setState('idle')
      setRPData(null)
    }
  }, [state])

  // --- Already verified UI ---
  if (isVerified) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <WorldIdBadge level={currentLevel || 'device'} size="md" />
        <span className="text-sm text-gray-600">
          {currentLevel === 'orb'
            ? t('worldId.orbVerified', 'Orb Verified Human')
            : t('worldId.deviceVerified', 'Device Verified')}
        </span>
      </div>
    )
  }

  // Build rp_context from backend data
  const rpContext: RpContext | null = rpData ? {
    rp_id: rpData.rp_id,
    nonce: rpData.nonce,
    created_at: rpData.created_at,
    expires_at: rpData.expires_at,
    signature: rpData.signature,
  } : null

  // --- Verification flow UI ---
  return (
    <div className={`space-y-3 ${className}`}>
      {/* Trigger button */}
      {state === 'idle' && !rpData && (
        <button
          onClick={startVerification}
          className="flex items-center gap-2 px-4 py-2.5 bg-black text-white rounded-xl hover:bg-gray-800 transition-colors font-medium text-sm"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
          </svg>
          {t('worldId.verifyButton', 'Verify with World ID')}
        </button>
      )}

      {/* Loading state */}
      {state === 'loading_rp' && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-black rounded-full animate-spin" />
          {t('worldId.preparing', 'Preparing verification...')}
        </div>
      )}

      {/* IDKit v4 Widget (controlled, rendered when RP data is ready) */}
      {rpData && rpContext && state === 'widget_open' && (
        <IDKitRequestWidget
          app_id={rpData.app_id as `app_${string}`}
          action={rpData.action}
          rp_context={rpContext}
          allow_legacy_proofs={true}
          preset={orbLegacy({ signal: walletAddress || '' })}
          open={widgetOpen}
          onOpenChange={handleOpenChange}
          onSuccess={handleSuccess}
          autoClose
        />
      )}

      {/* Verifying state */}
      {state === 'verifying' && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-black rounded-full animate-spin" />
          {t('worldId.verifyingProof', 'Verifying proof...')}
        </div>
      )}

      {/* Success state */}
      {state === 'success' && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-700 font-medium">
            {t('worldId.success', 'Verification successful! You are now verified as a unique human.')}
          </p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={() => { setError(null); setState('idle'); setRPData(null) }}
            className="mt-1 text-sm text-red-600 hover:text-red-800 underline"
          >
            {t('worldId.tryAgain', 'Try again')}
          </button>
        </div>
      )}

      {/* Explainer */}
      {state === 'idle' && !rpData && (
        <p className="text-xs text-gray-400">
          {t('worldId.explainer', 'World ID verifies you are a unique human without revealing your identity. Required for tasks above $5.')}
        </p>
      )}
    </div>
  )
}


// ---------------------------------------------------------------------------
// World ID Badge (reusable inline badge)
// ---------------------------------------------------------------------------

interface WorldIdBadgeProps {
  level: string
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

export function WorldIdBadge({ level, size = 'sm', showLabel = false }: WorldIdBadgeProps) {
  const isOrb = level === 'orb'
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  }

  return (
    <span
      className={`inline-flex items-center gap-1 ${isOrb ? 'text-black' : 'text-gray-500'}`}
      title={isOrb ? 'World ID Orb Verified' : 'World ID Device Verified'}
    >
      <svg
        className={sizeClasses[size]}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="12" cy="12" r="10"
          stroke="currentColor"
          strokeWidth={isOrb ? 2.5 : 1.5}
          fill={isOrb ? 'currentColor' : 'none'}
        />
        <circle
          cx="12" cy="12" r="4"
          stroke={isOrb ? 'white' : 'currentColor'}
          strokeWidth={isOrb ? 2 : 1.5}
          fill="none"
        />
      </svg>
      {showLabel && (
        <span className="text-xs font-medium">
          {isOrb ? 'Orb' : 'Device'}
        </span>
      )}
    </span>
  )
}
