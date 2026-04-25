// WalletSelector — lets the user see every wallet linked to their session
// and switch which one is primary. Built for the case where a user logs in
// via email (Dynamic auto-creates an embedded wallet) AND has an external
// wallet linked (Ledger, MetaMask, ...). Without this UI, Dynamic's "Edit
// Profile" was the only way to switch — surfacing it here removes the
// surprise of "I see one wallet on the dashboard but Edit Profile shows
// another."
//
// Trust model: switching is delegated to Dynamic's `useSwitchWallet`. We
// never touch keys; we just set which connector ID is the active one. The
// embedded-wallet badge is informational so users know which wallets are
// custody-of-Dynamic vs custody-of-themselves.

import { useTranslation } from 'react-i18next'
import { useDynamicContext, useSwitchWallet, useUserWallets } from '@dynamic-labs/sdk-react-core'
import { useState } from 'react'

const formatShortAddress = (addr: string) => `${addr.slice(0, 6)}...${addr.slice(-4)}`

export function WalletSelector() {
  const { t } = useTranslation()
  const { primaryWallet } = useDynamicContext()
  const userWallets = useUserWallets()
  const switchWallet = useSwitchWallet()
  const [switching, setSwitching] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Don't render anything if there's only one wallet — selector adds no value
  // and would just be visual noise on the profile.
  const wallets = userWallets.filter((w) => Boolean(w.address))
  if (wallets.length < 2) return null

  const activeId = primaryWallet?.id

  const handleSwitch = async (walletId: string) => {
    if (walletId === activeId || switching) return
    setSwitching(walletId)
    setError(null)
    try {
      await switchWallet(walletId)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Switch failed'
      setError(message)
    } finally {
      setSwitching(null)
    }
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          {t('wallet.selector.title', 'Active wallet')}
        </span>
        <span className="text-[11px] text-gray-400">
          {t('wallet.selector.count', '{{count}} linked', { count: wallets.length })}
        </span>
      </div>
      <div className="space-y-1.5">
        {wallets.map((wallet) => {
          const address = wallet.address as string
          const isActive = wallet.id === activeId
          const isEmbedded = Boolean(wallet.connector?.isEmbeddedWallet)
          const isSwitching = switching === wallet.id
          return (
            <button
              key={wallet.id}
              type="button"
              onClick={() => void handleSwitch(wallet.id)}
              disabled={isActive || Boolean(switching)}
              aria-pressed={isActive}
              className={[
                'w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg border text-left transition',
                isActive
                  ? 'bg-blue-50 border-blue-200 cursor-default'
                  : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300',
                switching && !isActive ? 'opacity-50 cursor-wait' : '',
              ].join(' ')}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    isActive ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
                  aria-hidden="true"
                />
                <div className="flex flex-col min-w-0">
                  <span className="font-mono text-sm text-gray-900 truncate">
                    {formatShortAddress(address)}
                  </span>
                  <span className="text-[11px] text-gray-500">
                    {isEmbedded
                      ? t('wallet.selector.embedded', 'Embedded (Dynamic-managed)')
                      : t('wallet.selector.external', 'External (self-custody)')}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {isActive && (
                  <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700 bg-blue-100 rounded-full">
                    {t('wallet.selector.active', 'Active')}
                  </span>
                )}
                {isSwitching && (
                  <svg
                    className="w-4 h-4 text-gray-500 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                )}
              </div>
            </button>
          )
        })}
      </div>
      {error && (
        <div className="px-3 py-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg">
          {error}
        </div>
      )}
    </div>
  )
}
