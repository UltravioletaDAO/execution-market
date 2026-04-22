// ExportWalletButton — opens Dynamic's built-in user profile UI which
// includes the vetted export-private-key / reveal-recovery-phrase flow.
// We intentionally do NOT build our own export UI: Dynamic handles the
// Turnkey iframe, passkey re-auth and anti-phishing warnings. Our only job
// is to surface it clearly.

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDynamicContext } from '@dynamic-labs/sdk-react-core'

export function ExportWalletButton() {
  const { t } = useTranslation()
  const { setShowDynamicUserProfile, primaryWallet } = useDynamicContext()
  const [confirming, setConfirming] = useState(false)

  const isEmbedded = Boolean(primaryWallet?.connector?.isEmbeddedWallet)

  if (!isEmbedded) {
    return (
      <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-600">
        {t(
          'wallet.export.externalWallet',
          "You're using an external wallet — manage your keys from that wallet's app.",
        )}
      </div>
    )
  }

  const handleOpen = () => {
    setShowDynamicUserProfile(true)
    setConfirming(false)
  }

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3">
      <div className="flex items-start gap-2">
        <svg
          className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <div>
          <h4 className="text-sm font-semibold text-amber-900">
            {t('wallet.export.title', 'Export your private key')}
          </h4>
          <p className="text-xs text-amber-900/80 mt-1">
            {t(
              'wallet.export.body',
              'Your wallet is fully self-custody. Export the private key to move it to MetaMask, Rabby, or any wallet you already use. Anyone with this key can spend your funds — never share it.',
            )}
          </p>
        </div>
      </div>

      {confirming ? (
        <div className="flex gap-2">
          <button
            onClick={handleOpen}
            className="flex-1 px-3 py-2 text-sm font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700"
          >
            {t('wallet.export.confirm', 'Yes, show me')}
          </button>
          <button
            onClick={() => setConfirming(false)}
            className="flex-1 px-3 py-2 text-sm font-medium text-amber-900 bg-white border border-amber-200 rounded-lg hover:bg-amber-50"
          >
            {t('common.cancel', 'Cancel')}
          </button>
        </div>
      ) : (
        <button
          onClick={() => setConfirming(true)}
          className="w-full px-3 py-2 text-sm font-medium text-amber-900 bg-white border border-amber-300 rounded-lg hover:bg-amber-100"
        >
          {t('wallet.export.button', 'Open export flow')}
        </button>
      )}
    </div>
  )
}
