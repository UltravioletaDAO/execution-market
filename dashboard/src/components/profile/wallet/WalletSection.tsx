// WalletSection — canonical place on /profile for everything wallet-related
// under ADR-001: on-chain balance breakdown, send/receive, key export, AND
// (when the user has 2+ wallets linked) a switcher to pick which one is
// active.
//
// `walletAddress` from props is the address Supabase has on record for this
// executor. We display ITS balance only when Dynamic hasn't loaded yet —
// otherwise we follow Dynamic's `primaryWallet`, which the selector mutates.
// This keeps the displayed balance in sync with whatever wallet the user
// just clicked, without needing to round-trip through AuthContext.

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDynamicContext } from '@dynamic-labs/sdk-react-core'
import { useOnchainBalance } from '../../../hooks/useOnchainBalance'
import { ExportWalletButton } from './ExportWalletButton'
import { SendUSDCModal } from './SendUSDCModal'
import { ReceiveModal } from './ReceiveModal'
import { WalletSelector } from './WalletSelector'

interface WalletSectionProps {
  walletAddress: string
}

export function WalletSection({ walletAddress }: WalletSectionProps) {
  const { t } = useTranslation()
  const { primaryWallet } = useDynamicContext()
  const activeAddress = primaryWallet?.address?.toLowerCase() || walletAddress
  const { balances, totalUsdc, loading, error, lastUpdated, refetch } = useOnchainBalance(activeAddress)
  const [sendOpen, setSendOpen] = useState(false)
  const [receiveOpen, setReceiveOpen] = useState(false)

  const formatShortAddress = (addr: string) => `${addr.slice(0, 6)}...${addr.slice(-4)}`

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-gray-900 font-semibold">
              {t('wallet.section.title', 'Wallet')}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {formatShortAddress(activeAddress)} ·{' '}
              {t('wallet.section.subtitle', 'Live on-chain balance')}
            </p>
          </div>
          <button
            onClick={() => void refetch()}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg"
            title={t('common.refresh', 'Refresh')}
            aria-label={t('common.refresh', 'Refresh')}
            disabled={loading}
          >
            <svg
              className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>

        <WalletSelector />

        <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-4 text-white">
          <div className="text-xs text-gray-300 uppercase tracking-wide">
            {t('wallet.section.totalBalance', 'Total USDC across chains')}
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-bold">${totalUsdc.toFixed(2)}</span>
            <span className="text-xs text-gray-400">USDC</span>
          </div>
          {lastUpdated && (
            <div className="text-[11px] text-gray-400 mt-1">
              {t('wallet.section.updated', 'Updated')} {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => setSendOpen(true)}
            disabled={totalUsdc <= 0}
            className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M14 5l7 7m0 0l-7 7m7-7H3"
              />
            </svg>
            {t('wallet.section.send', 'Send')}
          </button>
          <button
            onClick={() => setReceiveOpen(true)}
            className="flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium text-gray-800 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            {t('wallet.section.receive', 'Receive')}
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-900">
            {t('wallet.section.error', "Couldn't load balances.")} {error.message}
          </div>
        )}

        <div className="space-y-1.5">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide px-1">
            {t('wallet.section.byChain', 'By chain')}
          </div>
          {loading && balances.length === 0 ? (
            <div className="space-y-1.5">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-10 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : (
            balances.map((b) => (
              <div
                key={b.network.key}
                className="flex items-center justify-between px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg"
              >
                <div className="flex items-center gap-2.5">
                  <img src={b.network.logo} alt="" className="w-5 h-5 rounded-full" />
                  <span className="text-sm text-gray-800">{b.network.name}</span>
                </div>
                {b.error ? (
                  <span
                    className="text-xs text-gray-400"
                    title={b.error}
                  >
                    {t('wallet.section.rpcError', 'RPC error')}
                  </span>
                ) : (
                  <span className="text-sm font-medium text-gray-900">
                    ${b.balance.toFixed(2)}
                  </span>
                )}
              </div>
            ))
          )}
        </div>

        <div className="pt-3 border-t border-gray-100">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 px-1">
            {t('wallet.section.security', 'Security')}
          </div>
          <ExportWalletButton />
        </div>
      </div>

      <SendUSDCModal open={sendOpen} onClose={() => setSendOpen(false)} balances={balances} />
      <ReceiveModal
        open={receiveOpen}
        onClose={() => setReceiveOpen(false)}
        walletAddress={activeAddress}
      />
    </>
  )
}
