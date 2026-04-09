/**
 * ENSLinkSection - ENS Identity management on profile page
 *
 * Shows existing ENS name (auto-detected) and allows claiming a subname
 * under execution-market.eth. Follows WorldIdVerification.tsx pattern.
 */

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { linkENS, claimSubname } from '../services/ens'
import { ENSBadge } from './agents/ENSBadge'
import { safeHref } from '../lib/safeHref'

type State = 'idle' | 'resolving' | 'claiming' | 'success' | 'error'

export function ENSLinkSection() {
  const { t } = useTranslation()
  const { executor, refreshExecutor } = useAuth()
  const [state, setState] = useState<State>('idle')
  const [error, setError] = useState<string | null>(null)
  const [subnameLabel, setSubnameLabel] = useState('')
  const [claimResult, setClaimResult] = useState<{
    subname?: string
    tx_hash?: string
    explorer?: string
  } | null>(null)

  const ensName = executor?.ens_name
  const ensSubname = executor?.ens_subname
  const executorId = executor?.id

  // Auto-detect ENS name via reverse resolution
  const handleDetectENS = useCallback(async () => {
    if (!executorId) return
    setState('resolving')
    setError(null)

    try {
      const result = await linkENS(executorId)
      if (result.linked) {
        await refreshExecutor?.()
        // Go back to idle — the refreshed executor data will show the detected ENS
        setState('idle')
      } else {
        setError(result.message)
        setState('error')
      }
    } catch {
      setError('Failed to resolve ENS name')
      setState('error')
    }
  }, [executorId, refreshExecutor])

  // Claim subname under execution-market.eth
  const handleClaimSubname = useCallback(async () => {
    if (!executorId || !subnameLabel.trim()) return
    setState('claiming')
    setError(null)

    try {
      const result = await claimSubname(executorId, subnameLabel.trim().toLowerCase())
      if (result.success) {
        setClaimResult({
          subname: result.subname ?? undefined,
          tx_hash: result.tx_hash ?? undefined,
          explorer: result.explorer ?? undefined,
        })
        setState('success')
        // Refresh executor data in background — don't let failure override success
        try { await refreshExecutor?.() } catch { /* non-critical */ }
      } else {
        setError(result.message)
        setState('error')
      }
    } catch {
      setError('Failed to claim subname')
      setState('error')
    }
  }, [executorId, subnameLabel, refreshExecutor])

  return (
    <div className="space-y-4">
      {/* Existing ENS Name */}
      {ensName && (
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('profile.ensDetected', 'ENS Name Detected')}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {t('profile.ensAutoDetected', 'Auto-detected from your wallet')}
            </div>
          </div>
          <ENSBadge ensName={ensName} size="md" />
        </div>
      )}

      {/* Existing Subname */}
      {ensSubname && (
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('profile.ensSubname', 'Execution Market Subname')}
            </div>
          </div>
          <ENSBadge ensName={ensSubname} size="md" />
        </div>
      )}

      {/* Detect ENS (only if no ENS detected yet) */}
      {!ensName && !ensSubname && state === 'idle' && (
        <div>
          <button
            onClick={handleDetectENS}
            className="w-full px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-lg hover:bg-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-300 dark:hover:bg-indigo-900/40 transition-colors"
          >
            {t('profile.ensDetect', 'Detect ENS Name')}
          </button>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {t('profile.ensDetectHint', 'Check if your wallet has an ENS name')}
          </p>
        </div>
      )}

      {/* Claim subname — always show if no subname yet */}
      {!ensSubname && state === 'idle' && (
        <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('profile.ensClaimTitle', 'Claim your execution-market.eth subname')}
          </div>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <input
                type="text"
                value={subnameLabel}
                onChange={(e) => setSubnameLabel(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                placeholder="alice"
                maxLength={63}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
              />
              {subnameLabel && (
                <div className="mt-1 text-xs text-indigo-600 dark:text-indigo-400">
                  {subnameLabel}.execution-market.eth
                </div>
              )}
            </div>
            <button
              onClick={handleClaimSubname}
              disabled={!subnameLabel.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {t('profile.ensClaim', 'Claim')}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {t('profile.ensClaimHint', 'Free subname — creates an on-chain ENS identity for you')}
          </p>
        </div>
      )}

      {/* Resolving state */}
      {state === 'resolving' && (
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {t('profile.ensResolving', 'Checking ENS...')}
        </div>
      )}

      {/* Claiming state */}
      {state === 'claiming' && (
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {t('profile.ensClaiming', 'Creating subname on-chain...')}
        </div>
      )}

      {/* Success */}
      {state === 'success' && claimResult && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-sm font-medium text-green-800 dark:text-green-300">
            {t('profile.ensClaimSuccess', 'Subname created!')}
          </div>
          {claimResult.subname && (
            <div className="mt-1">
              <ENSBadge ensName={claimResult.subname} size="md" />
            </div>
          )}
          {claimResult.explorer && (
            <a
              href={safeHref(claimResult.explorer)}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 text-xs text-green-600 dark:text-green-400 underline"
            >
              {t('profile.viewOnEtherscan', 'View on Etherscan')}
            </a>
          )}
        </div>
      )}

      {/* Already has ENS and/or subname */}
      {(ensName || ensSubname) && state === 'idle' && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <a
            href="https://app.ens.domains"
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            {t('profile.ensManage', 'Manage on ENS App')}
          </a>
        </div>
      )}

      {/* Error */}
      {state === 'error' && error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <div className="text-sm text-red-800 dark:text-red-300">{error}</div>
          <button
            onClick={() => { setState('idle'); setError(null) }}
            className="mt-1 text-xs text-red-600 dark:text-red-400 underline"
          >
            {t('common.tryAgain', 'Try again')}
          </button>
        </div>
      )}
    </div>
  )
}
