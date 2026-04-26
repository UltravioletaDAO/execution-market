// Phase 4 — surfaced on /profile when the wallet Dynamic has active is not
// the same address Supabase has on record as the executor's rewards inbox.
// One click → sign a short challenge → backend swaps the on-record wallet,
// future task payouts land in the new address.
//
// Hidden when active == identity (the common case). The banner is a soft
// nudge, not an error: nothing is broken, but the user might be confused
// about why the active wallet they're staring at isn't where rewards go.

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDynamicContext } from '@dynamic-labs/sdk-react-core'
import { useAuth } from '../../../context/hooks'
import { truncateAddress } from '../../../lib/utils'
import { updateWalletAddress } from '../../../services/updateWalletAddress'

interface WalletMismatchBannerProps {
  /** Executor's on-record rewards inbox (Supabase row, ERC-8004 identity). */
  identityAddress: string
}

export function WalletMismatchBanner({ identityAddress }: WalletMismatchBannerProps) {
  const { t } = useTranslation()
  const { primaryWallet } = useDynamicContext()
  const { executor, refreshExecutor } = useAuth()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)

  const activeAddress = primaryWallet?.address?.toLowerCase() || ''
  const identity = identityAddress.toLowerCase()

  if (!activeAddress || !identity || activeAddress === identity) {
    return null
  }

  const handleChange = async () => {
    if (!executor || !primaryWallet) return
    setBusy(true)
    setError(null)
    try {
      await updateWalletAddress({
        newWalletAddress: activeAddress,
        executorId: executor.id,
        primaryWallet,
      })
      await refreshExecutor()
      setConfirming(false)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Wallet change failed'
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-amber-900 text-sm">
            {t('wallet.mismatch.title', 'Different wallet active')}
          </h4>
          <p className="text-xs text-amber-800 mt-1 break-words">
            {t(
              'wallet.mismatch.body',
              'Payments land in {{identity}}. Want them to land in {{active}} instead?',
              {
                identity: truncateAddress(identity),
                active: truncateAddress(activeAddress),
              },
            )}
          </p>

          {error && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-900">
              {error}
            </div>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            {!confirming ? (
              <button
                onClick={() => {
                  setError(null)
                  setConfirming(true)
                }}
                className="px-3 py-1.5 text-xs font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700"
              >
                {t('wallet.mismatch.cta', 'Change payment wallet')}
              </button>
            ) : (
              <>
                <button
                  onClick={handleChange}
                  disabled={busy}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700 disabled:bg-amber-300 disabled:cursor-not-allowed"
                >
                  {busy
                    ? t('wallet.mismatch.signing', 'Signing...')
                    : t('wallet.mismatch.confirm', 'Sign with {{active}}', {
                        active: truncateAddress(activeAddress),
                      })}
                </button>
                <button
                  onClick={() => {
                    setConfirming(false)
                    setError(null)
                  }}
                  disabled={busy}
                  className="px-3 py-1.5 text-xs font-medium text-amber-900 bg-white border border-amber-300 rounded-lg hover:bg-amber-50 disabled:cursor-not-allowed"
                >
                  {t('common.cancel', 'Cancel')}
                </button>
              </>
            )}
          </div>

          {confirming && !busy && !error && (
            <p className="mt-2 text-[11px] text-amber-700">
              {t(
                'wallet.mismatch.note',
                "We'll ask you to sign a short message. No transaction, no gas.",
              )}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
