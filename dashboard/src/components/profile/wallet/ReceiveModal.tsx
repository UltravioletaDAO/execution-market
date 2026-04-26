// ReceiveModal — shows the worker's wallet address + QR so anyone can send
// USDC to them. Under ADR-001 the rewards inbox is `identityAddress`: the
// wallet bound to this executor's row in Supabase and to their on-chain
// ERC-8004 identity. That's where agents settle on task approval.
//
// `activeAddress` is whatever Dynamic currently has selected. When it differs
// from identity (e.g. the user linked a Ledger but is signing from an embedded
// wallet today), we expose a toggle so they can copy the active address for a
// one-off transfer. The default tab is always identity — that prevents the
// "QR shows wallet B but rewards land in wallet A" footgun.

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import QRCode from 'qrcode'
import { LIVE_NETWORKS } from '../../../config/networks'

interface ReceiveModalProps {
  identityAddress: string
  activeAddress?: string
  open: boolean
  onClose: () => void
}

type Mode = 'identity' | 'active'

export function ReceiveModal({ identityAddress, activeAddress, open, onClose }: ReceiveModalProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>('identity')
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // Reset to identity each time the modal opens — rewards default beats whatever
  // the user picked last time. If they want the active wallet, they re-pick it.
  useEffect(() => {
    if (open) setMode('identity')
  }, [open])

  const showToggle =
    !!activeAddress && activeAddress.toLowerCase() !== identityAddress.toLowerCase()
  const displayedAddress = mode === 'active' && activeAddress ? activeAddress : identityAddress

  useEffect(() => {
    if (!open || !displayedAddress) return
    QRCode.toDataURL(displayedAddress, {
      width: 240,
      margin: 1,
      color: { dark: '#111827', light: '#ffffff' },
    })
      .then(setQrDataUrl)
      .catch(() => setQrDataUrl(null))
  }, [open, displayedAddress])

  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), 2000)
    return () => clearTimeout(timer)
  }, [copied])

  if (!open) return null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(displayedAddress)
      setCopied(true)
    } catch {
      /* ignore */
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              {t('wallet.receive.title', 'Receive USDC')}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {mode === 'identity'
                ? t(
                    'wallet.receive.identitySubtitle',
                    'This is your rewards inbox. USDC sent here lands across any supported chain.',
                  )
                : t(
                    'wallet.receive.activeSubtitle',
                    'For one-off transfers to the wallet you have active right now — task rewards still go to your rewards inbox.',
                  )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1"
            aria-label={t('common.close', 'Close')}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {showToggle && (
          <div className="mb-4 inline-flex p-1 bg-gray-100 rounded-lg">
            <button
              onClick={() => setMode('identity')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                mode === 'identity'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {t('wallet.receive.toggleIdentity', 'Rewards inbox')}
            </button>
            <button
              onClick={() => setMode('active')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                mode === 'active'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {t('wallet.receive.toggleActive', 'Active wallet')}
            </button>
          </div>
        )}

        <div className="flex flex-col items-center gap-4 bg-gray-50 rounded-xl p-4 border border-gray-100">
          {qrDataUrl ? (
            <img src={qrDataUrl} alt="Wallet QR" className="w-60 h-60 rounded-lg bg-white p-2" />
          ) : (
            <div className="w-60 h-60 bg-gray-200 animate-pulse rounded-lg" />
          )}

          <div className="w-full">
            <div className="text-xs text-gray-500 mb-1">
              {mode === 'identity'
                ? t('wallet.receive.identityLabel', 'Your rewards inbox')
                : t('wallet.receive.activeLabel', 'Your active wallet (one-off)')}
            </div>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono text-gray-800 bg-white border border-gray-200 rounded-lg px-3 py-2 break-all">
                {displayedAddress}
              </code>
              <button
                onClick={handleCopy}
                className="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100"
              >
                {copied ? t('common.copied', 'Copied!') : t('common.copy', 'Copy')}
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900">
          <strong>{t('wallet.receive.warningTitle', 'One address, multiple chains.')}</strong>{' '}
          {t(
            'wallet.receive.warningBody',
            'This is your EVM address. You can receive USDC on Base, Ethereum, Polygon, Arbitrum, Optimism, Avalanche, and Celo — make sure the sender picks the right chain.',
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {LIVE_NETWORKS.filter((n) => n.networkType !== 'svm').map((n) => (
            <span
              key={n.key}
              className="inline-flex items-center gap-1.5 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-full px-2.5 py-1"
            >
              <img src={n.logo} alt="" className="w-3.5 h-3.5 rounded-full" />
              {n.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
